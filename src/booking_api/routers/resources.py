from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models import Resource
from ..schemas import ResourceCreate, ResourceOut, ResourceUpdate

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: ResourceCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    if db.scalar(select(Resource).where(Resource.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource name already exists")

    resource = Resource(**payload.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("", response_model=list[ResourceOut])
def list_resources(
    include_inactive: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    statement = select(Resource).order_by(Resource.name)
    if not include_inactive:
        statement = statement.where(Resource.is_active.is_(True))

    return list(db.scalars(statement.limit(limit).offset(offset)))


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.patch("/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Deactivate rather than delete, so existing bookings keep their history."""
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    resource.is_active = False
    db.commit()


