from fastapi import APIRouter, Depends, HTTPException, Response, Body, Query
from fastapi import Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time
from sqlalchemy import and_, or_

from app.core.database import get_db
from app import models, schemas
from app.core.security import get_current_user, get_current_user_bypass, require_role
from app.core.config import settings
import json

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post('/categories', dependencies=[Depends(require_role('admin'))])
def create_category(payload: dict, db: Session = Depends(get_db)):
    name = payload.get('name')
    c = models.ActivityCategory(name=name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.post('/types', dependencies=[Depends(require_role('admin'))])
async def create_activity_type(request: Request, db: Session = Depends(get_db)):
    # support JSON body or query params for backward compatibility
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    # fallback to query params if fields missing
    qp = request.query_params
    name = payload.get('name') or qp.get('name')
    metadata = payload.get('metadata') or qp.get('metadata')
    fields = payload.get('fields') or []
    t = models.ActivityType(name=name, meta=metadata)
    db.add(t)
    db.flush()
    created_fields = []
    for f in fields:
        opts_json = None
        if f.get('options'):
            opts_json = json.dumps(f.get('options'))
        af = models.ActivityTypeField(activity_type_id=t.id, name=f.get('name'), field_type=f.get('field_type'), options=opts_json)
        db.add(af)
        db.flush()
        created_fields.append(af)
    db.commit()
    db.refresh(t)
    out_fields = []
    for f in created_fields:
        opts = None
        if f.options:
            opts = json.loads(f.options)
        out_fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
    return {'id': t.id, 'name': t.name, 'metadata': t.meta, 'fields': out_fields}


@router.get('/types')
def list_activity_types(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    tts = db.query(models.ActivityType).all()
    out = []
    for tt in tts:
        frows = db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == tt.id).all()
        fields = []
        for f in frows:
            opts = None
            if f.options:
                opts = json.loads(f.options)
            fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
        out.append({'id': tt.id, 'name': tt.name, 'metadata': tt.meta, 'fields': fields})
    return out


@router.patch('/types/{type_id}', dependencies=[Depends(require_role('admin'))])
def update_activity_type(type_id: int, payload: dict, db: Session = Depends(get_db)):
    at = db.query(models.ActivityType).filter(models.ActivityType.id == type_id).first()
    if not at:
        raise HTTPException(status_code=404, detail='ActivityType not found')
    if payload.get('name') is not None:
        at.name = payload.get('name')
    if payload.get('metadata') is not None:
        at.meta = payload.get('metadata')
    # replace fields if provided
    created_fields = []
    if 'fields' in payload:
        # delete existing field values and fields
        fids = [f.id for f in db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == at.id).all()]
        if fids:
            db.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.field_id.in_(fids)).delete(synchronize_session='fetch')
        db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == at.id).delete()
        for f in payload.get('fields', []):
            opts_json = None
            if f.get('options'):
                opts_json = json.dumps(f.get('options'))
            af = models.ActivityTypeField(activity_type_id=at.id, name=f.get('name'), field_type=f.get('field_type'), options=opts_json)
            db.add(af)
            db.flush()
            created_fields.append(af)
    db.commit()
    # build response
    frows = created_fields if created_fields else db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == at.id).all()
    fields = []
    for f in frows:
        opts = None
        if f.options:
            opts = json.loads(f.options)
        fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
    db.refresh(at)
    return {'id': at.id, 'name': at.name, 'metadata': at.meta, 'fields': fields}


