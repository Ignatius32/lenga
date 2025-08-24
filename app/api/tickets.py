from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app import models
from app import schemas
from app.core.security import get_current_user, get_current_user_bypass
from app.core.movement import record_ticket_movement

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post('/', response_model=schemas.TicketOut)
def create_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    # Verify queue exists
    queue = db.query(models.Queue).filter(models.Queue.id == payload.queue_id).first()
    if not queue:
        raise HTTPException(status_code=404, detail='Queue not found')

    # Check user's groups and permissions: ensure at least one of user's groups has a permission for the target queue
    user_groups = db.query(models.UserGroup).filter(models.UserGroup.user_id == user.id).all()
    group_ids = [g.group_id for g in user_groups]
    if not group_ids:
        raise HTTPException(status_code=403, detail='User does not belong to any group allowed to create tickets')
    perm = db.query(models.QueuePermission).filter(models.QueuePermission.queue_id == payload.queue_id, models.QueuePermission.group_id.in_(group_ids)).first()
    if not perm:
        raise HTTPException(status_code=403, detail='User groups lack permission to post in this queue')

    ticket = models.Ticket(
        subject=payload.subject,
        description=payload.description,
        client_user_id=user.id,
        current_queue_id=payload.queue_id,
        ticket_type_id=payload.ticket_type_id,
    )
    db.add(ticket)
    db.flush()

    # If a ticket type with allowed groups is set, ensure user belongs to allowed groups
    if payload.ticket_type_id:
        tt = db.query(models.TicketType).filter(models.TicketType.id == payload.ticket_type_id).first()
        if not tt:
            raise HTTPException(status_code=404, detail='Ticket type not found')
        allowed = db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).all()
        if allowed:
            allowed_group_ids = [a.group_id for a in allowed]
            # ensure intersection
            if not set(allowed_group_ids).intersection(set(group_ids)):
                raise HTTPException(status_code=403, detail='User groups not allowed to create this ticket type')

    # Persist custom field values if provided
    created_field_values = []
    if payload.custom_fields:
        # load field defs
        field_defs = {}
        frows = db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == payload.ticket_type_id).all() if payload.ticket_type_id else []
        for f in frows:
            field_defs[f.id] = f

        import json
        for cf in payload.custom_fields:
            # expect dict with either 'field_id' or 'name'
            field_id = cf.get('field_id')
            value = cf.get('value')
            if field_id:
                fdef = field_defs.get(field_id)
                if not fdef:
                    raise HTTPException(status_code=400, detail=f'Unknown custom field id {field_id}')
            else:
                # try match by name
                fdef = None
                for fd in field_defs.values():
                    if fd.name == cf.get('name'):
                        fdef = fd
                        break
                if not fdef:
                    raise HTTPException(status_code=400, detail=f'Unknown custom field name {cf.get("name")}')

            # validate based on type
            if fdef.field_type == 'select' and fdef.options:
                opts = json.loads(fdef.options)
                if value not in opts:
                    raise HTTPException(status_code=400, detail=f'Invalid option for field {fdef.name}')
            if fdef.field_type == 'space':
                # ensure space exists
                sid = int(value)
                sp = db.query(models.Space).filter(models.Space.id == sid).first()
                if not sp:
                    raise HTTPException(status_code=400, detail=f'Invalid space id for field {fdef.name}')

            tfv = models.TicketFieldValue(ticket_id=ticket.id, field_id=fdef.id, value=str(value) if value is not None else None)
            db.add(tfv)
            created_field_values.append(tfv)
    record_ticket_movement(db, ticket, user.id, 'CREATE', {'queue_id': payload.queue_id})
    db.commit()
    db.refresh(ticket)
    # attach custom fields to response model (TicketOut expects custom_fields list)
    out_custom = []
    for cfv in created_field_values:
        out_custom.append({'field_id': cfv.field_id, 'value': cfv.value})
    # FastAPI will use response_model to serialize; we return a dict-compatible object
    resp = ticket
    # monkey-patch attribute for Pydantic from_attributes
    setattr(resp, 'custom_fields', out_custom)
    return resp


