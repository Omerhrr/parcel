"""
Accounting Models - Financial tracking
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class AccountType(str, enum.Enum):
    """Chart of accounts types"""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class TransactionType(str, enum.Enum):
    """Type of transaction"""
    DEBIT = "debit"
    CREDIT = "credit"


class ExpenseCategory(str, enum.Enum):
    """Categories for expenses"""
    FUEL = "fuel"
    SALARY = "salary"
    TRANSPORT = "transport"
    PACKAGING = "packaging"
    OFFICE_RENT = "office_rent"
    UTILITIES = "utilities"
    MAINTENANCE = "maintenance"
    MARKETING = "marketing"
    OTHER = "other"


class RemittanceStatus(str, enum.Enum):
    """Status of vendor remittance"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Account(Base, TimestampMixin, TenantMixin):
    """
    Account entity - chart of accounts for double-entry bookkeeping.
    Tracks all financial accounts for a business.
    """
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Account details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, unique=True)  # Account code
    account_type = Column(Enum(AccountType), nullable=False)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Balance (cached)
    balance = Column(Numeric(15, 2), default=0)
    
    # Status
    is_active = Column(Integer, default=1)
    
    # Relationships
    business = relationship("Business", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    parent = relationship("Account", remote_side=[id], backref="children", foreign_keys=[parent_id])
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type.value}')>"


class Transaction(Base, TimestampMixin):
    """
    Transaction entity - individual financial transactions.
    Records all money movements with double-entry references.
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    
    # Reference - what caused this transaction
    reference_type = Column(String(50), nullable=True)  # order, waybill, expense, remittance
    reference_id = Column(Integer, nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Date
    transaction_date = Column(String(50), nullable=True)  # Date
    
    # Who recorded it
    recorded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Balance after transaction
    balance_after = Column(Numeric(15, 2), nullable=True)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    business = relationship("Business")
    recorded_by = relationship("User")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type.value}', amount={self.amount})>"


class Expense(Base, TimestampMixin, TenantMixin):
    """
    Expense entity - business expenses.
    Tracks all business expenditures.
    """
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Expense details
    category = Column(Enum(ExpenseCategory), default=ExpenseCategory.OTHER, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    # Date
    expense_date = Column(String(50), nullable=True)
    
    # Payment
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # Who recorded it
    recorded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Approval (if needed)
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(String(50), nullable=True)
    
    # Receipt
    receipt_url = Column(String(500), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    branch = relationship("Branch", back_populates="expenses")
    recorded_by = relationship("User", foreign_keys=[recorded_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    
    def __repr__(self):
        return f"<Expense(id={self.id}, category='{self.category.value}', amount={self.amount})>"
    
    def get_category_display(self) -> str:
        """Get human-readable category"""
        category_map = {
            ExpenseCategory.FUEL: "Fuel",
            ExpenseCategory.SALARY: "Salary",
            ExpenseCategory.TRANSPORT: "Transport",
            ExpenseCategory.PACKAGING: "Packaging",
            ExpenseCategory.OFFICE_RENT: "Office Rent",
            ExpenseCategory.UTILITIES: "Utilities",
            ExpenseCategory.MAINTENANCE: "Maintenance",
            ExpenseCategory.MARKETING: "Marketing",
            ExpenseCategory.OTHER: "Other"
        }
        return category_map.get(self.category, self.category.value)


class VendorLedger(Base, TimestampMixin):
    """
    VendorLedger entity - tracks vendor balances.
    Records all credits (sales) and debits (payments/remittances) for vendors.
    """
    __tablename__ = "vendor_ledger"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Reference
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="SET NULL"), nullable=True)
    remittance_id = Column(Integer, ForeignKey("remittances.id", ondelete="SET NULL"), nullable=True)
    
    # Amounts
    credit = Column(Numeric(12, 2), default=0)  # Amount owed to vendor
    debit = Column(Numeric(12, 2), default=0)  # Amount paid to vendor
    balance = Column(Numeric(12, 2), default=0)  # Running balance
    
    # Description
    description = Column(Text, nullable=True)
    
    # Date
    entry_date = Column(String(50), nullable=True)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="ledger_entries")
    order = relationship("Order")
    waybill = relationship("Waybill")
    remittance = relationship("Remittance", back_populates="ledger_entries")
    
    def __repr__(self):
        return f"<VendorLedger(id={self.id}, vendor_id={self.vendor_id}, balance={self.balance})>"


class AgentCollection(Base, TimestampMixin):
    """
    AgentCollection entity - cash collected by agents.
    Tracks COD collections and remittance status.
    """
    __tablename__ = "agent_collections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("logistic_agents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Reference
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="SET NULL"), nullable=True)
    
    # Collection
    amount_collected = Column(Numeric(12, 2), default=0)
    collection_date = Column(String(50), nullable=True)
    
    # Remittance
    remitted = Column(Integer, default=0)  # 0 = Not remitted, 1 = Remitted
    remitted_at = Column(String(50), nullable=True)
    remittance_reference = Column(String(255), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    agent = relationship("LogisticAgent")
    order = relationship("Order")
    waybill = relationship("Waybill")
    
    def __repr__(self):
        return f"<AgentCollection(id={self.id}, agent_id={self.agent_id}, amount={self.amount_collected})>"


class Remittance(Base, TimestampMixin):
    """
    Remittance entity - payments to vendors.
    Tracks settlement of vendor balances.
    """
    __tablename__ = "remittances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Period
    period_start = Column(String(50), nullable=True)  # Start of period being remitted
    period_end = Column(String(50), nullable=True)  # End of period
    
    # Payment details
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    payment_date = Column(String(50), nullable=True)
    
    # Status
    status = Column(Enum(RemittanceStatus), default=RemittanceStatus.PENDING, nullable=False)
    
    # Approval
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(String(50), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="remittances")
    ledger_entries = relationship("VendorLedger", back_populates="remittance")
    approved_by = relationship("User")
    
    def __repr__(self):
        return f"<Remittance(id={self.id}, vendor_id={self.vendor_id}, amount={self.amount})>"
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            RemittanceStatus.PENDING: "Pending",
            RemittanceStatus.PROCESSING: "Processing",
            RemittanceStatus.COMPLETED: "Completed",
            RemittanceStatus.CANCELLED: "Cancelled"
        }
        return status_map.get(self.status, self.status.value)


class AgentRemittance(Base, TimestampMixin):
    """
    AgentRemittance entity - tracks when agents remit collected COD back to business.
    Separate from AgentCollection which tracks what they collected.
    """
    __tablename__ = "agent_remittances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("logistic_agents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Amount being remitted
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Collection period
    period_start = Column(String(50), nullable=True)
    period_end = Column(String(50), nullable=True)
    
    # When collected and remitted
    collected_at = Column(String(50), nullable=True)
    remitted_at = Column(String(50), nullable=True)
    
    # Status
    status = Column(Enum(RemittanceStatus), default=RemittanceStatus.PENDING, nullable=False)
    
    # Payment details
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    agent = relationship("LogisticAgent")
    
    def __repr__(self):
        return f"<AgentRemittance(id={self.id}, agent_id={self.agent_id}, amount={self.amount})>"
