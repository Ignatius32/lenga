from fastapi import APIRouter, Depends, HTTPException
from fastapi import UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas
from app.core.security import require_role, get_current_user_bypass

router = APIRouter(prefix='/admin', tags=['admin'])


# Simple admin UI endpoints (minimal HTML) for quick admin tasks
@router.get('/ui/users', response_model=None)
def admin_ui_users(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    users = db.query(models.User).all()
    # Render a minimal HTML page
    html = ['<html><head><title>Admin Users</title></head><body>']
    html.append('<h1>Users</h1>')
    html.append('<ul>')
    for u in users:
        html.append(f'<li>{u.id} - {u.first_name or ""} {u.last_name or ""} &lt;{u.email or ""}&gt; - <a href="/admin/ui/users/{u.id}">view</a> - <a href="/admin/users/{u.id}">json</a></li>')
    html.append('</ul>')
    html.append('</body></html>')
    return '\n'.join(html)


@router.get('/ui/users/{user_id}', response_model=None)
def admin_ui_user_detail(user_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail='user not found')
    # minimal detail view linking to JSON endpoints
    html = [f'<html><head><title>User {u.id}</title></head><body>']
    html.append(f'<h1>User {u.id}</h1>')
    html.append(f'<p>Name: {u.first_name or ""} {u.last_name or ""}</p>')
    html.append(f'<p>Email: {u.email or ""}</p>')
    html.append(f'<p><a href="/admin/users/{u.id}">View JSON</a> | <a href="/admin/users/{u.id}/roles">Roles (JSON)</a></p>')
    html.append('</body></html>')
    return '\n'.join(html)



@router.get('/ui/activity_types', response_model=None)
def admin_ui_activity_types(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tts = db.query(models.ActivityType).all()
    html = ['<html><head><title>Activity Types</title></head><body>']
    html.append('<h1>Activity Types</h1>')
    html.append('<ul>')
    for tt in tts:
        html.append(f'<li>{tt.id} - {tt.name} - <a href="/admin/ui/activity_types/{tt.id}">view</a> - <a href="/admin/ticket_types/{tt.id}">json</a></li>')
    html.append('</ul>')
    html.append('</body></html>')
    return '\n'.join(html)


@router.get('/ui/activity_types/{type_id}', response_model=None)
def admin_ui_activity_type_detail(type_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tt = db.query(models.ActivityType).filter(models.ActivityType.id == type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail='ActivityType not found')
    html = [f'<html><head><title>Activity Type {tt.id}</title></head><body>']
    html.append(f'<h1>Activity Type {tt.id} - {tt.name}</h1>')
    html.append(f'<p>Metadata: {tt.meta or ""}</p>')
    # fields list
    frows = db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == tt.id).all()
    html.append('<h2>Fields</h2>')
    html.append('<ul>')
    import json
    for f in frows:
        opts = ''
        if f.options:
            opts = json.loads(f.options)
        html.append(f'<li>{f.id} - {f.name} ({f.field_type}) - options: {opts} - <a href="/admin/types/{tt.id}/fields/{f.id}">edit</a> - <a href="/activities/types/{tt.id}">json</a></li>')
    html.append('</ul>')
    html.append(f'<p><a href="/admin/types/{tt.id}/fields">Add field (json)</a></p>')
    html.append('</body></html>')
    return '\n'.join(html)


@router.get('/roles')
def list_roles(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    return db.query(models.Role).all()


@router.post('/roles/assign')
def assign_role(payload: schemas.UserRoleAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    role = db.query(models.Role).filter(models.Role.name == payload.role_name).first()
    if not role:
        # create role on the fly
        role = models.Role(name=payload.role_name)
        db.add(role)
        db.commit()
        db.refresh(role)
    ur = db.query(models.UserRole).filter(models.UserRole.user_id == payload.user_id, models.UserRole.role_id == role.id).first()
    if ur:
        return {'status': 'already_assigned'}
    ur = models.UserRole(user_id=payload.user_id, role_id=role.id)
    db.add(ur)
    db.commit()
    return {'status': 'assigned'}


@router.post('/roles/remove')
def remove_role(payload: schemas.UserRoleAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    role = db.query(models.Role).filter(models.Role.name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail='role not found')
    ur = db.query(models.UserRole).filter(models.UserRole.user_id == payload.user_id, models.UserRole.role_id == role.id).first()
    if not ur:
        return {'status': 'not_assigned'}
    db.delete(ur)
    db.commit()
    return {'status': 'removed'}


@router.post('/ticket_types', response_model=schemas.TicketTypeOut)
def create_ticket_type(payload: schemas.TicketTypeCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    # create the ticket type
    tt = models.TicketType(queue_id=payload.queue_id, name=payload.name)
    db.add(tt)
    db.flush()

    # allowed groups
    if payload.allowed_group_ids:
        for gid in payload.allowed_group_ids:
            tg = models.TicketTypeAllowedGroup(ticket_type_id=tt.id, group_id=gid)
            db.add(tg)

    # fields
    created_fields = []
    if payload.fields:
        for f in payload.fields:
            options_json = None
            if f.options:
                import json
                options_json = json.dumps(f.options)
            tf = models.TicketTypeField(ticket_type_id=tt.id, name=f.name, field_type=f.field_type, options=options_json)
            db.add(tf)
            db.flush()
            created_fields.append(tf)

    db.commit()
    db.refresh(tt)

    # Build response structure
    out_fields = []
    for f in created_fields:
        opts = None
        if f.options:
            import json
            opts = json.loads(f.options)
        out_fields.append(schemas.TicketFieldOut(id=f.id, name=f.name, field_type=f.field_type, options=opts))

    allowed = []
    if payload.allowed_group_ids:
        allowed = payload.allowed_group_ids

    return schemas.TicketTypeOut(id=tt.id, queue_id=tt.queue_id, name=tt.name, allowed_group_ids=allowed, fields=out_fields)



@router.get('/ticket_types', response_model=list[schemas.TicketTypeOut])
def list_ticket_types(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tts = db.query(models.TicketType).all()
    out = []
    import json
    for tt in tts:
        # gather fields
        frows = db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()
        fields = []
        for f in frows:
            opts = None
            if f.options:
                opts = json.loads(f.options)
            fields.append(schemas.TicketFieldOut(id=f.id, name=f.name, field_type=f.field_type, options=opts))
        # gather allowed groups
        agr = db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).all()
        allowed = [a.group_id for a in agr]
        out.append(schemas.TicketTypeOut(id=tt.id, queue_id=tt.queue_id, name=tt.name, allowed_group_ids=allowed, fields=fields))
    return out


@router.get('/ticket_types/{ticket_type_id}', response_model=schemas.TicketTypeOut)
def get_ticket_type(ticket_type_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tt = db.query(models.TicketType).filter(models.TicketType.id == ticket_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail='Ticket type not found')
    import json
    frows = db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()
    fields = []
    for f in frows:
        opts = None
        if f.options:
            opts = json.loads(f.options)
        fields.append(schemas.TicketFieldOut(id=f.id, name=f.name, field_type=f.field_type, options=opts))
    agr = db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).all()
    allowed = [a.group_id for a in agr]
    return schemas.TicketTypeOut(id=tt.id, queue_id=tt.queue_id, name=tt.name, allowed_group_ids=allowed, fields=fields)


@router.put('/ticket_types/{ticket_type_id}', response_model=schemas.TicketTypeOut)
def update_ticket_type(ticket_type_id: int, payload: schemas.TicketTypeUpdate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tt = db.query(models.TicketType).filter(models.TicketType.id == ticket_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail='Ticket type not found')

    # apply simple updates
    if payload.name is not None:
        tt.name = payload.name
    if payload.queue_id is not None:
        tt.queue_id = payload.queue_id

    # replace allowed groups if provided
    if payload.allowed_group_ids is not None:
        # delete existing
        db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).delete()
        # add new
        for gid in payload.allowed_group_ids:
            db.add(models.TicketTypeAllowedGroup(ticket_type_id=tt.id, group_id=gid))

    # replace fields if provided
    created_fields = []
    if payload.fields is not None:
        # delete existing fields and their values
        # first delete field values
        fids = [f.id for f in db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()]
        if fids:
            db.query(models.TicketFieldValue).filter(models.TicketFieldValue.field_id.in_(fids)).delete(synchronize_session='fetch')
        db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).delete()
        # create new
        import json
        for f in payload.fields:
            options_json = None
            if f.options:
                options_json = json.dumps(f.options)
            tf = models.TicketTypeField(ticket_type_id=tt.id, name=f.name, field_type=f.field_type, options=options_json)
            db.add(tf)
            db.flush()
            created_fields.append(tf)

    db.commit()
    db.refresh(tt)

    # build response
    import json
    out_fields = []
    # if fields replaced, use created_fields list, otherwise load from db
    if created_fields:
        frows = created_fields
    else:
        frows = db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()
    for f in frows:
        opts = None
        if f.options:
            opts = json.loads(f.options)
        out_fields.append(schemas.TicketFieldOut(id=f.id, name=f.name, field_type=f.field_type, options=opts))
    agr = db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).all()
    allowed = [a.group_id for a in agr]
    return schemas.TicketTypeOut(id=tt.id, queue_id=tt.queue_id, name=tt.name, allowed_group_ids=allowed, fields=out_fields)


@router.delete('/ticket_types/{ticket_type_id}')
def delete_ticket_type(ticket_type_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    tt = db.query(models.TicketType).filter(models.TicketType.id == ticket_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail='Ticket type not found')
    # do not allow delete if tickets reference this type
    cnt = db.query(models.Ticket).filter(models.Ticket.ticket_type_id == tt.id).count()
    if cnt > 0:
        raise HTTPException(status_code=400, detail='Cannot delete ticket type with existing tickets')

    # delete related rows
    fids = [f.id for f in db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).all()]
    if fids:
        db.query(models.TicketFieldValue).filter(models.TicketFieldValue.field_id.in_(fids)).delete(synchronize_session='fetch')
    db.query(models.TicketTypeField).filter(models.TicketTypeField.ticket_type_id == tt.id).delete()
    db.query(models.TicketTypeAllowedGroup).filter(models.TicketTypeAllowedGroup.ticket_type_id == tt.id).delete()
    db.delete(tt)
    db.commit()
    return {'status': 'deleted'}


@router.post('/users', response_model=schemas.UserBase)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    u = db.query(models.User).filter(models.User.keycloak_id == payload.keycloak_id).first()
    if u:
        return u
    u = models.User(keycloak_id=payload.keycloak_id, dni=payload.dni, first_name=payload.first_name, last_name=payload.last_name, email=payload.email)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.get('/users/{user_id}', response_model=schemas.UserBase)
def get_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail='user not found')
    return u


@router.get('/users/{user_id}/roles', response_model=list[str])
def get_user_roles(user_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    # return list of role names assigned to the user
    rows = db.query(models.Role.name).join(models.UserRole, models.Role.id == models.UserRole.role_id).filter(models.UserRole.user_id == user_id).all()
    return [r[0] for r in rows]


@router.post('/users/bulk')
def bulk_create_users(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    """Accepts a CSV file with columns: keycloak_id,email,first_name,last_name,dni,roles
    roles is optional and can be semicolon-separated role names.
    Returns per-row results.
    """
    import csv
    import io

    content = file.file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    results = []
    for idx, row in enumerate(reader, start=1):
        kc = row.get('keycloak_id')
        if not kc:
            results.append({'row': idx, 'status': 'error', 'message': 'missing keycloak_id'})
            continue
        # check existing
        u = db.query(models.User).filter(models.User.keycloak_id == kc).first()
        try:
            if not u:
                u = models.User(keycloak_id=kc, email=row.get('email'), first_name=row.get('first_name'), last_name=row.get('last_name'), dni=row.get('dni'))
                db.add(u)
                db.flush()
                created = True
            else:
                # update basic fields if provided
                if row.get('email'):
                    u.email = row.get('email')
                if row.get('first_name'):
                    u.first_name = row.get('first_name')
                if row.get('last_name'):
                    u.last_name = row.get('last_name')
                if row.get('dni'):
                    u.dni = row.get('dni')
                created = False

            # handle roles column
            roles_cell = row.get('roles') or ''
            roles = [r.strip() for r in roles_cell.split(';') if r.strip()]
            for rn in roles:
                role = db.query(models.Role).filter(models.Role.name == rn).first()
                if not role:
                    role = models.Role(name=rn)
                    db.add(role)
                    db.flush()
                ur = db.query(models.UserRole).filter(models.UserRole.user_id == u.id, models.UserRole.role_id == role.id).first()
                if not ur:
                    db.add(models.UserRole(user_id=u.id, role_id=role.id))

            db.commit()
            results.append({'row': idx, 'status': 'created' if created else 'updated', 'user_id': u.id})
        except Exception as e:
            db.rollback()
            results.append({'row': idx, 'status': 'error', 'message': str(e)})

    return {'results': results}


@router.put('/users/{user_id}', response_model=schemas.UserBase)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail='user not found')
    if payload.dni is not None:
        u.dni = payload.dni
    if payload.first_name is not None:
        u.first_name = payload.first_name
    if payload.last_name is not None:
        u.last_name = payload.last_name
    if payload.email is not None:
        u.email = payload.email
    db.commit()
    db.refresh(u)
    return u


@router.delete('/users/{user_id}')
def delete_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail='user not found')
    # Prevent deleting user if referenced by tickets/comments/movements/assignments
    from sqlalchemy import or_
    # Check references
    tcnt = db.query(models.Ticket).filter(or_(models.Ticket.client_user_id == user_id, models.Ticket.current_agent_id == user_id)).count()
    ccnt = db.query(models.TicketComment).filter(models.TicketComment.author_user_id == user_id).count()
    mcnt = db.query(models.TicketMovementLog).filter(models.TicketMovementLog.action_user_id == user_id).count()
    acost = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user_id).count()
    if any([tcnt, ccnt, mcnt, acost]):
        raise HTTPException(status_code=400, detail='Cannot delete user referenced by tickets/comments/movements/assignments')
    # safe to remove user_roles, user_groups
    db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete()
    db.query(models.UserGroup).filter(models.UserGroup.user_id == user_id).delete()
    db.delete(u)
    db.commit()
    return {'status': 'deleted'}


@router.post('/groups', response_model=schemas.GroupOut)
def create_group(payload: schemas.GroupCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    g = models.Group(name=payload.name, description=payload.description)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.get('/groups', response_model=list[schemas.GroupOut])
def list_groups(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    gs = db.query(models.Group).all()
    return gs


@router.post('/groups/{group_id}/users')
def add_user_to_group(group_id: int, payload: schemas.UserGroupAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    g = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail='Group not found')
    ug = db.query(models.UserGroup).filter(models.UserGroup.user_id == payload.user_id, models.UserGroup.group_id == group_id).first()
    if ug:
        return schemas.UserGroupOut(user_id=payload.user_id, group_id=group_id)
    ug = models.UserGroup(user_id=payload.user_id, group_id=group_id)
    db.add(ug)
    db.commit()
    return schemas.UserGroupOut(user_id=ug.user_id, group_id=ug.group_id)


@router.delete('/groups/{group_id}/users/{user_id}')
def remove_user_from_group(group_id: int, user_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    ug = db.query(models.UserGroup).filter(models.UserGroup.user_id == user_id, models.UserGroup.group_id == group_id).first()
    if not ug:
        raise HTTPException(status_code=404, detail='membership not found')
    db.delete(ug)
    db.commit()
    return {'status': 'removed'}


@router.post('/queues', response_model=schemas.QueueOut)
def create_queue(payload: schemas.QueueCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    q = models.Queue(name=payload.name, description=payload.description)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.get('/queues', response_model=list[schemas.QueueOut])
def list_queues(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    return db.query(models.Queue).all()


@router.put('/queues/{queue_id}', response_model=schemas.QueueOut)
def update_queue(queue_id: int, payload: schemas.QueueCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    q = db.query(models.Queue).filter(models.Queue.id == queue_id).first()
    if not q:
        raise HTTPException(status_code=404, detail='queue not found')
    if payload.name is not None:
        q.name = payload.name
    if payload.description is not None:
        q.description = payload.description
    db.commit()
    db.refresh(q)
    return q


@router.delete('/queues/{queue_id}')
def delete_queue(queue_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    q = db.query(models.Queue).filter(models.Queue.id == queue_id).first()
    if not q:
        raise HTTPException(status_code=404, detail='queue not found')
    # prevent deleting queue if tickets reference it
    cnt = db.query(models.Ticket).filter(models.Ticket.current_queue_id == q.id).count()
    if cnt > 0:
        raise HTTPException(status_code=400, detail='Cannot delete queue with existing tickets')
    db.delete(q)
    db.commit()
    return {'status': 'deleted'}


@router.get('/users')
def list_users(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    # Return a lightweight JSON-friendly list to avoid Pydantic response validation errors
    rows = db.query(models.User).all()
    out = []
    for u in rows:
        out.append({'id': u.id, 'keycloak_id': u.keycloak_id, 'first_name': u.first_name, 'last_name': u.last_name, 'email': u.email})
    return out


@router.get('/agent_assignments', response_model=list[schemas.AgentAssignmentOut])
def list_agent_assignments(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    a = db.query(models.AgentAssignment).all()
    return a


@router.get('/queue_permissions', response_model=list[schemas.QueuePermissionOut])
def list_queue_permissions(db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    q = db.query(models.QueuePermission).all()
    return q


@router.get('/groups/{group_id}/members', response_model=list[schemas.UserMinimalOut])
def list_group_members(group_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    ugs = db.query(models.UserGroup).filter(models.UserGroup.group_id == group_id).all()
    user_ids = [ug.user_id for ug in ugs]
    if not user_ids:
        return []
    users = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    # map to minimal structure
    return [ {'id': u.id, 'first_name': u.first_name, 'last_name': u.last_name} for u in users ]


@router.post('/queue_permissions')
def assign_queue_permission(payload: schemas.QueuePermissionAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    qp = db.query(models.QueuePermission).filter(models.QueuePermission.group_id == payload.group_id, models.QueuePermission.queue_id == payload.queue_id).first()
    if qp:
        return qp
    qp = models.QueuePermission(group_id=payload.group_id, queue_id=payload.queue_id)
    db.add(qp)
    db.commit()
    db.refresh(qp)
    return qp


@router.delete('/queue_permissions')
def remove_queue_permission(payload: schemas.QueuePermissionAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    qp = db.query(models.QueuePermission).filter(models.QueuePermission.group_id == payload.group_id, models.QueuePermission.queue_id == payload.queue_id).first()
    if not qp:
        raise HTTPException(status_code=404, detail='permission not found')
    db.delete(qp)
    db.commit()
    return {'status': 'removed'}


@router.post('/agents/assign')
def assign_agent(payload: schemas.AgentAssignmentCreate, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    aa = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == payload.agent_user_id, models.AgentAssignment.queue_id == payload.queue_id).first()
    if aa:
        return aa
    aa = models.AgentAssignment(agent_user_id=payload.agent_user_id, queue_id=payload.queue_id, access_level=payload.access_level)
    db.add(aa)
    db.commit()
    db.refresh(aa)
    return aa


@router.delete('/agents/assign/{agent_assignment_id}')
def unassign_agent(agent_assignment_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    aa = db.query(models.AgentAssignment).filter(models.AgentAssignment.id == agent_assignment_id).first()
    if not aa:
        raise HTTPException(status_code=404, detail='assignment not found')
    db.delete(aa)
    db.commit()
    return {'status': 'removed'}


@router.post('/roles/make_agent')
def make_agent_role(payload: schemas.UserRoleAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    # convenience wrapper to assign 'agent' role
    payload.role_name = payload.role_name or 'agent'
    return assign_role(payload, db, user)


@router.post('/roles/remove_agent')
def remove_agent_role(payload: schemas.UserRoleAssign, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    payload.role_name = payload.role_name or 'agent'
    return remove_role(payload, db, user)
