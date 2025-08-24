from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.storage import storage
from app.core.security import get_current_user, get_current_user_bypass
from app import models

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post('/upload')
def upload_attachment(ticket_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    # Save file to local storage
    path = storage.save(file.file, file.filename)
    attachment = models.Attachment(ticket_id=ticket_id, file_name=file.filename, file_path=path, uploader_user_id=user.id)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
