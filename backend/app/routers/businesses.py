"""
Businesses Router
ParcelFlow - Multi-tenant Logistics Platform
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.schemas.business import (
    BusinessCreate, BusinessUpdate, BusinessResponse, BusinessListResponse,
    EmailSettingsUpdate, EmailSettingsResponse
)
from app.utils.auth import get_current_user


logger = logging.getLogger(__name__)


router = APIRouter()


def get_business_settings(business: Business) -> dict:
    """Parse and return business settings"""
    if business.settings:
        try:
            return json.loads(business.settings)
        except json.JSONDecodeError:
            return {}
    return {}


def save_business_settings(business: Business, settings: dict):
    """Save settings to business"""
    business.settings = json.dumps(settings)


@router.get("", response_model=BusinessListResponse)
async def list_businesses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List businesses (super admin only)"""
    if not current_user.has_role("super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    query = db.query(Business)
    total = query.count()
    offset = (page - 1) * page_size
    businesses = query.offset(offset).limit(page_size).all()
    
    items = [BusinessResponse(
        id=b.id, name=b.name, slug=b.slug, email=b.email, phone=b.phone,
        address=b.address, city=b.city, country=b.country, plan=b.plan.value,
        status=b.status.value, logo_url=b.logo_url, primary_color=b.primary_color,
        subscription_start=b.subscription_start, subscription_end=b.subscription_end,
        created_at=b.created_at, updated_at=b.updated_at
    ) for b in businesses]
    
    return BusinessListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/current", response_model=BusinessResponse)
async def get_current_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's business"""
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return BusinessResponse(
        id=business.id, name=business.name, slug=business.slug, email=business.email,
        phone=business.phone, address=business.address, city=business.city,
        country=business.country, plan=business.plan.value, status=business.status.value,
        logo_url=business.logo_url, primary_color=business.primary_color,
        subscription_start=business.subscription_start, subscription_end=business.subscription_end,
        created_at=business.created_at, updated_at=business.updated_at
    )


@router.put("/current", response_model=BusinessResponse)
async def update_current_business(
    request: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's business"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(business, field, value)
    
    db.commit()
    db.refresh(business)
    
    return BusinessResponse(
        id=business.id, name=business.name, slug=business.slug, email=business.email,
        phone=business.phone, address=business.address, city=business.city,
        country=business.country, plan=business.plan.value, status=business.status.value,
        logo_url=business.logo_url, primary_color=business.primary_color,
        subscription_start=business.subscription_start, subscription_end=business.subscription_end,
        created_at=business.created_at, updated_at=business.updated_at
    )


@router.get("/current/email-settings", response_model=EmailSettingsResponse)
async def get_email_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get email settings for current business"""
    if not current_user.has_permission("settings.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    settings = get_business_settings(business)
    email_settings = settings.get('email', {})
    
    return EmailSettingsResponse(
        smtp_host=email_settings.get('smtp_host'),
        smtp_port=email_settings.get('smtp_port', 587),
        smtp_user=email_settings.get('smtp_user'),
        smtp_use_tls=email_settings.get('smtp_use_tls', True),
        email_from_name=email_settings.get('email_from_name', business.name),
        email_from_address=email_settings.get('email_from_address'),
        email_enabled=email_settings.get('email_enabled', True),
        is_configured=bool(email_settings.get('smtp_host') and email_settings.get('smtp_user'))
    )


@router.put("/current/email-settings", response_model=EmailSettingsResponse)
async def update_email_settings(
    request: EmailSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update email settings for current business"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    settings = get_business_settings(business)
    
    # Update email settings
    update_data = request.model_dump(exclude_unset=True)
    
    # Don't store empty passwords
    if 'smtp_password' in update_data and not update_data['smtp_password']:
        del update_data['smtp_password']
    
    if 'email' not in settings:
        settings['email'] = {}
    
    settings['email'].update(update_data)
    save_business_settings(business, settings)
    
    db.commit()
    db.refresh(business)
    
    logger.info(f"Email settings updated for business {business.id}")
    
    return EmailSettingsResponse(
        smtp_host=settings['email'].get('smtp_host'),
        smtp_port=settings['email'].get('smtp_port', 587),
        smtp_user=settings['email'].get('smtp_user'),
        smtp_use_tls=settings['email'].get('smtp_use_tls', True),
        email_from_name=settings['email'].get('email_from_name', business.name),
        email_from_address=settings['email'].get('email_from_address'),
        email_enabled=settings['email'].get('email_enabled', True),
        is_configured=bool(settings['email'].get('smtp_host') and settings['email'].get('smtp_user'))
    )


@router.post("/current/email-settings/test")
async def test_email_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a test email using current email settings"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    settings = get_business_settings(business)
    email_settings = settings.get('email', {})
    
    if not email_settings.get('smtp_host') or not email_settings.get('smtp_user'):
        raise HTTPException(
            status_code=400,
            detail="Email is not configured. Please configure SMTP settings first."
        )
    
    # Send test email
    from app.services.email import send_notification
    
    try:
        await send_notification(
            to=current_user.email,
            title="Test Email",
            message=f"This is a test email from {business.name}. Your email settings are working correctly!",
            action_url=None
        )
        
        return {
            "success": True,
            "message": f"Test email sent to {current_user.email}"
        }
    except Exception as e:
        logger.error(f"Failed to send test email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {str(e)}"
        )