@router.delete('/types/{type_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_activity_type(type_id: int, db: Session = Depends(get_db)):
    at = db.query(models.ActivityType).filter(models.ActivityType.id == type_id).first()
    if not at:
        raise HTTPException(status_code=404, detail='ActivityType not found')
    referenced = db.query(models.Activity).filter(models.Activity.activity_type_id == type_id).first()
    if referenced:
        if settings.TYPE_CASCADE_DELETE:
            # set referencing activities' activity_type_id to NULL
            db.query(models.Activity).filter(models.Activity.activity_type_id == type_id).update({'activity_type_id': None})
            db.commit()
        else:
            raise HTTPException(status_code=400, detail='Cannot delete ActivityType in use')
    db.delete(at)
    db.commit()
    return Response(status_code=204)


# Partial field edits for activity types
@router.post('/types/{type_id}/fields', dependencies=[Depends(require_role('admin'))])
def create_activity_field(type_id: int, payload: dict, db: Session = Depends(get_db)):
    at = db.query(models.ActivityType).filter(models.ActivityType.id == type_id).first()
    if not at:
        raise HTTPException(status_code=404, detail='ActivityType not found')
    opts_json = None
    if payload.get('options'):
        opts_json = json.dumps(payload.get('options'))
    af = models.ActivityTypeField(activity_type_id=type_id, name=payload.get('name'), field_type=payload.get('field_type'), options=opts_json)
    db.add(af)
    db.commit()
    db.refresh(af)
    opts = None
    if af.options:
        opts = json.loads(af.options)
    return {'id': af.id, 'name': af.name, 'field_type': af.field_type, 'options': opts}


@router.patch('/types/{type_id}/fields/{field_id}', dependencies=[Depends(require_role('admin'))])
def update_activity_field(type_id: int, field_id: int, payload: dict, db: Session = Depends(get_db)):
    af = db.query(models.ActivityTypeField).filter(models.ActivityTypeField.id == field_id, models.ActivityTypeField.activity_type_id == type_id).first()
    if not af:
        raise HTTPException(status_code=404, detail='Field not found')
    # if changing options/field_type, we should remove incompatible ActivityFieldValue rows
    old_type = af.field_type
    old_options = json.loads(af.options) if af.options else None
    if payload.get('name') is not None:
        af.name = payload.get('name')
    if payload.get('field_type') is not None:
        af.field_type = payload.get('field_type')
    if 'options' in payload:
        af.options = json.dumps(payload.get('options')) if payload.get('options') is not None else None
    db.commit()
    # cleanup values if necessary
    if payload.get('field_type') is not None and payload.get('field_type') != old_type:
        # remove all ActivityFieldValue rows for this field since semantics changed
        db.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.field_id == af.id).delete()
        db.commit()
    if payload.get('options') is not None and af.field_type == 'select' and old_options:
        new_opts = payload.get('options') or []
        # remove any values not in new options
        all_vals = db.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.field_id == af.id).all()
        for v in all_vals:
            if v.value not in new_opts:
                db.delete(v)
        db.commit()
    opts = None
    if af.options:
        opts = json.loads(af.options)
    return {'id': af.id, 'name': af.name, 'field_type': af.field_type, 'options': opts}


@router.delete('/types/{type_id}/fields/{field_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_activity_field(type_id: int, field_id: int, db: Session = Depends(get_db)):
    af = db.query(models.ActivityTypeField).filter(models.ActivityTypeField.id == field_id, models.ActivityTypeField.activity_type_id == type_id).first()
    if not af:
        raise HTTPException(status_code=404, detail='Field not found')
    # delete related values
    db.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.field_id == af.id).delete()
    db.delete(af)
    db.commit()
    return Response(status_code=204)


