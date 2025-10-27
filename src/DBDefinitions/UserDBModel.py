import typing
import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Index
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.sql import func

from .BaseModel import BaseModel, IDType
from .BaseModel import UUIDFKey


class UserModel(BaseModel):
    """
    User model pro Task 11 - externí uživatelé systému
    
    Reprezentuje uživatele, kteří vlastní API klíče a mají přístup k AI modelům.
    Externí uživatel - není součástí hlavního systému, ale má vlastní API klíče.
    """
    __tablename__ = "users"
    
    # Základní informace o uživateli
    name: Mapped[typing.Optional[str]] = mapped_column(
        String(120), 
        nullable=True, 
        default=None,
        comment="Display name of the user"
    )
    
    email: Mapped[typing.Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        default=None,
        index=True,
        comment="Email address of the user"
    )
    
    # Autentizace a autorizace
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Whether the user account is active"
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Whether the user email is verified"
    )
    
    # Metadata
    last_login_at: Mapped[typing.Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True, 
        default=None,
        comment="Last time the user logged in"
    )
    
    login_count: Mapped[typing.Optional[int]] = mapped_column(
        default=0,
        nullable=True,
        comment="Total number of logins"
    )
    
    # Externí identifikátory (pro integraci s jinými systémy)
    external_string: Mapped[typing.Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        default=None,
        comment="External system user ID"
    )
    
    external_provider: Mapped[typing.Optional[str]] = mapped_column(
        String(64), 
        nullable=True, 
        default=None,
        comment="External provider (e.g., 'google', 'microsoft', 'azure')"
    )
    
    # Poznámky a metadata
    notes: Mapped[typing.Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        default=None,
        comment="Administrative notes about the user"
    )
    
    # Timezone a lokalizace
    timezone: Mapped[typing.Optional[str]] = mapped_column(
        String(64), 
        nullable=True, 
        default=None,
        comment="User's timezone (e.g., 'Europe/Prague')"
    )
    
    # API limits (globální limity pro uživatele)
    max_api_keys: Mapped[typing.Optional[int]] = mapped_column(
        default=10,
        nullable=True,
        comment="Maximum number of API keys this user can have"
    )
    
    # Indexy pro optimalizaci dotazů
    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
        Index('ix_users_external_string', 'external_string'),
        Index('ix_users_last_login', 'last_login_at'),
        Index('ix_users_created', 'created'),
        Index('ix_users_active_created', 'is_active', 'created'),
    )
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email}, name={self.name}, active={self.is_active})>"
