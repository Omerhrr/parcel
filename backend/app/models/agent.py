"""
Agent and Vehicle Models
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class AgentStatus(str, enum.Enum):
    """Status of a logistic agent"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFF_DUTY = "off_duty"
    ON_LEAVE = "on_leave"
    INACTIVE = "inactive"


class VehicleType(str, enum.Enum):
    """Type of vehicle"""
    BIKE = "bike"
    VAN = "van"
    TRUCK = "truck"
    CAR = "car"
    BICYCLE = "bicycle"
    THIRD_PARTY = "third_party"


class VehicleStatus(str, enum.Enum):
    """Status of a vehicle"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class LogisticAgent(Base, TimestampMixin, TenantMixin):
    """
    LogisticAgent entity - delivery personnel.
    Agents handle pickups and deliveries.
    """
    __tablename__ = "logistic_agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    
    # Agent information
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Identification
    employee_id = Column(String(50), nullable=True)
    national_id = Column(String(100), nullable=True)
    
    # Vehicle assignment
    vehicle_type = Column(Enum(VehicleType), default=VehicleType.BIKE, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    status = Column(Enum(AgentStatus), default=AgentStatus.AVAILABLE, nullable=False)
    
    # Performance metrics (cached)
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    rating = Column(Numeric(3, 2), default=0)  # 0-5 rating
    
    # Financials
    base_salary = Column(Numeric(12, 2), default=0)
    commission_rate = Column(Numeric(5, 2), default=0)  # Percentage
    
    # Current location
    current_latitude = Column(String(20), nullable=True)
    current_longitude = Column(String(20), nullable=True)
    last_location_update = Column(String(50), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="agents")
    branch = relationship("Branch", back_populates="agents")
    user = relationship("User")
    vehicle = relationship("Vehicle", back_populates="assigned_agent")
    pickups = relationship("Pickup", back_populates="agent")
    dispatches = relationship("Dispatch", back_populates="agent")
    
    def __repr__(self):
        return f"<LogisticAgent(id={self.id}, name='{self.name}', status='{self.status.value}')>"
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for assignment"""
        return self.status == AgentStatus.AVAILABLE
    
    @property
    def success_rate(self) -> float:
        """Calculate delivery success rate"""
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            AgentStatus.AVAILABLE: "Available",
            AgentStatus.BUSY: "Busy",
            AgentStatus.OFF_DUTY: "Off Duty",
            AgentStatus.ON_LEAVE: "On Leave",
            AgentStatus.INACTIVE: "Inactive"
        }
        return status_map.get(self.status, self.status.value)


class Vehicle(Base, TimestampMixin, TenantMixin):
    """
    Vehicle entity - transportation vehicles.
    Vehicles are assigned to agents for deliveries.
    """
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    
    # Vehicle details
    name = Column(String(255), nullable=False)
    registration_number = Column(String(50), nullable=True, unique=True)
    vehicle_type = Column(Enum(VehicleType), default=VehicleType.BIKE, nullable=False)
    
    # Specifications
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    color = Column(String(50), nullable=True)
    
    # Capacity
    max_weight_kg = Column(Numeric(10, 2), nullable=True)
    max_volume_cbm = Column(Numeric(10, 2), nullable=True)  # Cubic meters
    
    # Status
    status = Column(Enum(VehicleStatus), default=VehicleStatus.AVAILABLE, nullable=False)
    
    # Ownership
    is_owned = Column(Integer, default=1)  # 1 = Company owned, 0 = Third party
    owner_name = Column(String(255), nullable=True)
    owner_phone = Column(String(50), nullable=True)
    
    # Documentation
    insurance_expiry = Column(String(50), nullable=True)
    license_expiry = Column(String(50), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    assigned_agent = relationship("LogisticAgent", back_populates="vehicle")
    dispatches = relationship("Dispatch", back_populates="vehicle")
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, name='{self.name}', reg='{self.registration_number}')>"
    
    @property
    def is_available(self) -> bool:
        """Check if vehicle is available"""
        return self.status == VehicleStatus.AVAILABLE
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            VehicleStatus.AVAILABLE: "Available",
            VehicleStatus.IN_USE: "In Use",
            VehicleStatus.MAINTENANCE: "Maintenance",
            VehicleStatus.OUT_OF_SERVICE: "Out of Service"
        }
        return status_map.get(self.status, self.status.value)
