from typing import Dict
from sqlalchemy.orm import Session
from app.models.models import TicketMovementLog, Ticket
import json


def record_ticket_movement(db: Session, ticket: Ticket, action_user_id: int, action_type: str, details: Dict):
    """Create a movement log entry within the current transaction. Does not commit.

    Caller should commit the transaction. The function will flush to ensure `entry.id` is available.
    """
    entry = TicketMovementLog(
        ticket_id=ticket.id,
        action_user_id=action_user_id,
        action_type=action_type,
        details=json.dumps(details)
    )
    db.add(entry)
    # flush to populate PK without committing
    db.flush()
    return entry
