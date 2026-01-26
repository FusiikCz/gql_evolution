import dataclasses
import datetime
import typing
import strawberry

import strawberry.types
from uoishelpers.gqlpermissions import (
    OnlyForAuthentized
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
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from src.Utils.api_key_utils import generate_api_key
from src.Utils.error_codes import get_error_code

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
    description="""Entity representing an API Key for accessing AI models with rate limiting and usage tracking.
API keys are used to authenticate and authorize access to AI services like OpenAI, Azure OpenAI, etc.
Each API key belongs to a user and has configurable rate limits (per minute, hour, day).
API keys can have expiration dates and usage quotas (max tokens, max cost per month).
Usage is tracked in UsageGQLModel entities linked via api_key_id.
Example use cases:
- "List all API keys for current user"
- "Find active API keys expiring soon"
- "Get API key usage statistics"
- "Filter API keys by usage patterns"
Use ApiKeyInputFilter with filters like name, is_active, expires_at, and nested usage filters.""",
    keys=["id"]
)
class ApiKeyGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).ApiKeyModel

    # API Key specific fields - Order must match DBModel EXACTLY
    # name first (from DBModel)
    name: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Human-readable name for the API key""",
        permission_classes=[OnlyForAuthentized]
    )
    
    prefix: str = strawberry.field(
        description="""Prefix of the API key for identification""",
        permission_classes=[OnlyForAuthentized]
    )

    key_hash: str = strawberry.field(
        description="""Hash of the API key for secure storage""",
        permission_classes=[OnlyForAuthentized]
    )

    is_active: bool = strawberry.field(
        description="""Whether the API key is active and can be used""",
        permission_classes=[OnlyForAuthentized]
    )

    last_used_at: typing.Optional[datetime.datetime] = strawberry.field(
        default=None,
        description="""Last time the API key was used""",
        permission_classes=[OnlyForAuthentized]
    )

    expires_at: typing.Optional[datetime.datetime] = strawberry.field(
        default=None,
        description="""Expiration date of the API key""",
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
        description="""User who owns this API key - foreign key to User entity.
        @relation(to: UserGQLModel, field: 'id')""",
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="UserGQLModel")]
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
        from sqlalchemy import select, func
        from src.DBDefinitions import UsageModel
        
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            stmt = select(func.coalesce(func.sum(UsageModel.total_tokens), 0)).where(
                UsageModel.api_key_id == self.id,
                UsageModel.ts >= start_of_month
            )
            
            result = await session.execute(stmt)
            total = result.scalar()
            return int(total or 0)

    @strawberry.field(
        description="""Total cost this month in USD""",
        permission_classes=[OnlyForAuthentized]
    )
    async def total_cost_this_month(self, info: strawberry.types.Info) -> float:
        from sqlalchemy import select, func
        from src.DBDefinitions import UsageModel
        
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            stmt = select(func.coalesce(func.sum(UsageModel.cost_usd), 0.0)).where(
                UsageModel.api_key_id == self.id,
                UsageModel.ts >= start_of_month
            )
            
            result = await session.execute(stmt)
            total = result.scalar()
            return float(total or 0.0)

    @strawberry.field(
        description="""True when monthly token usage exceeds max_tokens_per_month""",
        permission_classes=[OnlyForAuthentized]
    )
    async def is_over_token_limit(self, info: strawberry.types.Info) -> bool:
        if self.max_tokens_per_month is None:
            return False
        total = await self.total_usage_this_month(info)
        return total > self.max_tokens_per_month

    @strawberry.field(
        description="""True when monthly cost exceeds max_cost_per_month""",
        permission_classes=[OnlyForAuthentized]
    )
    async def is_over_cost_limit(self, info: strawberry.types.Info) -> bool:
        if self.max_cost_per_month is None:
            return False
        total = await self.total_cost_this_month(info)
        return total > self.max_cost_per_month

    @strawberry.field(
        description="""List of alert codes when API key limits are exceeded""",
        permission_classes=[OnlyForAuthentized]
    )
    async def limit_alerts(self, info: strawberry.types.Info) -> typing.List[str]:
        alerts: list[str] = []
        if self.max_tokens_per_month is not None:
            total_tokens = await self.total_usage_this_month(info)
            if total_tokens > self.max_tokens_per_month:
                alerts.append("TOKENS_EXCEEDED")
        if self.max_cost_per_month is not None:
            total_cost = await self.total_cost_this_month(info)
            if total_cost > self.max_cost_per_month:
                alerts.append("COST_EXCEEDED")
        return alerts

    @strawberry.field(
        description="""Whether the API key is expired""",
        permission_classes=[OnlyForAuthentized]
    )
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        # Ensure expires_at is timezone-aware
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return now > self.expires_at

    @strawberry.field(
        description="""Number of usage records""",
        permission_classes=[OnlyForAuthentized]
    )
    async def usage_count(self, info: strawberry.types.Info) -> int:
        from sqlalchemy import select, func
        from src.DBDefinitions import UsageModel
        
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            stmt = select(func.count(UsageModel.id)).where(
                UsageModel.api_key_id == self.id
            )
            
            result = await session.execute(stmt)
            count = result.scalar()
            return int(count or 0)

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
        
        user_id = getattr(user, "id", None)
        if user_id is None and isinstance(user, dict):
            user_id = user.get("id")
        if user_id is None:
            return []
        
        # Get database session
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Query API keys for current user (only active keys)
            stmt = select(ApiKeyModel).where(
                ApiKeyModel.user_id == user_id,
                ApiKeyModel.is_active == True
            ).order_by(ApiKeyModel.created.desc())
            
            result = await session.execute(stmt)
            db_rows = result.scalars().all()
            
            # Convert to GQL models
            return [ApiKeyGQLModel.from_dataclass(row) for row in db_rows]

    @strawberry.field(
        description="""Get all expired API keys that are still active"""
    )
    async def expired_api_keys(
        self,
        info: strawberry.types.Info
    ) -> typing.List[ApiKeyGQLModel]:
        from sqlalchemy import select
        from src.DBDefinitions import ApiKeyModel
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Get database session
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Query expired but still active API keys
            stmt = select(ApiKeyModel).where(
                ApiKeyModel.is_active == True,
                ApiKeyModel.expires_at.isnot(None),
                ApiKeyModel.expires_at < now
            ).order_by(ApiKeyModel.expires_at.desc())
            
            result = await session.execute(stmt)
            db_rows = result.scalars().all()
            
            # Convert to GQL models
            return [ApiKeyGQLModel.from_dataclass(row) for row in db_rows]

    @strawberry.field(
        description="""Get top API keys by usage (dashboard analytics)"""
    )
    async def top_api_keys_by_usage(
        self,
        info: strawberry.types.Info,
        limit: int = 10
    ) -> typing.List[ApiKeyGQLModel]:
        from sqlalchemy import select, func
        from src.DBDefinitions import ApiKeyModel, UsageModel
        
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Subquery for usage this month
            stmt = select(
                ApiKeyModel,
                func.coalesce(func.sum(UsageModel.total_tokens), 0).label('total_usage')
            ).outerjoin(
                UsageModel, 
                (UsageModel.api_key_id == ApiKeyModel.id) & (UsageModel.ts >= start_of_month)
            ).group_by(
                ApiKeyModel.id
            ).order_by(
                func.coalesce(func.sum(UsageModel.total_tokens), 0).desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            rows = result.all()
            
            # Extract ApiKeyModel from rows
            return [ApiKeyGQLModel.from_dataclass(row[0]) for row in rows]

    @strawberry.field(
        description="""Get API keys that exceeded monthly limits"""
    )
    async def api_key_alerts(
        self,
        info: strawberry.types.Info,
        limit: int = 50
    ) -> typing.List[ApiKeyGQLModel]:
        from sqlalchemy import select, func, or_
        from src.DBDefinitions import ApiKeyModel, UsageModel

        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_tokens = func.coalesce(func.sum(UsageModel.total_tokens), 0)
        total_cost = func.coalesce(func.sum(UsageModel.cost_usd), 0.0)

        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            stmt = select(ApiKeyModel).outerjoin(
                UsageModel,
                (UsageModel.api_key_id == ApiKeyModel.id) & (UsageModel.ts >= start_of_month)
            ).group_by(
                ApiKeyModel.id
            ).having(
                or_(
                    (ApiKeyModel.max_tokens_per_month.isnot(None)) & (total_tokens > ApiKeyModel.max_tokens_per_month),
                    (ApiKeyModel.max_cost_per_month.isnot(None)) & (total_cost > ApiKeyModel.max_cost_per_month)
                )
            ).order_by(
                total_cost.desc(),
                total_tokens.desc()
            ).limit(limit)

            result = await session.execute(stmt)
            db_rows = result.scalars().all()
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
    
    # These will be auto-generated
    prefix: strawberry.Private[str] = None
    key_hash: strawberry.Private[str] = None
    is_active: strawberry.Private[bool] = None

    rbacobject_id: IDType = strawberry.field(
        description="""RBAC object ID""",
        default=None
    )
    createdby_id: strawberry.Private[IDType] = None
    user_id: strawberry.Private[IDType] = None

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

@strawberry.input(
    description="""Input type for regenerating an API Key"""
)
class ApiKeyRegenerateGQLModel:
    id: IDType = strawberry.field(
        description="""API Key id"""
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""timestamp for optimistic locking"""
    )

