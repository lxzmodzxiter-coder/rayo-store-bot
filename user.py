from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum

# Clase base para todos los modelos de la base de datos
class Base(DeclarativeBase):
    pass

# Roles permitidos en la tienda
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"

# Estructura del Usuario
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    
    total_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    purchases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    referrals_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referral_earnings: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # Fechas automáticas
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
  