@router.get('/me', response_model=List[schemas.TicketOut])
def my_tickets(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    tickets = db.query(models.Ticket).filter(models.Ticket.client_user_id == user.id).all()
    return tickets


@router.get('/{ticket_id}', response_model=schemas.TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Ensure requester is creator or (agent logic deferred)
    if ticket.client_user_id != user.id:
        raise HTTPException(status_code=403, detail='Not authorized to view this ticket')
    return ticket



@router.get('/types', response_model=List[schemas.TicketTypeOut])
def list_ticket_types_for_user(queue_id: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    # get user's groups
    user_groups = db.query(models.UserGroup).filter(models.UserGroup.user_id == user.id).all()
    group_ids = [g.group_id for g in user_groups]

    q = db.query(models.TicketType)
    if queue_id is not None:
        q = q.filter(models.TicketType.queue_id == queue_id)
    tts = q.all()

    result = []
    import json
    for tt in tts:
        # check allowed groups
        allowed_rows = db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).all()
        if allowed_rows:
            allowed_ids = [a.group_id for a in allowed_rows]
            if not set(allowed_ids).intersection(set(group_ids)):
                # skip ticket types user isn't allowed to create
                continue

        # include fields
        frows = db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()
        fields = []
        for f in frows:
            opts = None
            if f.options:
                opts = json.loads(f.options)
            fields.append(schemas.TicketFieldOut(id=f.id, name=f.name, field_type=f.field_type, options=opts))

        # allowed group ids
        allowed = [a.group_id for a in allowed_rows]
        result.append(schemas.TicketTypeOut(id=tt.id, queue_id=tt.queue_id, name=tt.name, allowed_group_ids=allowed, fields=fields))

    return result



@router.get('/{ticket_id}/history', response_model=schemas.TicketHistoryOut)
def ticket_history(ticket_id: int, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')

    # Authorization: allow ticket creator, assigned agent for the queue, or admin
    if ticket.client_user_id != user.id:
        # check agent assignment for user's agent assignments
        is_agent_assigned = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
        if not is_agent_assigned and 'admin' not in getattr(user, 'roles', []):
            raise HTTPException(status_code=403, detail='Not authorized to view this ticket history')

    # movements
    mrows = db.query(models.TicketMovementLog).filter(models.TicketMovementLog.ticket_id == ticket.id).order_by(models.TicketMovementLog.timestamp.asc()).all()

    # comments
    crows = db.query(models.TicketComment).filter(models.TicketComment.ticket_id == ticket.id).order_by(models.TicketComment.created_at.asc()).all()

    # attachments (ticket-level and comment-level)
    arows = db.query(models.Attachment).filter(models.Attachment.ticket_id == ticket.id).all()

    # collect all involved user ids to fetch brief user profiles in one query
    user_ids = set()
    for m in mrows:
        if m.action_user_id:
            user_ids.add(m.action_user_id)
    for c in crows:
        if c.author_user_id:
            user_ids.add(c.author_user_id)
    for a in arows:
        if a.uploader_user_id:
            user_ids.add(a.uploader_user_id)

    user_map = {}
    if user_ids:
        urows = db.query(models.User).filter(models.User.id.in_(list(user_ids))).all()
        for u in urows:
            user_map[u.id] = {'id': u.id, 'keycloak_id': u.keycloak_id, 'first_name': u.first_name, 'last_name': u.last_name, 'email': u.email}

    movements = []
    for m in mrows:
        movements.append(schemas.MovementOut(id=m.id, ticket_id=m.ticket_id, timestamp=m.timestamp, action_user=user_map.get(m.action_user_id), action_type=m.action_type, details=m.details))

    comments = []
    for c in crows:
        comments.append(schemas.CommentOut(id=c.id, ticket_id=c.ticket_id, author=user_map.get(c.author_user_id), comment_text=c.comment_text, is_internal=c.is_internal, created_at=c.created_at))

    attachments = []
    for a in arows:
        attachments.append(schemas.AttachmentOut(id=a.id, ticket_id=a.ticket_id, comment_id=a.comment_id, file_name=a.file_name, file_path=a.file_path, uploader=user_map.get(a.uploader_user_id)))

    return schemas.TicketHistoryOut(ticket_id=ticket.id, movements=movements, comments=comments, attachments=attachments)
