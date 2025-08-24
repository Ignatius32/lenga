from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models
from app import schemas
from app.core.security import get_current_user_bypass, require_role
from app.core.config import settings

router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.get('/buildings', response_model=List[schemas.BuildingOut])
def list_buildings(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    return db.query(models.Building).all()


@router.post('/buildings', response_model=schemas.BuildingOut, dependencies=[Depends(require_role('admin'))])
def create_building(b: schemas.BuildingCreate, db: Session = Depends(get_db)):
    building = models.Building(name=b.name, address=b.address)
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get('/spaces', response_model=List[schemas.SpaceOut])
def list_spaces(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    spaces = db.query(models.Space).all()
    space_ids = [s.id for s in spaces]
    # load all field values in one query
    frows = []
    if space_ids:
        frows = db.query(models.SpaceFieldValue).filter(models.SpaceFieldValue.space_id.in_(space_ids)).all()
    vals_by_space = {}
    for f in frows:
        vals_by_space.setdefault(f.space_id, []).append({'id': f.id, 'name': f.field_name, 'value': f.value})
    out = []
    for s in spaces:
        cf = vals_by_space.get(s.id, [])
        out.append({'id': s.id, 'building_id': s.building_id, 'name': s.name, 'type': s.type, 'capacity': s.capacity, 'space_template_id': s.space_template_id, 'custom_fields': cf})
    return out


@router.post('/spaces', response_model=schemas.SpaceOut, dependencies=[Depends(require_role('admin'))])
def create_space(s: schemas.SpaceCreate, db: Session = Depends(get_db)):
    space = models.Space(building_id=s.building_id, name=s.name, type=s.type, capacity=s.capacity, space_template_id=getattr(s, 'space_template_id', None))
    db.add(space)
    db.flush()
    # persist any custom fields
    if getattr(s, 'custom_fields', None):
        for f in s.custom_fields:
            try:
                fv = models.SpaceFieldValue(space_id=space.id if space.id else None, field_name=f.get('name'), value=str(f.get('value')))
                db.add(fv)
            except Exception:
                pass
    db.commit()
    db.refresh(space)
    # attach custom fields to response
    frows = db.query(models.SpaceFieldValue).filter(models.SpaceFieldValue.space_id == space.id).all()
    cf = [{'id': f.id, 'name': f.field_name, 'value': f.value} for f in frows]
    return {'id': space.id, 'building_id': space.building_id, 'name': space.name, 'type': space.type, 'capacity': space.capacity, 'space_template_id': space.space_template_id, 'custom_fields': cf}


@router.patch('/spaces/{space_id}', response_model=schemas.SpaceOut, dependencies=[Depends(require_role('admin'))])
def update_space(space_id: int, payload: dict, db: Session = Depends(get_db)):
    space = db.query(models.Space).filter(models.Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')
    # update basic fields
    if 'building_id' in payload:
        space.building_id = payload.get('building_id')
    if 'name' in payload:
        space.name = payload.get('name')
    if 'type' in payload:
        space.type = payload.get('type')
    if 'capacity' in payload:
        space.capacity = payload.get('capacity')
    if 'space_template_id' in payload:
        space.space_template_id = payload.get('space_template_id')

    # replace custom fields if provided
    if 'custom_fields' in payload:
        # delete existing values
        db.query(models.SpaceFieldValue).filter(models.SpaceFieldValue.space_id == space.id).delete()
        for f in payload.get('custom_fields') or []:
            try:
                fv = models.SpaceFieldValue(space_id=space.id, field_name=f.get('name'), value=str(f.get('value')) if f.get('value') is not None else None)
                db.add(fv)
            except Exception:
                pass

    db.commit()
    db.refresh(space)
    # attach custom fields to response
    frows = db.query(models.SpaceFieldValue).filter(models.SpaceFieldValue.space_id == space.id).all()
    cf = [{'id': f.id, 'name': f.field_name, 'value': f.value} for f in frows]
    return {'id': space.id, 'building_id': space.building_id, 'name': space.name, 'type': space.type, 'capacity': space.capacity, 'space_template_id': space.space_template_id, 'custom_fields': cf}


@router.delete('/spaces/{space_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_space(space_id: int, db: Session = Depends(get_db)):
    space = db.query(models.Space).filter(models.Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')
    # delete custom field values first
    db.query(models.SpaceFieldValue).filter(models.SpaceFieldValue.space_id == space.id).delete()
    db.delete(space)
    db.commit()
    return Response(status_code=204)


@router.get('/stock_items', response_model=List[schemas.StockItemOut])
def list_items(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    return db.query(models.StockItem).all()


@router.post('/stock_items', response_model=schemas.StockItemOut, dependencies=[Depends(require_role('admin'))])
def create_item(i: schemas.StockItemCreate, db: Session = Depends(get_db)):
    item = models.StockItem(category_id=i.category_id, name=i.name, sku=i.sku, description=i.description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# --- Types management ---
@router.post('/space_types', dependencies=[Depends(require_role('admin'))])
def create_space_type(name: str, metadata: str = None, db: Session = Depends(get_db)):
    st = models.SpaceType(name=name, meta=metadata)
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.get('/space_types')
def list_space_types(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    return db.query(models.SpaceType).all()


@router.patch('/space_types/{type_id}', dependencies=[Depends(require_role('admin'))])
def update_space_type(type_id: int, name: str = None, metadata: str = None, db: Session = Depends(get_db)):
    st = db.query(models.SpaceType).filter(models.SpaceType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='SpaceType not found')
    if name is not None:
        st.name = name
    if metadata is not None:
        st.meta = metadata
    db.commit()
    db.refresh(st)
    return st


@router.delete('/space_types/{type_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_space_type(type_id: int, db: Session = Depends(get_db)):
    st = db.query(models.SpaceType).filter(models.SpaceType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='SpaceType not found')
    referenced = db.query(models.Space).filter(models.Space.space_type_id == type_id).first()
    if referenced:
        if settings.TYPE_CASCADE_DELETE:
            db.query(models.Space).filter(models.Space.space_type_id == type_id).update({'space_type_id': None})
            db.commit()
        else:
            raise HTTPException(status_code=400, detail='Cannot delete SpaceType in use')
    db.delete(st)
    db.commit()
    return Response(status_code=204)


@router.post('/stock_types', dependencies=[Depends(require_role('admin'))])
def create_stock_type(name: str, metadata: str = None, db: Session = Depends(get_db)):
    st = models.StockType(name=name, meta=metadata)
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.get('/stock_types')
def list_stock_types(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    return db.query(models.StockType).all()


@router.patch('/stock_types/{type_id}', dependencies=[Depends(require_role('admin'))])
def update_stock_type(type_id: int, name: str = None, metadata: str = None, db: Session = Depends(get_db)):
    st = db.query(models.StockType).filter(models.StockType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='StockType not found')
    if name is not None:
        st.name = name
    if metadata is not None:
        st.meta = metadata
    db.commit()
    db.refresh(st)
    return st


@router.delete('/stock_types/{type_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_stock_type(type_id: int, db: Session = Depends(get_db)):
    st = db.query(models.StockType).filter(models.StockType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='StockType not found')
    referenced = db.query(models.StockItem).filter(models.StockItem.stock_type_id == type_id).first()
    if referenced:
        if settings.TYPE_CASCADE_DELETE:
            db.query(models.StockItem).filter(models.StockItem.stock_type_id == type_id).update({'stock_type_id': None})
            db.commit()
        else:
            raise HTTPException(status_code=400, detail='Cannot delete StockType in use')
    db.delete(st)
    db.commit()
    return Response(status_code=204)


# --- Space template management ---
@router.post('/space_templates', dependencies=[Depends(require_role('admin'))])
def create_space_template(payload: dict, db: Session = Depends(get_db)):
    name = payload.get('name')
    desc = payload.get('description')
    st = models.SpaceTemplate(name=name, description=desc)
    db.add(st)
    db.flush()
    created_fields = []
    for f in payload.get('fields', []) or []:
        opts = None
        if f.get('options'):
            import json as _json
            opts = _json.dumps(f.get('options'))
        sf = models.SpaceTemplateField(space_template_id=st.id, name=f.get('name'), field_type=f.get('field_type'), options=opts)
        db.add(sf)
        db.flush()
        created_fields.append(sf)
    db.commit()
    db.refresh(st)
    out_fields = []
    import json as _json
    for f in created_fields:
        opts = None
        if f.options:
            opts = _json.loads(f.options)
        out_fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
    return {'id': st.id, 'name': st.name, 'description': st.description, 'fields': out_fields}


@router.get('/space_templates')
def list_space_templates(db: Session = Depends(get_db), user=Depends(get_current_user_bypass)):
    tts = db.query(models.SpaceTemplate).all()
    out = []
    import json as _json
    for tt in tts:
        frows = db.query(models.SpaceTemplateField).filter(models.SpaceTemplateField.space_template_id == tt.id).all()
        fields = []
        for f in frows:
            opts = None
            if f.options:
                opts = _json.loads(f.options)
            fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
        out.append({'id': tt.id, 'name': tt.name, 'description': tt.description, 'fields': fields})
    return out


@router.patch('/space_templates/{template_id}', dependencies=[Depends(require_role('admin'))])
def update_space_template(template_id: int, payload: dict, db: Session = Depends(get_db)):
    st = db.query(models.SpaceTemplate).filter(models.SpaceTemplate.id == template_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='SpaceTemplate not found')
    if payload.get('name') is not None:
        st.name = payload.get('name')
    if payload.get('description') is not None:
        st.description = payload.get('description')
    # replace fields if provided
    created_fields = []
    if 'fields' in payload:
        fids = [f.id for f in db.query(models.SpaceTemplateField).filter(models.SpaceTemplateField.space_template_id == st.id).all()]
        if fids:
            db.query(models.SpaceTemplateField).filter(models.SpaceTemplateField.space_template_id == st.id).delete()
        for f in payload.get('fields', []):
            opts = None
            if f.get('options'):
                import json as _json
                opts = _json.dumps(f.get('options'))
            sf = models.SpaceTemplateField(space_template_id=st.id, name=f.get('name'), field_type=f.get('field_type'), options=opts)
            db.add(sf)
            db.flush()
            created_fields.append(sf)
    db.commit()
    db.refresh(st)
    # build response
    import json as _json
    frows = created_fields if created_fields else db.query(models.SpaceTemplateField).filter(models.SpaceTemplateField.space_template_id == st.id).all()
    fields = []
    for f in frows:
        opts = None
        if f.options:
            opts = _json.loads(f.options)
        fields.append({'id': f.id, 'name': f.name, 'field_type': f.field_type, 'options': opts})
    return {'id': st.id, 'name': st.name, 'description': st.description, 'fields': fields}


@router.delete('/space_templates/{template_id}', dependencies=[Depends(require_role('admin'))], status_code=204)
def delete_space_template(template_id: int, db: Session = Depends(get_db)):
    st = db.query(models.SpaceTemplate).filter(models.SpaceTemplate.id == template_id).first()
    if not st:
        raise HTTPException(status_code=404, detail='SpaceTemplate not found')
    referenced = db.query(models.Space).filter(models.Space.space_template_id == template_id).first()
    if referenced:
        raise HTTPException(status_code=400, detail='Cannot delete SpaceTemplate in use')
    # delete fields
    db.query(models.SpaceTemplateField).filter(models.SpaceTemplateField.space_template_id == st.id).delete()
    db.delete(st)
    db.commit()
    return Response(status_code=204)
