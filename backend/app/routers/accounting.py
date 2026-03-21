"""
Accounting Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.accounting import (
    Expense, Transaction, Remittance, AgentRemittance, 
    RemittanceStatus, ExpenseCategory
)
from app.schemas.accounting import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseListResponse,
    TransactionResponse, TransactionListResponse,
    RemittanceCreate, RemittanceResponse, RemittanceListResponse,
    AgentRemittanceResponse, AgentRemittanceListResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


# ==================== EXPENSES ====================

@router.get("/expenses", response_model=ExpenseListResponse)
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List expenses"""
    query = db.query(Expense).filter(Expense.business_id == current_user.business_id)
    
    if category:
        query = query.filter(Expense.category == category)
    if branch_id:
        query = query.filter(Expense.branch_id == branch_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    expenses = query.order_by(Expense.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [ExpenseResponse(
        id=e.id, business_id=e.business_id, branch_id=e.branch_id,
        category=e.category.value, amount=e.amount, description=e.description,
        expense_date=e.expense_date, payment_method=e.payment_method,
        payment_reference=e.payment_reference, recorded_by_user_id=e.recorded_by_user_id,
        approved_by_user_id=e.approved_by_user_id, approved_at=e.approved_at,
        receipt_url=e.receipt_url, notes=e.notes,
        created_at=e.created_at, updated_at=e.updated_at
    ) for e in expenses]
    
    return ExpenseListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    request: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create expense"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    expense = Expense(
        business_id=current_user.business_id,
        branch_id=request.branch_id,
        category=request.category,
        amount=request.amount,
        description=request.description,
        expense_date=request.expense_date,
        payment_method=request.payment_method,
        payment_reference=request.payment_reference,
        receipt_url=request.receipt_url,
        notes=request.notes,
        recorded_by_user_id=current_user.id
    )
    
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id, business_id=expense.business_id, branch_id=expense.branch_id,
        category=expense.category.value, amount=expense.amount,
        description=expense.description, expense_date=expense.expense_date,
        payment_method=expense.payment_method, payment_reference=expense.payment_reference,
        recorded_by_user_id=expense.recorded_by_user_id,
        approved_by_user_id=expense.approved_by_user_id, approved_at=expense.approved_at,
        receipt_url=expense.receipt_url, notes=expense.notes,
        created_at=expense.created_at, updated_at=expense.updated_at
    )


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get expense by ID"""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.business_id == current_user.business_id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return ExpenseResponse(
        id=expense.id, business_id=expense.business_id, branch_id=expense.branch_id,
        category=expense.category.value, amount=expense.amount,
        description=expense.description, expense_date=expense.expense_date,
        payment_method=expense.payment_method, payment_reference=expense.payment_reference,
        recorded_by_user_id=expense.recorded_by_user_id,
        approved_by_user_id=expense.approved_by_user_id, approved_at=expense.approved_at,
        receipt_url=expense.receipt_url, notes=expense.notes,
        created_at=expense.created_at, updated_at=expense.updated_at
    )


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    request: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update expense"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.business_id == current_user.business_id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    expense.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id, business_id=expense.business_id, branch_id=expense.branch_id,
        category=expense.category.value, amount=expense.amount,
        description=expense.description, expense_date=expense.expense_date,
        payment_method=expense.payment_method, payment_reference=expense.payment_reference,
        recorded_by_user_id=expense.recorded_by_user_id,
        approved_by_user_id=expense.approved_by_user_id, approved_at=expense.approved_at,
        receipt_url=expense.receipt_url, notes=expense.notes,
        created_at=expense.created_at, updated_at=expense.updated_at
    )


@router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete expense"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.business_id == current_user.business_id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    
    return {"success": True, "message": "Expense deleted"}


# ==================== TRANSACTIONS ====================

@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List transactions"""
    if not current_user.has_permission("accounting.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Transaction).filter(
        Transaction.business_id == current_user.business_id
    )
    
    total = query.count()
    offset = (page - 1) * page_size
    transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [TransactionResponse(
        id=t.id, account_id=t.account_id, business_id=t.business_id,
        transaction_type=t.transaction_type.value, amount=t.amount,
        reference_type=t.reference_type, reference_id=t.reference_id,
        description=t.description, transaction_date=t.transaction_date,
        recorded_by_user_id=t.recorded_by_user_id, balance_after=t.balance_after,
        created_at=t.created_at, updated_at=t.updated_at
    ) for t in transactions]
    
    return TransactionListResponse(
        items=items, total=total, page=page_size, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


# ==================== VENDOR REMITTANCES ====================

@router.get("/remittances", response_model=RemittanceListResponse)
async def list_remittances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List remittances"""
    query = db.query(Remittance).filter(
        Remittance.business_id == current_user.business_id
    )
    
    if vendor_id:
        query = query.filter(Remittance.vendor_id == vendor_id)
    if status:
        query = query.filter(Remittance.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    remittances = query.order_by(Remittance.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [RemittanceResponse(
        id=r.id, vendor_id=r.vendor_id, business_id=r.business_id,
        amount=r.amount, period_start=r.period_start, period_end=r.period_end,
        payment_method=r.payment_method, payment_reference=r.payment_reference,
        payment_date=r.payment_date, status=r.status.value,
        approved_by_user_id=r.approved_by_user_id, approved_at=r.approved_at,
        notes=r.notes, created_at=r.created_at, updated_at=r.updated_at
    ) for r in remittances]
    
    return RemittanceListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/remittances", response_model=RemittanceResponse, status_code=status.HTTP_201_CREATED)
async def create_remittance(
    request: RemittanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create remittance"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    remittance = Remittance(
        vendor_id=request.vendor_id,
        business_id=current_user.business_id,
        amount=request.amount,
        period_start=request.period_start,
        period_end=request.period_end,
        payment_method=request.payment_method,
        payment_reference=request.payment_reference,
        payment_date=request.payment_date,
        notes=request.notes
    )
    
    db.add(remittance)
    db.commit()
    db.refresh(remittance)
    
    return RemittanceResponse(
        id=remittance.id, vendor_id=remittance.vendor_id,
        business_id=remittance.business_id, amount=remittance.amount,
        period_start=remittance.period_start, period_end=remittance.period_end,
        payment_method=remittance.payment_method,
        payment_reference=remittance.payment_reference,
        payment_date=remittance.payment_date, status=remittance.status.value,
        approved_by_user_id=remittance.approved_by_user_id,
        approved_at=remittance.approved_at, notes=remittance.notes,
        created_at=remittance.created_at, updated_at=remittance.updated_at
    )


@router.get("/remittances/{remittance_id}", response_model=RemittanceResponse)
async def get_remittance(
    remittance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get remittance by ID"""
    remittance = db.query(Remittance).filter(
        Remittance.id == remittance_id,
        Remittance.business_id == current_user.business_id
    ).first()
    
    if not remittance:
        raise HTTPException(status_code=404, detail="Remittance not found")
    
    return RemittanceResponse(
        id=remittance.id, vendor_id=remittance.vendor_id,
        business_id=remittance.business_id, amount=remittance.amount,
        period_start=remittance.period_start, period_end=remittance.period_end,
        payment_method=remittance.payment_method,
        payment_reference=remittance.payment_reference,
        payment_date=remittance.payment_date, status=remittance.status.value,
        approved_by_user_id=remittance.approved_by_user_id,
        approved_at=remittance.approved_at, notes=remittance.notes,
        created_at=remittance.created_at, updated_at=remittance.updated_at
    )


@router.post("/remittances/{remittance_id}/approve")
async def approve_remittance(
    remittance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a remittance"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    remittance = db.query(Remittance).filter(
        Remittance.id == remittance_id,
        Remittance.business_id == current_user.business_id
    ).first()
    
    if not remittance:
        raise HTTPException(status_code=404, detail="Remittance not found")
    
    if remittance.status == RemittanceStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Remittance already completed")
    
    remittance.status = RemittanceStatus.COMPLETED
    remittance.approved_by_user_id = current_user.id
    remittance.approved_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Remittance approved"}


# ==================== AGENT REMITTANCES ====================

@router.get("/agent-remittances", response_model=AgentRemittanceListResponse)
async def list_agent_remittances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List agent remittances (COD collections)"""
    query = db.query(AgentRemittance).filter(
        AgentRemittance.business_id == current_user.business_id
    )
    
    if agent_id:
        query = query.filter(AgentRemittance.agent_id == agent_id)
    if status:
        query = query.filter(AgentRemittance.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    remittances = query.order_by(AgentRemittance.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [AgentRemittanceResponse(
        id=r.id, agent_id=r.agent_id, business_id=r.business_id,
        amount=r.amount, collected_at=r.collected_at,
        remitted_at=r.remitted_at, status=r.status.value,
        payment_method=r.payment_method, payment_reference=r.payment_reference,
        notes=r.notes, created_at=r.created_at, updated_at=r.updated_at
    ) for r in remittances]
    
    return AgentRemittanceListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/agent-remittances/{remittance_id}/confirm")
async def confirm_agent_remittance(
    remittance_id: int,
    payment_method: str = "cash",
    payment_reference: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm agent remittance"""
    if not current_user.has_permission("accounting.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    remittance = db.query(AgentRemittance).filter(
        AgentRemittance.id == remittance_id,
        AgentRemittance.business_id == current_user.business_id
    ).first()
    
    if not remittance:
        raise HTTPException(status_code=404, detail="Remittance not found")
    
    remittance.status = RemittanceStatus.COMPLETED
    remittance.remitted_at = datetime.utcnow()
    remittance.payment_method = payment_method
    remittance.payment_reference = payment_reference
    db.commit()
    
    return {"success": True, "message": "Agent remittance confirmed"}


# ==================== SUMMARY ====================

@router.get("/summary")
async def get_accounting_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get accounting summary"""
    if not current_user.has_permission("accounting.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Total expenses
    total_expenses = db.query(func.sum(Expense.amount)).filter(
        Expense.business_id == business_id
    ).scalar() or 0
    
    # Pending vendor remittances
    pending_vendor_remittances = db.query(func.sum(Remittance.amount)).filter(
        Remittance.business_id == business_id,
        Remittance.status == RemittanceStatus.PENDING
    ).scalar() or 0
    
    # Pending agent remittances
    pending_agent_remittances = db.query(func.sum(AgentRemittance.amount)).filter(
        AgentRemittance.business_id == business_id,
        AgentRemittance.status == RemittanceStatus.PENDING
    ).scalar() or 0
    
    # Expenses by category
    expenses_by_category = db.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        Expense.business_id == business_id
    ).group_by(Expense.category).all()
    
    return {
        "total_expenses": float(total_expenses),
        "pending_vendor_remittances": float(pending_vendor_remittances),
        "pending_agent_remittances": float(pending_agent_remittances),
        "expenses_by_category": {
            cat.value if hasattr(cat, 'value') else str(cat): float(amt) 
            for cat, amt in expenses_by_category
        }
    }
