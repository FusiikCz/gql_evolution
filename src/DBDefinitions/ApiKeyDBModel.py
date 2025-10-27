import typing
import datetime
import sqlalchemy
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    Float,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .BaseModel import BaseModel, UUIDColumn, UUIDFKey, IDType

###########################################################################################################################
#
# API Key Database Model
# Represents API keys for accessing AI models with rate limiting and usage tracking
#
###########################################################################################################################

class ApiKeyModel(BaseModel):
    __tablename__ = "api_keys" 
    # TODO: nadefinovat do jsonu systemdata.json    
    # Basic identification
    name: Mapped[typing.Optional[str]] = mapped_column(String(120), nullable=True, default=None, comment="Human-readable name for the API key")
    prefix: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="", comment="Prefix of the API key for identification")
    key_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False, default="", comment="Hashed API key for security")

    # Status and activity
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Whether the API key is active and can be used")
    last_used_at: Mapped[typing.Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, comment="Last time the API key was used")

    # Time limits
    expires_at: Mapped[typing.Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, comment="Expiration date of the API key")

    # Rate limiting
    rate_limit_per_minute: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Maximum requests per minute")
    rate_limit_per_hour: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Maximum requests per hour")
    rate_limit_per_day: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Maximum requests per day")

    # Volume limits
    max_tokens_per_month: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Maximum tokens per month")
    max_cost_per_month: Mapped[typing.Optional[float]] = mapped_column(Float, nullable=True, default=None, comment="Maximum cost per month in USD")

    # Relationships
    user_id: Mapped[IDType] = UUIDFKey(ForeignKey("users.id"), comment="User who owns this API key")
    
    # Usage tracking relationship - removed to avoid SQLAlchemy issues
    # usages will be accessed via GraphQL resolvers instead

    # Indexes for performance
    __table_args__ = (
        Index('ix_api_keys_active_prefix', 'prefix', 'is_active'),
        Index('ix_api_keys_user_active', 'user_id', 'is_active'),
        Index('ix_api_keys_expires', 'expires_at'),
        Index('ix_api_keys_last_used', 'last_used_at'),
    )

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if the API key is expired"""
        if self.expires_at:
            return datetime.datetime.now(datetime.timezone.utc) > self.expires_at
        return False

    @hybrid_property
    def usage_count(self) -> int:
        """Get the number of times this API key has been used"""
        # This will be calculated via GraphQL resolvers or separate queries
        return 0

    @hybrid_property
    def total_usage_this_month(self) -> int:
        """Calculate total usage this month in tokens"""
        # This will be calculated via GraphQL resolvers or separate queries
        return 0

    @hybrid_property
    def total_cost_this_month(self) -> float:
        """Calculate total cost this month in USD"""
        # This will be calculated via GraphQL resolvers or separate queries
        return 0.0

    def __repr__(self):
        return f"<ApiKeyModel(id={self.id}, prefix={self.prefix}, name={self.name}, active={self.is_active})>"
