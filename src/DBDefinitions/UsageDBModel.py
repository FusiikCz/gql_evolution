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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .BaseModel import BaseModel, UUIDColumn, UUIDFKey, IDType

###########################################################################################################################
#
# Usage Database Model
# Time-series optimized model for tracking API key usage with performance indexes
#
###########################################################################################################################

class UsageModel(BaseModel):
    __tablename__ = "usage"

    # Time-series primary key (timestamp-based for better performance)
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        index=True,
        comment="Timestamp of the usage record"
    )

    # API Key relationship
    api_key_id: Mapped[IDType] = UUIDFKey(ForeignKey("api_keys.id"), comment="API key that was used")
    # api_key relationship removed to avoid SQLAlchemy issues
    # api_key will be accessed via GraphQL resolvers instead

    # Request details
    route: Mapped[typing.Optional[str]] = mapped_column(String(128), nullable=True, default=None, comment="API route that was called")
    deployment: Mapped[typing.Optional[str]] = mapped_column(String(128), nullable=True, default=None, comment="AI model deployment used")
    status: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="HTTP status code of the response")
    stream: Mapped[bool] = mapped_column(Boolean, default=False, comment="Whether the request was streaming")

    # Token usage
    prompt_tokens: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Number of prompt tokens used")
    completion_tokens: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Number of completion tokens generated")
    total_tokens: Mapped[typing.Optional[int]] = mapped_column(Integer, nullable=True, default=None, comment="Total tokens used (prompt + completion)")

    # Cost tracking
    cost_usd: Mapped[typing.Optional[float]] = mapped_column(Float, nullable=True, default=None, comment="Cost of this request in USD")

    # Additional metadata
    model: Mapped[typing.Optional[str]] = mapped_column(String(128), nullable=True, default=None, comment="AI model name used")
    request_id: Mapped[typing.Optional[str]] = mapped_column(String(128), nullable=True, default=None, comment="Unique request identifier")
    user_agent: Mapped[typing.Optional[str]] = mapped_column(String(512), nullable=True, default=None, comment="User agent string")
    ip_address: Mapped[typing.Optional[str]] = mapped_column(String(45), nullable=True, default=None, comment="IP address of the request")

    # Error tracking
    error_code: Mapped[typing.Optional[str]] = mapped_column(String(64), nullable=True, default=None, comment="Error code if request failed")
    error_message: Mapped[typing.Optional[str]] = mapped_column(Text, nullable=True, default=None, comment="Error message if request failed")

    # Time-series optimized indexes
    __table_args__ = (
        # Primary time-series index for fast time-based queries
        Index('ix_usage_ts_api_key', 'ts', 'api_key_id'),
        
        # Index for API key usage queries
        Index('ix_usage_api_key_ts', 'api_key_id', 'ts'),
        
        # Index for cost tracking
        Index('ix_usage_cost_ts', 'cost_usd', 'ts'),
        
        # Index for error tracking
        Index('ix_usage_errors', 'error_code', 'ts'),
        
        # Index for model usage statistics
        Index('ix_usage_model_ts', 'model', 'ts'),
        
        # Index for route analytics
        Index('ix_usage_route_ts', 'route', 'ts'),
    )

    @hybrid_property
    def date(self) -> datetime.date:
        """Get the date of this usage record (for daily aggregations)"""
        return self.ts.date() if self.ts else None

    @hybrid_property
    def hour(self) -> int:
        """Get the hour of this usage record (for hourly aggregations)"""
        return self.ts.hour if self.ts else None

    @hybrid_property
    def is_successful(self) -> bool:
        """Check if the request was successful"""
        return self.status is not None and 200 <= self.status < 300

    @hybrid_property
    def is_error(self) -> bool:
        """Check if the request resulted in an error"""
        return self.error_code is not None or (self.status is not None and self.status >= 400)

    @hybrid_property
    def tokens_per_minute(self) -> typing.Optional[float]:
        """Calculate tokens per minute if this is a streaming request"""
        if not self.stream or not self.total_tokens:
            return None
        
        # Estimate duration based on total tokens (rough approximation)
        # This is a simplified calculation - in real implementation you'd track actual duration
        estimated_duration_minutes = max(1, self.total_tokens / 1000)  # Rough estimate
        return self.total_tokens / estimated_duration_minutes

    @hybrid_property
    def cost_per_token(self) -> typing.Optional[float]:
        """Calculate cost per token"""
        if not self.cost_usd or not self.total_tokens:
            return None
        return self.cost_usd / self.total_tokens

    def __repr__(self):
        return f"<UsageModel(id={self.id}, api_key_id={self.api_key_id}, ts={self.ts}, tokens={self.total_tokens}, cost={self.cost_usd})>"

    # Class methods for common queries
    @classmethod
    def get_usage_for_period(cls, api_key_id: IDType, start_date: datetime.datetime, end_date: datetime.datetime):
        """Get usage records for a specific API key within a date range"""
        return cls.query.filter(
            cls.api_key_id == api_key_id,
            cls.ts >= start_date,
            cls.ts <= end_date
        ).order_by(cls.ts.desc())

    @classmethod
    def get_daily_usage_summary(cls, api_key_id: IDType, date: datetime.date):
        """Get daily usage summary for a specific API key"""
        start_datetime = datetime.datetime.combine(date, datetime.time.min)
        end_datetime = datetime.datetime.combine(date, datetime.time.max)
        
        return cls.query.filter(
            cls.api_key_id == api_key_id,
            cls.ts >= start_datetime,
            cls.ts <= end_datetime
        )

    @classmethod
    def get_monthly_usage_summary(cls, api_key_id: IDType, year: int, month: int):
        """Get monthly usage summary for a specific API key"""
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)
        
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.min)
        
        return cls.query.filter(
            cls.api_key_id == api_key_id,
            cls.ts >= start_datetime,
            cls.ts < end_datetime
        )
