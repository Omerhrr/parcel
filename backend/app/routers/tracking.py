"""
Public Tracking Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.waybill import Waybill
from app.models.tracking import TrackingEvent
from app.schemas.waybill import WaybillTrackingResponse, TrackingEventResponse

router = APIRouter()


@router.get("/{waybill_number}", response_model=WaybillTrackingResponse)
async def track_shipment(
    waybill_number: str,
    db: Session = Depends(get_db)
):
    """
    Public tracking endpoint.
    No authentication required.
    """
    waybill = db.query(Waybill).filter(
        Waybill.waybill_number == waybill_number
    ).first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get tracking events
    events = db.query(TrackingEvent).filter(
        TrackingEvent.waybill_id == waybill.id,
        TrackingEvent.is_public == 1
    ).order_by(TrackingEvent.created_at.desc()).all()
    
    timeline = [TrackingEventResponse(
        id=e.id,
        status=e.status,
        title=e.title,
        description=e.description,
        location=e.location,
        is_public=e.is_public,
        created_at=e.created_at
    ) for e in events]
    
    return WaybillTrackingResponse(
        waybill_number=waybill.waybill_number,
        status=waybill.status.value,
        status_display=waybill.get_status_display(),
        sender_name=waybill.sender_name,
        receiver_name=waybill.receiver_name,
        receiver_address=waybill.receiver_address,
        receiver_city=waybill.receiver_city,
        estimated_delivery=waybill.estimated_delivery_date,
        timeline=timeline
    )
