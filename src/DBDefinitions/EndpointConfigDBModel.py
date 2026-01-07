import typing
import datetime
import sqlalchemy
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .BaseModel import BaseModel, UUIDColumn, UUIDFKey, IDType

###########################################################################################################################
#
# Endpoint Configuration Database Model
# Represents OpenAI/Azure endpoint configurations with model mapping and shared tokens
#
###########################################################################################################################

class EndpointConfigModel(BaseModel):
    __tablename__ = "endpoint_configs"
    
    # Basic identification (must come before optional fields from BaseModel)
    name: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        default="",
        comment="Human-readable name for the endpoint configuration"
    )
    
    endpoint_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True,
        default="custom",
        comment="Type of endpoint: 'openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom'"
    )
    
    # Connection configuration
    base_url: Mapped[str] = mapped_column(
        String(500), 
        nullable=False,
        default="",
        comment="Base URL for the endpoint (e.g., 'https://api.openai.com/v1' or Azure endpoint)"
    )
    
    # Model mapping configuration
    model_mapping: Mapped[typing.Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="JSON mapping of OpenAI model names to Azure deployments: {'gpt-4o': 'gpt4o-prod', ...}"
    )
    
    default_deployment: Mapped[typing.Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        default=None,
        comment="Default deployment name to use when model is not in mapping"
    )
    
    api_version: Mapped[typing.Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="API version for Azure endpoints (e.g., '2024-12-01-preview')"
    )
    
    # Shared token for endpoint access
    shared_token_hash: Mapped[typing.Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        default=None,
        comment="Hashed shared token for this endpoint configuration"
    )
    
    token_prefix: Mapped[typing.Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        default=None,
        comment="Prefix of the shared token for quick lookup"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False, 
        index=True,
        comment="Whether this endpoint configuration is active and can be used"
    )
    
    # Metadata
    description: Mapped[typing.Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Description of the endpoint configuration"
    )
    
    # Relationships
    api_key_id: Mapped[typing.Optional[IDType]] = UUIDFKey(
        ForeignKey("api_keys.id"),
        comment="API key that owns or created this endpoint configuration (optional)"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_endpoint_configs_active_type', 'is_active', 'endpoint_type'),
        Index('ix_endpoint_configs_token_prefix', 'token_prefix'),
    )

    def __repr__(self):
        return f"<EndpointConfigModel(id={self.id}, name={self.name}, type={self.endpoint_type}, active={self.is_active})>"

