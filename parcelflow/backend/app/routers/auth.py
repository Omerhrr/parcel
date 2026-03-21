"""
Authentication Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import logging

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.models.role import Role
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    Token, PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest, RefreshTokenRequest
)
from app.schemas.user import UserResponse
from app.schemas.business import BusinessResponse
from app.utils.auth import (
    verify_password, hash_password, generate_tokens, decode_token,
    get_current_user
)
from app.services.email import send_password_reset, send_welcome, send_notification
from app.config import settings


logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns JWT tokens and user information.
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator."
        )
    
    # Check if user is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked. Please try again later."
        )
    
    # Verify password
    if not user.verify_password(request.password):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            from datetime import timedelta
            lock_until = datetime.utcnow() + timedelta(minutes=30)
            user.locked_until = lock_until.isoformat()
        
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow().isoformat()
    db.commit()
    
    # Generate tokens
    tokens = generate_tokens(user)
    
    # Get business
    business = db.query(Business).filter(Business.id == user.business_id).first()
    
    # Build response
    from app.schemas.auth import UserBrief, BusinessBrief, BranchBrief
    
    user_brief = UserBrief(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status.value,
        avatar_url=user.avatar_url
    )
    
    business_brief = BusinessBrief(
        id=business.id,
        name=business.name,
        slug=business.slug,
        plan=business.plan.value,
        status=business.status.value
    ) if business else None
    
    branch_brief = None
    if user.branch_id:
        from app.models.branch import Branch
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
        if branch:
            branch_brief = BranchBrief(
                id=branch.id,
                name=branch.name,
                code=branch.code,
                city=branch.city,
                currency=branch.currency
            )
    
    return LoginResponse(
        token=Token(**tokens),
        user=user_brief,
        business=business_brief,
        branch=branch_brief
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new business and admin user.
    Creates business, default branch, and admin user.
    """
    # Check if business email exists
    existing_business = db.query(Business).filter(
        Business.email == request.business_email
    ).first()
    if existing_business:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business with this email already exists"
        )
    
    # Check if user email exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate slug from business name
    from app.utils.helpers import slugify
    base_slug = slugify(request.business_name)
    slug = base_slug
    counter = 1
    while db.query(Business).filter(Business.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create business
    business = Business(
        name=request.business_name,
        slug=slug,
        email=request.business_email,
        phone=request.business_phone
    )
    db.add(business)
    db.flush()  # Get business ID
    
    # Create default branch
    from app.models.branch import Branch
    branch = Branch(
        business_id=business.id,
        name="Main Branch",
        code="HQ",
        is_headquarters=1
    )
    db.add(branch)
    db.flush()  # Get branch ID
    
    # Get admin role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    
    # Create admin user
    user = User(
        business_id=business.id,
        branch_id=branch.id,
        name=request.name,
        email=request.email,
        phone=request.phone,
        status="active",
        is_verified=True
    )
    user.set_password(request.password)
    if admin_role:
        user.roles.append(admin_role)
    
    db.add(user)
    db.commit()
    
    # Refresh to get relationships
    db.refresh(business)
    db.refresh(user)
    
    # Send welcome email in background
    login_url = f"{settings.FRONTEND_URL}/login"
    background_tasks.add_task(
        send_welcome,
        to=user.email,
        user_name=user.name,
        login_url=login_url,
        business_name=business.name
    )
    
    from app.schemas.auth import UserBrief, BusinessBrief
    
    return RegisterResponse(
        business=BusinessBrief(
            id=business.id,
            name=business.name,
            slug=business.slug,
            plan=business.plan.value,
            status=business.status.value
        ),
        user=UserBrief(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            status=user.status.value,
            avatar_url=user.avatar_url
        ),
        message="Registration successful. Please login to continue."
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    tokens = generate_tokens(user)
    
    return Token(**tokens)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user.
    In a production system, you might want to blacklist the token.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    """
    # Verify current password
    if not current_user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    # Update password
    current_user.set_password(request.new_password)
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    Sends an email with a reset link if the email exists.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        expires = datetime.utcnow() + timedelta(hours=1)
        user.password_reset_expires = expires.isoformat()
        db.commit()
        
        # Generate reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Send password reset email in background
        background_tasks.add_task(
            send_password_reset,
            to=user.email,
            reset_url=reset_url,
            user_name=user.name,
            expires_hours=1
        )
        
        logger.info(f"Password reset email queued for {user.email}")
    
    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Reset password with token.
    Validates the token and sets new password.
    """
    # Find user by reset token
    user = db.query(User).filter(
        User.password_reset_token == request.token
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    if user.password_reset_expires:
        try:
            expires_at = datetime.fromisoformat(user.password_reset_expires)
            if datetime.utcnow() > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reset token has expired"
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Validate passwords match
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Update password and clear reset token
    user.set_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    
    # Send confirmation email
    background_tasks.add_task(
        send_notification,
        to=user.email,
        title="Password Changed",
        message=f"Your password has been successfully changed. If you did not make this change, please contact support immediately.",
        action_url=f"{settings.FRONTEND_URL}/login",
        action_text="Login Now"
    )
    
    logger.info(f"Password reset successful for {user.email}")
    
    return {
        "success": True,
        "message": "Password has been reset successfully"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    """
    from app.schemas.user import RoleBrief
    from app.schemas.auth import BranchBrief
    
    roles = [
        RoleBrief(id=r.id, name=r.name, display_name=r.display_name)
        for r in current_user.roles
    ]
    
    branch = None
    if current_user.branch_id:
        from app.models.branch import Branch
        branch_obj = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
        if branch_obj:
            branch = BranchBrief(
                id=branch_obj.id,
                name=branch_obj.name,
                code=branch_obj.code,
                city=branch_obj.city,
                currency=branch_obj.currency
            )
    
    return UserResponse(
        id=current_user.id,
        business_id=current_user.business_id,
        branch_id=current_user.branch_id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        status=current_user.status.value,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        timezone=current_user.timezone,
        language=current_user.language,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        roles=roles,
        branch=branch
    )
