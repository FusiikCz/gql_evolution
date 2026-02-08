import asyncio
import dataclasses
import datetime
import typing
import strawberry
import json

import strawberry.types
from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
)    
from uoishelpers.resolvers import (
    getLoadersFromInfo, 
    createInputs2,

    InsertError, 
    Insert, 
    UpdateError, 
    Update, 
    DeleteError, 
    Delete,

    PageResolver,
    ScalarResolver,
    InputModelMixin
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from src.Utils.error_codes import get_error_code

# Forward references
ApiKeyGQLModel = typing.Annotated["ApiKeyGQLModel", strawberry.lazy(".ApiKeyGQLModel")]

@createInputs2
class EndpointConfigInputFilter:
    id: IDType
    name: str
    endpoint_type: str
    base_url: str
    is_active: bool
    api_key_id: IDType

@strawberry.federation.type(
    description="""Entity representing an Endpoint Configuration for AI model access.
Endpoint configurations define how to connect to AI model services (OpenAI, Azure OpenAI, custom endpoints).
Each configuration specifies base URL, endpoint type (chat/completions), model mappings, and authentication.
Endpoint configurations are linked to API keys via api_key_id for access control.
Example use cases:
- "Find endpoint configurations for OpenAI services"
- "Get all active endpoint configurations"
- "List endpoint configurations with model mappings"
Use EndpointConfigInputFilter with filters like name, endpoint_type, base_url, is_active, and nested api_key filters.""",
    keys=["id"]
)
class EndpointConfigGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).EndpointConfigModel

    @classmethod
    def from_dataclass(cls, db_row):
        """Override to convert model_mapping from dict to JSON string"""
        db_row_dict = dataclasses.asdict(db_row)
        # Convert model_mapping from dict to JSON string if it's a dict
        if 'model_mapping' in db_row_dict and isinstance(db_row_dict['model_mapping'], dict):
            db_row_dict['model_mapping'] = json.dumps(db_row_dict['model_mapping'])
        instance = cls(**db_row_dict)
        return instance

    # Basic identification
    name: str = strawberry.field(
        description="""Human-readable name for the endpoint configuration""",
        permission_classes=[OnlyForAuthentized]
    )
    
    endpoint_type: str = strawberry.field(
        description="""Type of endpoint: 'openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom'""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Connection configuration
    base_url: str = strawberry.field(
        description="""Base URL for the endpoint (e.g., 'https://api.openai.com/v1' or Azure endpoint)""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Model mapping configuration
    model_mapping: typing.Optional[str] = strawberry.field(
        default=None,
        description="""JSON mapping of OpenAI model names to Azure deployments: {'gpt-4o': 'gpt4o-prod', ...}""",
        permission_classes=[OnlyForAuthentized]
    )
    
    default_deployment: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Default deployment name to use when model is not in mapping""",
        permission_classes=[OnlyForAuthentized]
    )
    
    api_version: typing.Optional[str] = strawberry.field(
        default=None,
        description="""API version for Azure endpoints (e.g., '2024-12-01-preview')""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Shared token for endpoint access
    shared_token_hash: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Hashed shared token for this endpoint configuration""",
        permission_classes=[OnlyForAuthentized]
    )
    
    token_prefix: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Prefix of the shared token for quick lookup""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Status
    is_active: bool = strawberry.field(
        description="""Whether this endpoint configuration is active and can be used""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Metadata
    description: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Description of the endpoint configuration""",
        permission_classes=[OnlyForAuthentized]
    )
    
    # Relationships
    api_key_id: typing.Optional[IDType] = strawberry.field(
        default=None,
        description="""API key that owns or created this endpoint configuration - foreign key to ApiKey entity.
        @relation(to: ApiKeyGQLModel, field: 'id')""",
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="ApiKeyGQLModel")]
    )
    
    api_key: typing.Optional[ApiKeyGQLModel] = strawberry.field(
        description="""API key that owns or created this endpoint configuration""",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[ApiKeyGQLModel](fkey_field_name="api_key_id")
    )

# Query class
@strawberry.interface
class EndpointConfigQuery:
    endpoint_config_by_id: typing.Optional[EndpointConfigGQLModel] = strawberry.field(
        description="""Get an endpoint configuration by its id""",
        permission_classes=[OnlyForAuthentized],
        resolver=EndpointConfigGQLModel.load_with_loader
    )
    
    endpoint_config_page: typing.List[EndpointConfigGQLModel] = strawberry.field(
        description="""Returns list of endpoint configurations""",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[EndpointConfigGQLModel](whereType=EndpointConfigInputFilter)
    )

# Input types for mutations
@strawberry.input(
    description="""Input type for creating an Endpoint Configuration"""
)
class EndpointConfigInsertGQLModel(InputModelMixin):
    getLoader = EndpointConfigGQLModel.getLoader
    
    id: typing.Optional[IDType] = strawberry.field(
        description="""Endpoint Configuration id""",
        default=None
    )
    
    name: str = strawberry.field(
        description="""Human-readable name for the endpoint configuration"""
    )
    
    endpoint_type: str = strawberry.field(
        description="""Type of endpoint: 'openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom'""",
        default="custom"
    )
    
    base_url: str = strawberry.field(
        description="""Base URL for the endpoint"""
    )
    
    model_mapping: typing.Optional[str] = strawberry.field(
        description="""JSON mapping of OpenAI model names to Azure deployments""",
        default=None
    )
    
    default_deployment: typing.Optional[str] = strawberry.field(
        description="""Default deployment name""",
        default=None
    )
    
    api_version: typing.Optional[str] = strawberry.field(
        description="""API version for Azure endpoints""",
        default=None
    )
    
    shared_token_hash: typing.Optional[str] = strawberry.field(
        description="""Hashed shared token for this endpoint configuration""",
        default=None
    )
    
    token_prefix: typing.Optional[str] = strawberry.field(
        description="""Prefix of the shared token""",
        default=None
    )
    
    is_active: typing.Optional[bool] = strawberry.field(
        description="""Whether this endpoint configuration is active""",
        default=True
    )
    
    description: typing.Optional[str] = strawberry.field(
        description="""Description of the endpoint configuration""",
        default=None
    )
    
    api_key_id: typing.Optional[IDType] = strawberry.field(
        description="""API key that owns this endpoint configuration - foreign key to ApiKey entity.
        @relation(to: ApiKeyGQLModel, field: 'id')""",
        default=None
    )
    
    rbacobject_id: typing.Optional[IDType] = strawberry.field(
        description="""RBAC object ID""",
        default=None
    )
    
    createdby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for updating an Endpoint Configuration"""
)
class EndpointConfigUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""Endpoint Configuration id"""
    )
    
    lastchange: datetime.datetime = strawberry.field(
        description="""Last modification timestamp for optimistic locking.
        Must match the lastchange value from the current entity to prevent concurrent modification conflicts."""
    )
    
    name: typing.Optional[str] = strawberry.field(
        description="""Human-readable name for the endpoint configuration""",
        default=None
    )
    
    endpoint_type: typing.Optional[str] = strawberry.field(
        description="""Type of endpoint""",
        default=None
    )
    
    base_url: typing.Optional[str] = strawberry.field(
        description="""Base URL for the endpoint""",
        default=None
    )
    
    model_mapping: typing.Optional[str] = strawberry.field(
        description="""JSON mapping of OpenAI model names to Azure deployments""",
        default=None
    )
    
    default_deployment: typing.Optional[str] = strawberry.field(
        description="""Default deployment name""",
        default=None
    )
    
    api_version: typing.Optional[str] = strawberry.field(
        description="""API version for Azure endpoints""",
        default=None
    )
    
    shared_token_hash: typing.Optional[str] = strawberry.field(
        description="""Hashed shared token for this endpoint configuration""",
        default=None
    )
    
    token_prefix: typing.Optional[str] = strawberry.field(
        description="""Prefix of the shared token""",
        default=None
    )
    
    is_active: typing.Optional[bool] = strawberry.field(
        description="""Whether this endpoint configuration is active""",
        default=None
    )
    
    description: typing.Optional[str] = strawberry.field(
        description="""Description of the endpoint configuration""",
        default=None
    )
    
    api_key_id: typing.Optional[IDType] = strawberry.field(
        description="""API key that owns this endpoint configuration - foreign key to ApiKey entity.
        @relation(to: ApiKeyGQLModel, field: 'id')""",
        default=None
    )

# Mutation class
@strawberry.interface
class EndpointConfigMutation:
    @strawberry.mutation(
        description="""Creates a new endpoint configuration.
        
        Validates:
        - name must be provided
        - base_url must be a valid URL format
        - endpoint_type must be one of: 'openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom'
        
        Error codes:
        - INVALID_ENDPOINT_TYPE: endpoint_type is not valid
        - INVALID_BASE_URL: base_url format is invalid
        """,
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[InsertError, EndpointConfigGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[InsertError, EndpointConfigGQLModel](),
            RbacInsertProviderExtension[InsertError, EndpointConfigGQLModel](
                rbac_key_name="rbacobject_id"
            ),
            # LoadDataExtension není potřeba pro insert - nová entita ještě neexistuje
        ]
    )
    async def endpoint_config_insert(
        self,
        info: strawberry.types.Info,
        endpoint_config: EndpointConfigInsertGQLModel,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[EndpointConfigGQLModel, InsertError[EndpointConfigGQLModel]]:
        """
        Insert a new endpoint configuration.
        
        Args:
            info: GraphQL execution info
            endpoint_config: Endpoint configuration data
            
        Returns:
            Insert result with created endpoint configuration or error
        """
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            from src.DBDefinitions import EndpointConfigModel
            
            # Validate endpoint_type against allowed values
            # Supported types: OpenAI chat/completions, Azure chat/completions, custom endpoints
            valid_types = ['openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom']
            if endpoint_config.endpoint_type not in valid_types:
                return InsertError(
                    msg=f"Invalid endpoint_type: {endpoint_config.endpoint_type}. Must be one of: {', '.join(valid_types)}",
                    code=get_error_code("INVALID_ENDPOINT_TYPE"),
                    _input=endpoint_config
                )
            
            # Basic URL validation: must start with http:// or https://
            # Ensures endpoint URL is properly formatted for HTTP requests
            if endpoint_config.base_url and not (endpoint_config.base_url.startswith('http://') or endpoint_config.base_url.startswith('https://')):
                return InsertError(
                    msg=f"Invalid base_url format: {endpoint_config.base_url}. Must start with http:// or https://",
                    code=get_error_code("INVALID_BASE_URL"),
                    _input=endpoint_config
                )
            
            # Convert model_mapping from JSON string to dict if needed
            # Model mapping is stored as JSON in DB but can be provided as string or dict
            model_mapping = endpoint_config.model_mapping
            if isinstance(model_mapping, str):
                try:
                    model_mapping = json.loads(model_mapping)
                except json.JSONDecodeError:
                    return InsertError(
                        msg=f"Invalid model_mapping JSON: {model_mapping}",
                        code=get_error_code("INVALID_JSON"),
                        _input=endpoint_config
                    )
            
            # Create new endpoint configuration
            endpoint_data = {
                "name": endpoint_config.name,
                "endpoint_type": endpoint_config.endpoint_type,
                "base_url": endpoint_config.base_url,
                "model_mapping": model_mapping,
                "default_deployment": endpoint_config.default_deployment,
                "api_version": endpoint_config.api_version,
                "shared_token_hash": endpoint_config.shared_token_hash,
                "token_prefix": endpoint_config.token_prefix,
                "is_active": endpoint_config.is_active if endpoint_config.is_active is not None else True,
                "description": endpoint_config.description,
                "api_key_id": endpoint_config.api_key_id
            }
            
            # Add ID if provided
            if endpoint_config.id:
                endpoint_data["id"] = endpoint_config.id
                
            new_endpoint = EndpointConfigModel(**endpoint_data)
            
            session.add(new_endpoint)
            await session.commit()
            await session.refresh(new_endpoint)
            
            # Audit logging for critical operation
            import logging
            from uoishelpers.resolvers import getUserFromInfo
            logger = logging.getLogger(__name__)
            user = getUserFromInfo(info)
            user_id = user.id if user and hasattr(user, 'id') else (user.get('id') if user and isinstance(user, dict) else None)
            logger.info(
                f"AUDIT: endpoint_config_insert - user_id={user_id}, endpoint_config_id={new_endpoint.id}, "
                f"name={endpoint_config.name}, endpoint_type={endpoint_config.endpoint_type}, base_url={endpoint_config.base_url}"
            )
            
            return EndpointConfigGQLModel.from_dataclass(new_endpoint)

    @strawberry.mutation(
        description="""Updates an existing endpoint configuration.
        
        Error codes:
        - KEY_NOT_FOUND: Endpoint configuration with given ID not found
        - OPTIMISTIC_LOCKING_CONFLICT: Concurrent modification detected
        """,
        permission_classes=[OnlyForAuthentized]
    )
    async def endpoint_config_update(
        self, 
        info: strawberry.types.Info,
        endpoint_config: EndpointConfigUpdateGQLModel
    ) -> typing.Union[EndpointConfigGQLModel, UpdateError[EndpointConfigGQLModel]]:
        """
        Update an existing endpoint configuration.
        
        Args:
            info: GraphQL execution info
            endpoint_config: Endpoint configuration update data
            
        Returns:
            Update result with updated endpoint configuration or error
        """
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            from sqlalchemy import select
            from src.DBDefinitions import EndpointConfigModel
            
            # Find existing endpoint configuration
            stmt = select(EndpointConfigModel).where(EndpointConfigModel.id == endpoint_config.id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing is None:
                return UpdateError(
                    msg=f"Endpoint configuration with id {endpoint_config.id} not found",
                    code=get_error_code("KEY_NOT_FOUND"),
                    _input=endpoint_config
                )
            
            # Optimistic locking check
            if existing.lastchange != endpoint_config.lastchange:
                return UpdateError(
                    msg="Concurrent modification detected. Please refresh and try again.",
                    code=get_error_code("OPTIMISTIC_LOCKING_CONFLICT"),
                    _input=endpoint_config,
                    _entity=EndpointConfigGQLModel.from_dataclass(existing)
                )
            
            # Update fields
            if endpoint_config.name is not None:
                existing.name = endpoint_config.name
            if endpoint_config.endpoint_type is not None:
                existing.endpoint_type = endpoint_config.endpoint_type
            if endpoint_config.base_url is not None:
                existing.base_url = endpoint_config.base_url
            if endpoint_config.model_mapping is not None:
                # Convert to dict if string
                model_mapping = endpoint_config.model_mapping
                if isinstance(model_mapping, str):
                    try:
                        model_mapping = json.loads(model_mapping)
                    except json.JSONDecodeError:
                        return UpdateError(
                            msg=f"Invalid model_mapping JSON: {model_mapping}",
                            code=get_error_code("INVALID_JSON"),
                            _input=endpoint_config,
                            _entity=EndpointConfigGQLModel.from_dataclass(existing)
                        )
                existing.model_mapping = model_mapping
            if endpoint_config.default_deployment is not None:
                existing.default_deployment = endpoint_config.default_deployment
            if endpoint_config.api_version is not None:
                existing.api_version = endpoint_config.api_version
            if endpoint_config.shared_token_hash is not None:
                existing.shared_token_hash = endpoint_config.shared_token_hash
            if endpoint_config.token_prefix is not None:
                existing.token_prefix = endpoint_config.token_prefix
            if endpoint_config.is_active is not None:
                existing.is_active = endpoint_config.is_active
            if endpoint_config.description is not None:
                existing.description = endpoint_config.description
            if endpoint_config.api_key_id is not None:
                existing.api_key_id = endpoint_config.api_key_id
            
            await session.commit()
            await session.refresh(existing)
            
            # Audit logging for critical operation
            import logging
            from uoishelpers.resolvers import getUserFromInfo
            logger = logging.getLogger(__name__)
            user = getUserFromInfo(info)
            user_id = user.id if user and hasattr(user, 'id') else (user.get('id') if user and isinstance(user, dict) else None)
            logger.info(
                f"AUDIT: endpoint_config_update - user_id={user_id}, endpoint_config_id={endpoint_config.id}, "
                f"is_active={existing.is_active}"
            )
            
            return EndpointConfigGQLModel.from_dataclass(existing)

    @strawberry.mutation(
        description="""Deletes an endpoint configuration.
        
        Error codes:
        - KEY_NOT_FOUND: Endpoint configuration with given ID not found
        """,
        permission_classes=[OnlyForAuthentized]
    )
    async def endpoint_config_delete(
        self, 
        info: strawberry.types.Info,
        id: IDType
    ) -> typing.Optional[DeleteError[EndpointConfigGQLModel]]:
        """
        Delete an endpoint configuration.
        
        Args:
            info: GraphQL execution info
            id: Endpoint configuration ID to delete
            
        Returns:
            None on success, DeleteError on failure
        """
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            from sqlalchemy import select
            from src.DBDefinitions import EndpointConfigModel
            
            # Find existing endpoint configuration
            stmt = select(EndpointConfigModel).where(EndpointConfigModel.id == id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing is None:
                return DeleteError(
                    msg=f"Endpoint configuration with id {id} not found",
                    _input=None
                )
            
            # Store name for audit log before deletion
            name = existing.name
            endpoint_type = existing.endpoint_type
            
            await session.delete(existing)
            await session.commit()
            
            # Audit logging for critical operation
            import logging
            from uoishelpers.resolvers import getUserFromInfo
            logger = logging.getLogger(__name__)
            user = getUserFromInfo(info)
            user_id = user.id if user and hasattr(user, 'id') else (user.get('id') if user and isinstance(user, dict) else None)
            logger.info(
                f"AUDIT: endpoint_config_delete - user_id={user_id}, endpoint_config_id={id}, "
                f"name={name}, endpoint_type={endpoint_type}"
            )
            
            return None