@router.post('/', dependencies=[Depends(get_current_user_bypass)])
def create_activity(payload: schemas.ActivityCreateRequest, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail='end_time must be after start_time')
    a = models.Activity(title=payload.title, category_id=payload.category_id, start_time=payload.start_time, end_time=payload.end_time, organizer_user_id=payload.organizer_user_id, activity_type_id=payload.activity_type_id, description=getattr(payload, 'description', None))
    db.add(a)
    db.flush()
    created_field_values = []
    # persist custom field values if provided
    if getattr(payload, 'custom_fields', None):
        # load field defs
        frows = db.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == payload.activity_type_id).all() if payload.activity_type_id else []
        field_defs = {f.id: f for f in frows}
        for cf in payload.custom_fields:
            field_id = cf.get('field_id')
            value = cf.get('value')
            if field_id:
                fdef = field_defs.get(field_id)
                if not fdef:
                    raise HTTPException(status_code=400, detail=f'Unknown custom field id {field_id}')
            else:
                fdef = None
                for fd in field_defs.values():
                    if fd.name == cf.get('name'):
                        fdef = fd
                        break
                if not fdef:
                    raise HTTPException(status_code=400, detail=f'Unknown custom field name {cf.get("name")}')
            # validate and normalize based on field type
            ft = fdef.field_type if fdef and getattr(fdef, 'field_type', None) else 'text'
            norm = None
            if ft == 'select':
                if fdef.options:
                    opts = json.loads(fdef.options)
                    if value not in opts:
                        raise HTTPException(status_code=400, detail=f'Invalid option for field {fdef.name}')
                norm = str(value) if value is not None else None
            elif ft == 'space':
                try:
                    sid = int(value)
                except Exception:
                    raise HTTPException(status_code=400, detail=f'Invalid space id for field {fdef.name}')
                sp = db.query(models.Space).filter(models.Space.id == sid).first()
                if not sp:
                    raise HTTPException(status_code=400, detail=f'Invalid space id for field {fdef.name}')
                norm = str(sid)
            elif ft == 'boolean':
                if isinstance(value, bool):
                    norm = 'true' if value else 'false'
                elif isinstance(value, str):
                    lv = value.strip().lower()
                    if lv in ('true', '1', 'yes', 'y'):
                        norm = 'true'
                    elif lv in ('false', '0', 'no', 'n'):
                        norm = 'false'
                    else:
                        raise HTTPException(status_code=400, detail=f'Invalid boolean value for field {fdef.name}')
                else:
                    raise HTTPException(status_code=400, detail=f'Invalid boolean value for field {fdef.name}')
            elif ft == 'number':
                try:
                    # allow ints and floats
                    _ = float(value)
                    norm = str(value)
                except Exception:
                    raise HTTPException(status_code=400, detail=f'Invalid numeric value for field {fdef.name}')
            elif ft == 'datetime':
                try:
                    dt = datetime.fromisoformat(value)
                    norm = dt.isoformat()
                except Exception:
                    raise HTTPException(status_code=400, detail=f'Invalid datetime format for field {fdef.name}; expected ISO format')
            elif ft == 'date':
                try:
                    d = date.fromisoformat(value)
                    norm = d.isoformat()
                except Exception:
                    raise HTTPException(status_code=400, detail=f'Invalid date format for field {fdef.name}; expected YYYY-MM-DD')
            elif ft == 'time':
                try:
                    t = time.fromisoformat(value)
                    norm = t.isoformat()
                except Exception:
                    raise HTTPException(status_code=400, detail=f'Invalid time format for field {fdef.name}; expected HH:MM[:SS]')
            else:
                # treat as text
                norm = str(value) if value is not None else None

            afv = models.ActivityFieldValue(activity_id=a.id, field_id=fdef.id, value=norm)
            db.add(afv)
            created_field_values.append(afv)
    db.commit()
    db.refresh(a)
    # attach custom fields to response
    out_custom = []
    for cfv in created_field_values:
        out_custom.append({'field_id': cfv.field_id, 'value': cfv.value})
    setattr(a, 'custom_fields', out_custom)
    return a


