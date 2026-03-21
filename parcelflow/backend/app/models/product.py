"""
Product Model
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class Product(Base, TimestampMixin, TenantMixin):
    """
    Product entity - items that can be stored and sold.
    Products belong to vendors and are tracked in inventory.
    Supports dynamic pricing through pricing matrix.
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Product identification
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True, index=True)  # Stock Keeping Unit
    barcode = Column(String(100), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    
    # Physical attributes
    weight = Column(Numeric(10, 3), nullable=True)  # kg
    length = Column(Numeric(10, 2), nullable=True)  # cm
    width = Column(Numeric(10, 2), nullable=True)  # cm
    height = Column(Numeric(10, 2), nullable=True)  # cm
    
    # Pricing - Base prices (can be overridden by pricing matrix)
    cost_price = Column(Numeric(12, 2), default=0)  # Purchase price from vendor
    selling_price = Column(Numeric(12, 2), default=0)  # Default sale price
    
    # Pricing type: 'fixed' = single price, 'matrix' = quantity-based pricing
    pricing_type = Column(String(20), default="fixed")
    
    # Status
    is_active = Column(Integer, default=1)  # 1 = Active, 0 = Inactive
    
    # Image
    image_url = Column(String(500), nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="products")
    vendor = relationship("Vendor", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    pricing_matrix = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan", order_by="ProductPrice.min_quantity")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"
    
    @property
    def is_available(self) -> bool:
        """Check if product is available for sale"""
        return self.is_active == 1
    
    def get_price_for_quantity(self, quantity: int) -> float:
        """
        Get the price for a given quantity using pricing matrix.
        Falls back to selling_price if no matrix pricing exists.
        """
        if self.pricing_type == "fixed" or not self.pricing_matrix:
            return float(self.selling_price or 0)
        
        # Find applicable price tier
        for price_tier in self.pricing_matrix:
            if quantity >= price_tier.min_quantity:
                if price_tier.max_quantity is None or quantity <= price_tier.max_quantity:
                    return float(price_tier.price)
        
        # Fallback to base price
        return float(self.selling_price or 0)
    
    def get_total_price_for_quantity(self, quantity: int) -> float:
        """
        Calculate total price for quantity using pricing matrix.
        This handles bulk pricing (e.g., 2 units for 30,000 not 2 x 18,000).
        """
        if self.pricing_type == "fixed" or not self.pricing_matrix:
            return float(self.selling_price or 0) * quantity
        
        # Find applicable price tier and use the total_price if set
        for price_tier in self.pricing_matrix:
            if quantity >= price_tier.min_quantity:
                if price_tier.max_quantity is None or quantity <= price_tier.max_quantity:
                    # If tier has a total price defined, use it
                    if price_tier.total_price:
                        return float(price_tier.total_price)
                    # Otherwise calculate from unit price
                    return float(price_tier.price) * quantity
        
        # Fallback to base price
        return float(self.selling_price or 0) * quantity


class ProductPrice(Base, TimestampMixin):
    """
    ProductPrice entity - quantity-based pricing tiers.
    Supports dynamic pricing like:
    - 1 unit = 18,000 each
    - 2 units = 30,000 total (special deal)
    - 3 units = 45,000 total (special deal)
    - Buy 3 get 1 free
    """
    __tablename__ = "product_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Quantity range
    min_quantity = Column(Integer, default=1, nullable=False)  # Minimum quantity for this tier
    max_quantity = Column(Integer, nullable=True)  # Maximum quantity (null = no limit)
    
    # Pricing options
    price = Column(Numeric(12, 2), default=0)  # Unit price for this tier
    total_price = Column(Numeric(12, 2), nullable=True)  # Fixed total price for the quantity (e.g., 2 for 30,000)
    
    # Special offers
    is_buy_x_get_y = Column(Integer, default=0)  # Is this a "Buy X Get Y" deal?
    buy_quantity = Column(Integer, nullable=True)  # Buy this many
    get_quantity = Column(Integer, nullable=True)  # Get this many free
    
    # Label for display (e.g., "Buy 2 for ₦30,000", "Buy 3 Get 1 Free")
    label = Column(String(255), nullable=True)
    
    # Priority (higher = checked first)
    priority = Column(Integer, default=0)
    
    # Status
    is_active = Column(Integer, default=1)
    
    # Relationships
    product = relationship("Product", back_populates="pricing_matrix")
    
    def __repr__(self):
        return f"<ProductPrice(product_id={self.product_id}, qty={self.min_quantity}-{self.max_quantity}, price={self.price})>"
    
    @property
    def effective_unit_price(self) -> float:
        """Calculate effective unit price"""
        if self.total_price and self.min_quantity:
            return float(self.total_price) / self.min_quantity
        return float(self.price or 0)
