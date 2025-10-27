import asyncio
import dataclasses
import datetime
import typing
import strawberry

import strawberry.types
from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
    SimpleInsertPermission, 
    SimpleUpdatePermission, 
    SimpleDeletePermission
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
    VectorResolver,
    ScalarResolver
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType, Relation

# Forward references pro lazy loading
UsageGQLModel = typing.Annotated["UsageGQLModel", strawberry.lazy(".UsageGQLModel")]
UsageInputFilter = typing.Annotated["UsageInputFilter", strawberry.lazy(".UsageGQLModel")]
UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]

@createInputs2
class ApiKeyInputFilter:
    id: IDType
    name: str
    prefix: str
    is_active: bool
    expires_at: datetime.datetime
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    max_tokens_per_month: int
    max_cost_per_month: float
    user_id: IDType
    last_used_at: datetime.datetime
    
    # Nested filter for usage relationship
    usage: UsageInputFilter = strawberry.field(
        description="""Usage filter operators for filtering by usage data
        Example: {"usage": {"total_tokens": {"_gt": 1000}}}
        """, 
        default=None
    )

@strawberry.federation.type(
    description="""Entity representing an API Key for accessing AI models""",
    keys=["id"]
)
class ApiKeyGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).ApiKeyModel

    # API Key specific fields
    name: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Human-readable name for the API key""",
        permission_classes=[OnlyForAuthentized]
    )

    prefix: str = strawberry.field(
        description="""Prefix of the API key for identification""",
        permission_classes=[OnlyForAuthentized]
    )

    is_active: bool = strawberry.field(
        description="""Whether the API key is active and can be used""",
        permission_classes=[OnlyForAuthentized]
    )

    expires_at: typing.Optional[datetime.datetime] = strawberry.field(
        default=None,
        description="""Expiration date of the API key""",
        permission_classes=[OnlyForAuthentized]
    )

    last_used_at: typing.Optional[datetime.datetime] = strawberry.field(
        default=None,
        description="""Last time the API key was used""",
        permission_classes=[OnlyForAuthentized]
    )

    # Rate limiting fields
    rate_limit_per_minute: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Maximum requests per minute""",
        permission_classes=[OnlyForAuthentized]
    )

    rate_limit_per_hour: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Maximum requests per hour""",
        permission_classes=[OnlyForAuthentized]
    )

    rate_limit_per_day: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Maximum requests per day""",
        permission_classes=[OnlyForAuthentized]
    )

    # Volume limits
    max_tokens_per_month: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Maximum tokens per month""",
        permission_classes=[OnlyForAuthentized]
    )

    max_cost_per_month: typing.Optional[float] = strawberry.field(
        default=None,
        description="""Maximum cost per month in USD""",
        permission_classes=[OnlyForAuthentized]
    )

    # Foreign key fields (following BaseGQLModel pattern)
    user_id: typing.Optional[IDType] = strawberry.field(
        default=None,
        description="""User who owns this API key""",
        permission_classes=[OnlyForAuthentized]
    )

    # Relationships
    user: typing.Optional[UserGQLModel] = strawberry.field(
        description="""User who owns this API key""",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="user_id")
    )

    usage: typing.List[UsageGQLModel] = strawberry.field(
        description="""Usage records for this API key""",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[UsageGQLModel](fkey_field_name="api_key_id", whereType=UsageInputFilter)
    )

    # Computed fields
    @strawberry.field(
        description="""Total usage this month in tokens""",
        permission_classes=[OnlyForAuthentized]
    )
    async def total_usage_this_month(self, info: strawberry.types.Info) -> int:
        # TODO: Implement calculation from usage data
        return 0

    @strawberry.field(
        description="""Total cost this month in USD""",
        permission_classes=[OnlyForAuthentized]
    )
    async def total_cost_this_month(self, info: strawberry.types.Info) -> float:
        # TODO: Implement calculation from usage data
        return 0.0

    @strawberry.field(
        description="""Whether the API key is expired""",
        permission_classes=[OnlyForAuthentized]
    )
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.datetime.now() > self.expires_at

    @strawberry.field(
        description="""Number of usage records""",
        permission_classes=[OnlyForAuthentized]
    )
    async def usage_count(self, info: strawberry.types.Info) -> int:
        # TODO: Implement count from usage data
        return 0

# Query interface
@strawberry.interface(
    description="""API Key queries"""
)
class ApiKeyQuery:
    api_key_by_id: typing.Optional[ApiKeyGQLModel] = strawberry.field(
        description="""Get an API key by its id""",
        permission_classes=[OnlyForAuthentized],
        resolver=ApiKeyGQLModel.load_with_loader
    )

    api_key_page: typing.List[ApiKeyGQLModel] = strawberry.field(
        description="""Get a page of API keys""",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[ApiKeyGQLModel](whereType=ApiKeyInputFilter)
    )

    @strawberry.field(
        description="""Get API keys owned by the current user""",
        permission_classes=[OnlyForAuthentized]
    )
    async def my_api_keys(self, info: strawberry.types.Info) -> typing.List[ApiKeyGQLModel]:
        from uoishelpers.resolvers import getUserFromInfo
        from sqlalchemy import select
        from src.DBDefinitions import ApiKeyModel
        
        # Get current user from context
        user = getUserFromInfo(info)
        if not user:
            return []
        
        # Get database session
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Query API keys for current user
            stmt = select(ApiKeyModel).where(
                ApiKeyModel.user_id == user.id
            ).order_by(ApiKeyModel.created.desc())
            
            result = await session.execute(stmt)
            db_rows = result.scalars().all()
            
            # Convert to GQL models
            return [ApiKeyGQLModel.from_dataclass(row) for row in db_rows]

# Input types for mutations
from uoishelpers.resolvers import InputModelMixin

@strawberry.input(
    description="""Input type for creating an API Key"""
)
class ApiKeyInsertGQLModel(InputModelMixin):
    getLoader = ApiKeyGQLModel.getLoader
    
    name: typing.Optional[str] = strawberry.field(
        description="""Human-readable name for the API key""",
        default=None
    )
    
    expires_at: typing.Optional[datetime.datetime] = strawberry.field(
        description="""Expiration date of the API key""",
        default=None
    )
    
    rate_limit_per_minute: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per minute""",
        default=None
    )
    
    rate_limit_per_hour: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per hour""",
        default=None
    )
    
    rate_limit_per_day: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per day""",
        default=None
    )
    
    max_tokens_per_month: typing.Optional[int] = strawberry.field(
        description="""Maximum tokens per month""",
        default=None
    )
    
    max_cost_per_month: typing.Optional[float] = strawberry.field(
        description="""Maximum cost per month in USD""",
        default=None
    )

    id: typing.Optional[IDType] = strawberry.field(
        description="""API Key id""",
        default=None
    )

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for updating an API Key"""
)
class ApiKeyUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""API Key id"""
    )
    
    lastchange: datetime.datetime = strawberry.field(
        description="timestamp"
    )
    
    name: typing.Optional[str] = strawberry.field(
        description="""Human-readable name for the API key""",
        default=None
    )
    
    is_active: typing.Optional[bool] = strawberry.field(
        description="""Whether the API key is active""",
        default=None
    )
    
    expires_at: typing.Optional[datetime.datetime] = strawberry.field(
        description="""Expiration date of the API key""",
        default=None
    )
    
    rate_limit_per_minute: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per minute""",
        default=None
    )
    
    rate_limit_per_hour: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per hour""",
        default=None
    )
    
    rate_limit_per_day: typing.Optional[int] = strawberry.field(
        description="""Maximum requests per day""",
        default=None
    )
    
    max_tokens_per_month: typing.Optional[int] = strawberry.field(
        description="""Maximum tokens per month""",
        default=None
    )
    
    max_cost_per_month: typing.Optional[float] = strawberry.field(
        description="""Maximum cost per month in USD""",
        default=None
    )

    changedby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for deleting an API Key"""
)
class ApiKeyDeleteGQLModel:
    id: IDType = strawberry.field(
        description="""API Key id"""
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""last change"""
    )

