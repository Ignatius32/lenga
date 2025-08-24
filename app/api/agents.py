from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_bypass, require_role
from app.core.movement import record_ticket_movement
from app import models, schemas

router = APIRouter(prefix="/agents", tags=["agents"])


def require_agent_role():
    return require_role('agent')


@router.get('/queues', dependencies=[Depends(require_agent_role())])
def agent_queues(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    assignments = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id).all()
    queue_ids = [a.queue_id for a in assignments]
    queues = db.query(models.Queue).filter(models.Queue.id.in_(queue_ids)).all()
    return queues


@router.get('/tickets', dependencies=[Depends(require_agent_role())])
def agent_tickets(status: Optional[str] = None, priority: Optional[str] = None, unassigned: Optional[bool] = False, queue_id: Optional[int] = None, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    assignments = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id).all()
    queue_ids = [a.queue_id for a in assignments]
    if queue_id and queue_id not in queue_ids:
        raise HTTPException(status_code=403, detail='Not assigned to this queue')
    q = db.query(models.Ticket).filter(models.Ticket.current_queue_id.in_(queue_ids))
    if status:
        q = q.filter(models.Ticket.status == status)
    if priority:
        q = q.filter(models.Ticket.priority == priority)
    if unassigned:
        q = q.filter(models.Ticket.current_agent_id == None)
    if queue_id:
        q = q.filter(models.Ticket.current_queue_id == queue_id)
    return q.all()


@router.post('/tickets/{ticket_id}/claim', dependencies=[Depends(require_agent_role())])
def claim_ticket(ticket_id: int, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).with_for_update(of=models.Ticket).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # check assignment
    assignment = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail='Agent not assigned to this queue')
    if ticket.current_agent_id is not None:
        raise HTTPException(status_code=409, detail='Ticket already claimed')
    ticket.current_agent_id = user.id
    db.add(ticket)
    # create movement log and commit together
    record_ticket_movement(db, ticket, user.id, 'CLAIM', {'new_agent': user.id})
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post('/tickets/{ticket_id}/assign', dependencies=[Depends(require_agent_role())])
def assign_ticket(ticket_id: int, payload: schemas.AgentAssignRequest, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    target_agent_id = payload.target_agent_id
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).with_for_update(of=models.Ticket).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Ensure acting agent is assigned to this ticket's queue
    acting_assignment = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
    if not acting_assignment:
        raise HTTPException(status_code=403, detail='Acting agent not assigned to this queue')
    # Simple access level map
    rank = {'Tier 1': 1, 'Tier 2': 2, 'Manager': 3}
    def rank_of(a_id):
        a = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == a_id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
        if not a:
            return 0
        return rank.get(a.access_level, 0)

    if rank_of(user.id) < rank_of(target_agent_id) and rank_of(user.id) < 3:
        raise HTTPException(status_code=403, detail='Insufficient access to assign to that agent')
    old_agent = ticket.current_agent_id
    ticket.current_agent_id = target_agent_id
    db.add(ticket)
    record_ticket_movement(db, ticket, user.id, 'ASSIGN', {'old_agent': old_agent, 'new_agent': target_agent_id})
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post('/tickets/{ticket_id}/transfer', dependencies=[Depends(require_agent_role())])
def transfer_ticket(ticket_id: int, payload: schemas.TicketTransferRequest, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).with_for_update(of=models.Ticket).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Check acting agent assignment for source queue
    acting_assignment = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
    if not acting_assignment:
        raise HTTPException(status_code=403, detail='Acting agent not assigned to this queue')
    # Only managers or assignments with allow_transfer allowed
    access_level = acting_assignment.access_level or ''
    if access_level != 'Manager' and not getattr(acting_assignment, 'allow_transfer', False):
        raise HTTPException(status_code=403, detail='Insufficient access to transfer ticket')
    target_queue = db.query(models.Queue).filter(models.Queue.id == payload.target_queue_id).first()
    if not target_queue:
        raise HTTPException(status_code=404, detail='Target queue not found')
    old_queue = ticket.current_queue_id
    ticket.current_queue_id = payload.target_queue_id
    ticket.current_agent_id = None
    db.add(ticket)
    record_ticket_movement(db, ticket, user.id, 'TRANSFER_QUEUE', {'old_queue': old_queue, 'new_queue': payload.target_queue_id, 'reason': payload.reason})
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch('/tickets/{ticket_id}/status', dependencies=[Depends(require_agent_role())])
def change_status(ticket_id: int, payload: schemas.AgentStatusChangeRequest, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).with_for_update(of=models.Ticket).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Ensure agent is assigned to ticket queue
    assignment = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail='Agent not assigned to this queue')
    old_status = ticket.status
    ticket.status = payload.status
    if payload.resolved_at:
        ticket.resolved_at = payload.resolved_at
    db.add(ticket)
    record_ticket_movement(db, ticket, user.id, 'STATUS_CHANGE', {'old_status': old_status, 'new_status': payload.status})
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post('/tickets/{ticket_id}/comments', dependencies=[Depends(require_agent_role())])
def post_comment(ticket_id: int, payload: schemas.AgentCommentRequest, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Ensure agent is assigned to ticket queue
    assignment = db.query(models.AgentAssignment).filter(models.AgentAssignment.agent_user_id == user.id, models.AgentAssignment.queue_id == ticket.current_queue_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail='Agent not assigned to this queue')
    comment = models.TicketComment(ticket_id=ticket.id, author_user_id=user.id, comment_text=payload.comment_text, is_internal=payload.is_internal)
    db.add(comment)
    db.flush()
    record_ticket_movement(db, ticket, user.id, 'COMMENT', {'comment_id': comment.id, 'is_internal': payload.is_internal})
    db.commit()
    db.refresh(comment)
    return comment