@router.post('/{activity_id}/space_bookings')
def book_space(activity_id: int, payload: Optional[schemas.SpaceBookingRequest] = Body(None), space_id: Optional[int] = Query(None), status: Optional[str] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    # Verify activity and space
    activity = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail='Activity not found')
    # allow either JSON body or query params
    if payload is None:
        if space_id is None:
            raise HTTPException(status_code=400, detail='space_id is required')
        payload = schemas.SpaceBookingRequest(space_id=space_id, status=status or 'Confirmed')
    space_id = payload.space_id
    space = db.query(models.Space).filter(models.Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')
    # Check for conflicting confirmed bookings on the same space
    overlapping = db.query(models.SpaceBooking).join(models.Activity, models.SpaceBooking.activity_id == models.Activity.id).filter(
        models.SpaceBooking.space_id == space_id,
        models.SpaceBooking.status == 'Confirmed',
        models.Activity.start_time < activity.end_time,
        models.Activity.end_time > activity.start_time
    ).first()
    if overlapping:
        raise HTTPException(status_code=409, detail='Space already booked for this time range')
    booking = models.SpaceBooking(activity_id=activity_id, space_id=space_id, status=payload.status or 'Confirmed')
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.post('/{activity_id}/stock_bookings')
def book_stock(activity_id: int, payload: schemas.StockBookingRequest, db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    activity = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail='Activity not found')
    item_id = payload.item_id
    item = db.query(models.StockItem).filter(models.StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')
    # Check item not in use for overlapping confirmed bookings
    overlapping = db.query(models.StockBooking).join(models.Activity, models.StockBooking.activity_id == models.Activity.id).filter(
        models.StockBooking.item_id == item_id,
        models.StockBooking.status == 'Confirmed',
        models.Activity.start_time < activity.end_time,
        models.Activity.end_time > activity.start_time
    ).first()
    if overlapping:
        raise HTTPException(status_code=409, detail='Stock item already booked for this time range')
    booking = models.StockBooking(activity_id=activity_id, item_id=item_id, status=payload.status or 'Confirmed')
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# Full Activity CRUD
@router.get('/{activity_id}', response_model=schemas.ActivityOut)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    act = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail='Activity not found')
    return act


@router.patch('/{activity_id}', dependencies=[Depends(require_role('activity-manager'))], response_model=schemas.ActivityOut)
def update_activity(activity_id: int, payload: schemas.ActivityUpdateRequest, db: Session = Depends(get_db)):
    act = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail='Activity not found')
    # apply updates
    new_start = payload.start_time if payload.start_time is not None else act.start_time
    new_end = payload.end_time if payload.end_time is not None else act.end_time
    if new_end <= new_start:
        raise HTTPException(status_code=400, detail='end_time must be after start_time')
    # check space booking conflicts if start/end changed
    # get any confirmed space bookings for this activity
    bookings = db.query(models.SpaceBooking).filter(models.SpaceBooking.activity_id == activity_id).all()
    for b in bookings:
        conflict = db.query(models.SpaceBooking).join(models.Activity, models.SpaceBooking.activity_id == models.Activity.id).filter(
            models.SpaceBooking.space_id == b.space_id,
            models.SpaceBooking.status == 'Confirmed',
            models.SpaceBooking.activity_id != activity_id,
            or_(
                and_(models.Activity.start_time <= new_start, models.Activity.end_time > new_start),
                and_(models.Activity.start_time < new_end, models.Activity.end_time >= new_end),
                and_(models.Activity.start_time >= new_start, models.Activity.end_time <= new_end),
            )
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail='Space booking conflict with updated time range')
    if payload.title is not None:
        act.title = payload.title
    if payload.category_id is not None:
        act.category_id = payload.category_id
    if payload.start_time is not None:
        act.start_time = payload.start_time
    if payload.end_time is not None:
        act.end_time = payload.end_time
    db.commit()
    db.refresh(act)
    return act


@router.delete('/{activity_id}', dependencies=[Depends(require_role('activity-manager'))], status_code=204)
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    act = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail='Activity not found')
    # prevent deletion if bookings exist
    space_ref = db.query(models.SpaceBooking).filter(models.SpaceBooking.activity_id == activity_id).first()
    stock_ref = db.query(models.StockBooking).filter(models.StockBooking.activity_id == activity_id).first()
    if space_ref or stock_ref:
        raise HTTPException(status_code=400, detail='Cannot delete activity with bookings')
    db.delete(act)
    db.commit()
    return Response(status_code=204)


@router.get('/', response_model=List[schemas.ActivityOut])
def list_activities(start: Optional[datetime] = None, end: Optional[datetime] = None, organizer: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Activity)
    if organizer:
        q = q.filter(models.Activity.organizer_user_id == organizer)
    if start and end:
        q = q.filter(or_(
            and_(models.Activity.start_time <= start, models.Activity.end_time > start),
            and_(models.Activity.start_time < end, models.Activity.end_time >= end),
            and_(models.Activity.start_time >= start, models.Activity.end_time <= end),
        ))
    elif start:
        q = q.filter(models.Activity.end_time > start)
    elif end:
        q = q.filter(models.Activity.start_time < end)
    return q.all()