# Response type for API key insert (includes plaintext key)
@strawberry.type(
    description="""Response type for API key insertion, includes plaintext key that should be stored securely"""
)
class ApiKeyInsertResponse:
    """Response type that includes both the API key model and the plaintext key (shown only once)"""
    api_key: ApiKeyGQLModel = strawberry.field(
        description="""The created API key model"""
    )
    plaintext_key: str = strawberry.field(
        description="""The plaintext API key - STORE THIS SECURELY, it will not be shown again"""
    )

# Mutation interface
@strawberry.interface(
    description="""API Key mutations"""
)
class ApiKeyMutation:
    @strawberry.mutation(
        description="""Insert an API Key. Returns the created API key with plaintext key (shown only once).""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            # UserRoleProviderExtension není potřeba pro insert - user_roles jsou dostupné z kontextu
            # LoadDataExtension není potřeba pro insert - id se generuje automaticky
            # RbacInsertProviderExtension není potřeba pro insert - nový záznam ještě neexistuje, takže RBAC kontrola není nutná
        ]
    )
    async def api_key_insert(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyInsertGQLModel,
    ) -> typing.Union[ApiKeyInsertResponse, InsertError[ApiKeyGQLModel]]:
        """
        Insert a new API key with validation.
        
        Validates:
        - User exists and has ID
        - Rate limits are logically consistent (per_minute <= per_hour <= per_day)
        - Expiration date is in the future (if provided)
        - User hasn't exceeded max_api_keys limit
        """
        from uoishelpers.resolvers import getUserFromInfo
        from src.DBDefinitions import UserModel, ApiKeyModel
        from sqlalchemy import select, func
        import uuid
        
        # Get current user
        user = getUserFromInfo(info)
        if not user:
            return InsertError(msg="User not found in context", _input=api_key, code=get_error_code("USER_NOT_FOUND"))
        
        # Check if user has id
        if not hasattr(user, 'id') and 'id' not in user:
            return InsertError(msg="User missing ID attribute", _input=api_key, code=get_error_code("USER_INVALID"))
        
        user_id = user.id if hasattr(user, 'id') else user['id']
        
        # Generate ID early if not provided (needed for rbacobject_id)
        if api_key.id is None:
            api_key.id = uuid.uuid4()
        
        # Set rbacobject_id to the same as id for new API key
        # This must be set early because extensions may check it
        api_key.rbacobject_id = api_key.id
        
        # Validate rate limits if provided
        if api_key.rate_limit_per_minute is not None and api_key.rate_limit_per_hour is not None:
            if api_key.rate_limit_per_minute > api_key.rate_limit_per_hour:
                return InsertError(
                    msg="rate_limit_per_minute cannot be greater than rate_limit_per_hour",
                    _input=api_key,
                    code=get_error_code("INVALID_RATE_LIMITS")
                )
        
        if api_key.rate_limit_per_hour is not None and api_key.rate_limit_per_day is not None:
            if api_key.rate_limit_per_hour > api_key.rate_limit_per_day:
                return InsertError(
                    msg="rate_limit_per_hour cannot be greater than rate_limit_per_day",
                    _input=api_key,
                    code=get_error_code("INVALID_RATE_LIMITS")
                )
        
        # Validate all rate limits are non-negative
        if api_key.rate_limit_per_minute is not None and api_key.rate_limit_per_minute < 0:
            return InsertError(
                msg="rate_limit_per_minute must be non-negative",
                _input=api_key,
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        if api_key.rate_limit_per_hour is not None and api_key.rate_limit_per_hour < 0:
            return InsertError(
                msg="rate_limit_per_hour must be non-negative",
                _input=api_key,
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        if api_key.rate_limit_per_day is not None and api_key.rate_limit_per_day < 0:
            return InsertError(
                msg="rate_limit_per_day must be non-negative",
                _input=api_key,
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        
        # Validate expiration date is in the future
        if api_key.expires_at is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            if api_key.expires_at <= now:
                return InsertError(
                    msg="expires_at must be in the future",
                    _input=api_key,
                    code=get_error_code("INVALID_EXPIRATION")
                )
        
        # Check user's max_api_keys limit
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Get user from database to check max_api_keys
            user_stmt = select(UserModel).where(UserModel.id == user_id)
            user_result = await session.execute(user_stmt)
            db_user = user_result.scalar_one_or_none()
            
            if db_user and db_user.max_api_keys is not None:
                # Count active API keys for this user
                keys_stmt = select(func.count(ApiKeyModel.id)).where(
                    ApiKeyModel.user_id == user_id,
                    ApiKeyModel.is_active == True
                )
                keys_result = await session.execute(keys_stmt)
                active_keys_count = keys_result.scalar() or 0
                
                if active_keys_count >= db_user.max_api_keys:
                    return InsertError(
                        msg=f"User has reached the maximum number of API keys ({db_user.max_api_keys})",
                        _input=api_key,
                        code=get_error_code("MAX_KEYS_EXCEEDED")
                    )
        
        # Generate API key before insert
        plaintext, prefix, key_hash = generate_api_key()
        api_key.prefix = prefix
        api_key.key_hash = key_hash
        api_key.is_active = True  # Default to active
        api_key.user_id = user_id  # Set user_id from current user
        
        # ID and rbacobject_id are already set earlier in the function
        
        result = await Insert[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)
        
        # Check if insert was successful
        if isinstance(result, InsertError):
            return result
        
        # Audit logging for critical operation
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"AUDIT: api_key_insert - user_id={user_id}, api_key_id={result.id}, "
            f"name={api_key.name}, expires_at={api_key.expires_at}"
        )
        
        # Return response with plaintext key (shown only once)
        return ApiKeyInsertResponse(
            api_key=result,
            plaintext_key=plaintext
        )

    @strawberry.mutation(
        description="""Update an API Key""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            UserRoleProviderExtension[UpdateError, ApiKeyGQLModel](),
            RbacProviderExtension[UpdateError, ApiKeyGQLModel](),
            LoadDataExtension[UpdateError, ApiKeyGQLModel]()
        ]
    )
    async def api_key_update(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyUpdateGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        """
        Update an API key with validation.
        
        Validates:
        - Rate limits are logically consistent (per_minute <= per_hour <= per_day)
        - Expiration date is in the future (if provided)
        """
        # Validate rate limits if provided
        if api_key.rate_limit_per_minute is not None and api_key.rate_limit_per_hour is not None:
            if api_key.rate_limit_per_minute > api_key.rate_limit_per_hour:
                return UpdateError(
                    msg="rate_limit_per_minute cannot be greater than rate_limit_per_hour",
                    code=get_error_code("INVALID_RATE_LIMITS")
                )
        
        if api_key.rate_limit_per_hour is not None and api_key.rate_limit_per_day is not None:
            if api_key.rate_limit_per_hour > api_key.rate_limit_per_day:
                return UpdateError(
                    msg="rate_limit_per_hour cannot be greater than rate_limit_per_day",
                    code=get_error_code("INVALID_RATE_LIMITS")
                )
        
        # Validate all rate limits are non-negative
        if api_key.rate_limit_per_minute is not None and api_key.rate_limit_per_minute < 0:
            return UpdateError(
                msg="rate_limit_per_minute must be non-negative",
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        if api_key.rate_limit_per_hour is not None and api_key.rate_limit_per_hour < 0:
            return UpdateError(
                msg="rate_limit_per_hour must be non-negative",
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        if api_key.rate_limit_per_day is not None and api_key.rate_limit_per_day < 0:
            return UpdateError(
                msg="rate_limit_per_day must be non-negative",
                code=get_error_code("INVALID_RATE_LIMITS")
            )
        
        # Validate expiration date is in the future
        if api_key.expires_at is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            if api_key.expires_at <= now:
                return UpdateError(
                    msg="expires_at must be in the future",
                    code=get_error_code("INVALID_EXPIRATION")
                )
        
        return await Update[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.mutation(
        description="""Delete an API Key""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            UserAccessControlExtension[DeleteError, ApiKeyGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[DeleteError, ApiKeyGQLModel](),
            RbacProviderExtension[DeleteError, ApiKeyGQLModel](),
            LoadDataExtension[DeleteError, ApiKeyGQLModel]()
        ]
    )   
    async def api_key_delete(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyDeleteGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Optional[DeleteError[ApiKeyGQLModel]]:
        return await Delete[ApiKeyGQLModel].DoItSafeWay(info=info, entity=api_key)

    @strawberry.mutation(
        description="""Deactivate an API Key (soft delete)""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            # UserRoleProviderExtension a RbacProviderExtension nejsou potřeba - Update.DoItSafeWay načte data sám
            # LoadDataExtension není potřeba - Update.DoItSafeWay načte data sám
        ]
    )
    async def api_key_deactivate(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyUpdateGQLModel,
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        """
        Deactivate an API Key (soft delete).
        
        Sets is_active=False without deleting the key record,
        allowing it to be reactivated later if needed.
        
        Args:
            api_key: Contains id, lastchange, and optionally is_active flag
            
        Returns:
            Updated ApiKeyGQLModel or UpdateError
        """
        from src.DBDefinitions import ApiKeyModel
        from sqlalchemy import select
        import datetime
        
        # Get session from context
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Load the existing key
            stmt = select(ApiKeyModel).where(ApiKeyModel.id == api_key.id)
            result = await session.execute(stmt)
            db_key = result.scalar_one_or_none()
            
            if not db_key:
                return UpdateError(
                    msg="API key not found",
                    code=get_error_code("KEY_NOT_FOUND")
                )
            
            # Check optimistic locking
            if db_key.lastchange != api_key.lastchange:
                return UpdateError(
                    msg="Key was modified by another user. Please refresh and try again.",
                    code=get_error_code("OPTIMISTIC_LOCKING_CONFLICT")
                )
            
            # Set is_active to False and update lastchange
            # Convert to offset-naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
            db_key.is_active = False
            db_key.lastchange = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            
            await session.commit()
            await session.refresh(db_key)
            
            # Audit logging for critical operation
            import logging
            logger = logging.getLogger(__name__)
            user = info.context.get("user", {})
            user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
            logger.info(
                f"AUDIT: api_key_deactivate - user_id={user_id}, api_key_id={db_key.id}, "
                f"name={db_key.name}"
            )
            
            # Convert to GQL model
            return ApiKeyGQLModel.from_dataclass(db_key)

    @strawberry.mutation(
        description="""Regenerate an API Key (create new key, keep metadata)""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            # UserRoleProviderExtension a RbacProviderExtension nejsou potřeba - načítáme data ručně v resolveru
            # LoadDataExtension není potřeba - načítáme data ručně v resolveru
        ]
    )
    async def api_key_regenerate(
        self,
        info: strawberry.types.Info,
        api_key: ApiKeyRegenerateGQLModel,
    ) -> typing.Union[ApiKeyGQLModel, UpdateError[ApiKeyGQLModel]]:
        """
        Regenerate an API Key - create new key prefix and hash, keep all other metadata.
        
        This mutation:
        - Generates a new random prefix and key hash
        - Preserves all other metadata (rate limits, expiration, etc.)
        - Updates the lastchange timestamp for optimistic locking
        
        Args:
            api_key: Contains id and lastchange for optimistic locking
            
        Returns:
            Updated ApiKeyGQLModel or UpdateError with specific error codes:
            - 404: API key not found
            - 409: Key was modified by another user (optimistic locking conflict)
        """
        from src.DBDefinitions import ApiKeyModel
        from sqlalchemy import select
        
        # Get session from context
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Load the existing key
            stmt = select(ApiKeyModel).where(ApiKeyModel.id == api_key.id)
            result = await session.execute(stmt)
            db_key = result.scalar_one_or_none()
            
            if not db_key:
                return UpdateError(
                    msg="API key not found",
                    code=get_error_code("KEY_NOT_FOUND")
                )
            
            # Check optimistic locking
            if db_key.lastchange != api_key.lastchange:
                return UpdateError(
                    msg="Key was modified by another user. Please refresh and try again.",
                    code=get_error_code("OPTIMISTIC_LOCKING_CONFLICT")
                )
            
            # Generate new key
            plaintext, prefix, key_hash = generate_api_key()
            
            # Update only key-related fields
            db_key.prefix = prefix
            db_key.key_hash = key_hash
            # Convert to offset-naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
            db_key.lastchange = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            
            await session.commit()
            await session.refresh(db_key)
            
            # Audit logging for critical operation
            import logging
            from uoishelpers.resolvers import getUserFromInfo
            logger = logging.getLogger(__name__)
            user = getUserFromInfo(info)
            user_id = user.id if user and hasattr(user, 'id') else (user.get('id') if user and isinstance(user, dict) else None)
            logger.info(
                f"AUDIT: api_key_regenerate - user_id={user_id}, api_key_id={api_key.id}"
            )
            
            # Convert to GQL model
            gql_key = ApiKeyGQLModel.from_dataclass(db_key)
            
            # Return the updated key (without the plaintext for security)
            return gql_key

    @strawberry.mutation(
        description="""Deactivate all expired API keys (bulk operation)""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            UserAccessControlExtension[ApiKeyGQLModel](
                roles=["administrátor"]
            )
        ]
    )
    async def deactivate_expired_api_keys(
        self,
        info: strawberry.types.Info
    ) -> int:
        """
        Deactivate all expired API keys in a single operation.
        
        This bulk operation:
        - Finds all active API keys that have passed their expiration date
        - Sets is_active=False for all found keys
        - Updates lastchange timestamp for audit trail
        - Logs the operation for auditing
        
        Returns:
            The number of keys that were deactivated
            
        Permission:
            Requires 'administrátor' role for security
        """
        import logging
        from sqlalchemy import select
        from src.DBDefinitions import ApiKeyModel
        
        logger = logging.getLogger(__name__)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Get database session from context
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            try:
                # Start explicit transaction
                async with session.begin():
                    # Find expired but still active API keys
                    stmt = select(ApiKeyModel).where(
                        ApiKeyModel.is_active == True,
                        ApiKeyModel.expires_at.isnot(None),
                        ApiKeyModel.expires_at < now
                    )
                    
                    result = await session.execute(stmt)
                    expired_keys = result.scalars().all()
                    
                    if not expired_keys:
                        logger.info("deactivate_expired_api_keys: No expired keys found")
                        return 0
                    
                    # Deactivate them in bulk
                    # Convert to offset-naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
                    count = 0
                    deactivated_key_ids = []
                    now_db = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    for key in expired_keys:
                        key.is_active = False
                        key.lastchange = now_db
                        deactivated_key_ids.append(str(key.id))
                        count += 1
                    
                    # Transaction will commit automatically on exit from context manager
                    # If any error occurs, it will rollback automatically
                    
                    # Log for audit trail
                    logger.info(
                        f"deactivate_expired_api_keys: Deactivated {count} expired API keys. "
                        f"Key IDs: {', '.join(deactivated_key_ids[:10])}"
                        + (f" (and {len(deactivated_key_ids) - 10} more)" if len(deactivated_key_ids) > 10 else "")
                    )
                    
                    return count
            except Exception as e:
                # Log error and re-raise - transaction will rollback automatically
                logger.error(f"deactivate_expired_api_keys: Error during bulk deactivation: {e}")
                raise