# Mutation interface
@strawberry.interface(
    description="""API Key mutations"""
)
class ApiKeyMutation:
    @strawberry.field(
        description="""Insert an API Key""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            UserAccessControlExtension[InsertError, ApiKeyGQLModel](
                roles=[
                    "api_key_administrator", 
                    "user"
                ]
            ),
            UserRoleProviderExtension[InsertError, ApiKeyGQLModel](),
            RbacProviderExtension[InsertError, ApiKeyGQLModel](),
            LoadDataExtension[InsertError, ApiKeyGQLModel]()
        ],
    )
    async def api_key_insert(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[ApiKeyGQLModel, InsertError[ApiKeyGQLModel]]:
        return await Insert[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.mutation(
        description="""Update an API Key""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            LoadDataExtension[UpdateError, ApiKeyGQLModel]()
        ],
    )
    async def api_key_update(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyUpdateGQLModel,
        db_row: typing.Any
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        return await Update[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.field(
        description="""Delete an API Key""",
        permission_classes=[
            SimpleDeletePermission[ApiKeyGQLModel](roles=["administrátor"])
        ]
    )   
    async def api_key_delete(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyDeleteGQLModel
    ) -> typing.Optional[DeleteError[ApiKeyGQLModel]]:
        return await Delete[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.mutation(
        description="""Deactivate an API Key (soft delete)""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            LoadDataExtension[UpdateError, ApiKeyGQLModel]()
        ],
    )
    async def api_key_deactivate(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyUpdateGQLModel,
        db_row: typing.Any
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        # Set is_active to False
        api_key.is_active = False
        return await Update[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.mutation(
        description="""Regenerate an API Key (create new key, keep metadata)""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            LoadDataExtension[UpdateError, ApiKeyGQLModel]()
        ],
    )
    async def api_key_regenerate(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyUpdateGQLModel,
        db_row: typing.Any
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        # TODO: Implement key regeneration logic
        # This should generate a new key but keep all other metadata
        return await Update[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)
