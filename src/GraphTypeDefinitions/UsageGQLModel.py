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
ApiKeyGQLModel = typing.Annotated["ApiKeyGQLModel", strawberry.lazy(".ApiKeyGQLModel")]
ApiKeyInputFilter = typing.Annotated["ApiKeyInputFilter", strawberry.lazy(".ApiKeyGQLModel")]

# Output type pro statistics
@strawberry.type(description="""Usage statistics for a time period""")
class UsageStatsGQLModel:
    total_requests: int = strawberry.field(description="""Total number of requests""")
    total_tokens: int = strawberry.field(description="""Total tokens used""")
    total_cost: float = strawberry.field(description="""Total cost in USD""")
    average_tokens_per_request: float = strawberry.field(description="""Average tokens per request""")

@strawberry.type(description="""Usage rollup point for a time bucket""")
class UsageRollupPointGQLModel:
    bucket: str = strawberry.field(description="""Bucket identifier (e.g. YYYY-MM-DD or YYYY-MM-DDTHH:00Z)""")
    requests: int = strawberry.field(description="""Number of requests in bucket""")
    total_tokens: int = strawberry.field(description="""Total tokens in bucket""")
    total_cost: float = strawberry.field(description="""Total cost (USD) in bucket""")

@createInputs2
class UsageInputFilter:
    id: IDType
    api_key_id: IDType
    ts: datetime.datetime
    route: str
    deployment: str
    status: int
    stream: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model: str
    request_id: str
    user_agent: str
    ip_address: str
    error_code: str
    error_message: str
    
    # Nested filter for relationship
    api_key: ApiKeyInputFilter = strawberry.field(
        description="""API Key filter operators for filtering by API key properties
        Example: {"api_key": {"name": {"_eq": "Production Key"}}}
        """, 
        default=None
    )

@strawberry.federation.type(
    description="""Entity representing usage tracking for API Keys""",
    keys=["id"]
)
class UsageGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).UsageModel

    # Usage specific fields
    ts: datetime.datetime = strawberry.field(
        description="""Timestamp of the usage event""",
        permission_classes=[OnlyForAuthentized]
    )

    route: typing.Optional[str] = strawberry.field(
        default=None,
        description="""API route that was called""",
        permission_classes=[OnlyForAuthentized]
    )

    deployment: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Deployment name (e.g., gpt-4, gpt-3.5-turbo)""",
        permission_classes=[OnlyForAuthentized]
    )

    status: typing.Optional[int] = strawberry.field(
        default=None,
        description="""HTTP status code of the response""",
        permission_classes=[OnlyForAuthentized]
    )

    stream: bool = strawberry.field(
        description="""Whether the request was streamed""",
        permission_classes=[OnlyForAuthentized]
    )

    # Token usage fields
    prompt_tokens: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Number of tokens in the prompt""",
        permission_classes=[OnlyForAuthentized]
    )

    completion_tokens: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Number of tokens in the completion""",
        permission_classes=[OnlyForAuthentized]
    )

    total_tokens: typing.Optional[int] = strawberry.field(
        default=None,
        description="""Total number of tokens used""",
        permission_classes=[OnlyForAuthentized]
    )

    # Cost tracking
    cost_usd: typing.Optional[float] = strawberry.field(
        default=None,
        description="""Cost of the request in USD""",
        permission_classes=[OnlyForAuthentized]
    )

    # Model information
    model: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Model name used for the request""",
        permission_classes=[OnlyForAuthentized]
    )

    # Request metadata
    request_id: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Unique request identifier""",
        permission_classes=[OnlyForAuthentized]
    )

    user_agent: typing.Optional[str] = strawberry.field(
        default=None,
        description="""User agent string from the request""",
        permission_classes=[OnlyForAuthentized]
    )

    ip_address: typing.Optional[str] = strawberry.field(
        default=None,
        description="""IP address of the client""",
        permission_classes=[OnlyForAuthentized]
    )

    # Error tracking
    error_code: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Error code if the request failed""",
        permission_classes=[OnlyForAuthentized]
    )

    error_message: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Error message if the request failed""",
        permission_classes=[OnlyForAuthentized]
    )

    # Foreign key field
    api_key_id: typing.Optional[IDType] = strawberry.field(
        default=None,
        description="""API Key that was used for this request""",
        permission_classes=[OnlyForAuthentized]
    )

    # Relationship
    api_key: typing.Optional[ApiKeyGQLModel] = strawberry.field(
        description="""API Key that was used for this request""",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[ApiKeyGQLModel](fkey_field_name="api_key_id")
    )

    # Computed fields
    @strawberry.field(
        description="""Date extracted from timestamp""",
        permission_classes=[OnlyForAuthentized]
    )
    def date(self) -> datetime.date:
        return self.ts.date()

# Query interface
@strawberry.interface(
    description="""Usage queries"""
)
class UsageQuery:
    usage_by_id: typing.Optional[UsageGQLModel] = strawberry.field(
        description="""Get a usage record by its id""",
        permission_classes=[OnlyForAuthentized],
        resolver=UsageGQLModel.load_with_loader
    )

    usage_page: typing.List[UsageGQLModel] = strawberry.field(
        description="""Get a page of usage records""",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[UsageGQLModel](whereType=UsageInputFilter)
    )

    @strawberry.field(
        description="""Get usage statistics for a specific time period""",
        permission_classes=[OnlyForAuthentized]
    )
    async def usage_stats(
        self, 
        info: strawberry.types.Info,
        api_key_id: typing.Optional[IDType] = None,
        start_date: typing.Optional[datetime.datetime] = None,
        end_date: typing.Optional[datetime.datetime] = None
    ) -> UsageStatsGQLModel:
        from sqlalchemy import select, func
        from src.DBDefinitions import UsageModel
        
        # Get database session
        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Build query with filters
            stmt = select(
                func.count(UsageModel.id).label('total_requests'),
                func.coalesce(func.sum(UsageModel.total_tokens), 0).label('total_tokens'),
                func.coalesce(func.sum(UsageModel.cost_usd), 0.0).label('total_cost'),
                func.coalesce(func.avg(UsageModel.total_tokens), 0.0).label('avg_tokens')
            )
            
            # Apply filters
            if api_key_id:
                stmt = stmt.where(UsageModel.api_key_id == api_key_id)
            if start_date:
                stmt = stmt.where(UsageModel.ts >= start_date)
            if end_date:
                stmt = stmt.where(UsageModel.ts <= end_date)
            
            result = await session.execute(stmt)
            row = result.first()
            
            if not row:
                return UsageStatsGQLModel(
                    total_requests=0,
                    total_tokens=0,
                    total_cost=0.0,
                    average_tokens_per_request=0.0
                )
            
            return UsageStatsGQLModel(
                total_requests=int(row.total_requests or 0),
                total_tokens=int(row.total_tokens or 0),
                total_cost=float(row.total_cost or 0.0),
                average_tokens_per_request=float(row.avg_tokens or 0.0)
            )

    @strawberry.field(
        description="""Time-series rollup of usage for an API key (bucket=day|hour)""",
        permission_classes=[OnlyForAuthentized],
    )
    async def usage_rollup(
        self,
        info: strawberry.types.Info,
        api_key_id: IDType,
        bucket: str = "day",
        start_date: typing.Optional[datetime.datetime] = None,
        end_date: typing.Optional[datetime.datetime] = None,
    ) -> typing.List[UsageRollupPointGQLModel]:
        from sqlalchemy import select, func
        from src.DBDefinitions import UsageModel

        # defaults: last 30 days
        now = datetime.datetime.now(datetime.timezone.utc)
        if end_date is None:
            end_date = now
        if start_date is None:
            start_date = end_date - datetime.timedelta(days=30)

        async_session_maker = info.context["asyncSessionMaker"]
        async with async_session_maker() as session:
            # Pick bucket expression depending on dialect (sqlite vs postgres)
            bind = session.get_bind()
            dialect = getattr(getattr(bind, "dialect", None), "name", "")
            bucket_lower = (bucket or "day").lower()
            if bucket_lower not in ("day", "hour"):
                bucket_lower = "day"

            if dialect == "sqlite":
                if bucket_lower == "hour":
                    bucket_expr = func.strftime("%Y-%m-%dT%H:00:00Z", UsageModel.ts)
                else:
                    bucket_expr = func.strftime("%Y-%m-%d", UsageModel.ts)
            else:
                # Postgres-friendly date_trunc + to_char
                fmt = "YYYY-MM-DD\"T\"HH24:00:00Z" if bucket_lower == "hour" else "YYYY-MM-DD"
                bucket_expr = func.to_char(func.date_trunc(bucket_lower, UsageModel.ts), fmt)

            stmt = (
                select(
                    bucket_expr.label("bucket"),
                    func.count(UsageModel.id).label("requests"),
                    func.coalesce(func.sum(UsageModel.total_tokens), 0).label("total_tokens"),
                    func.coalesce(func.sum(UsageModel.cost_usd), 0.0).label("total_cost"),
                )
                .where(
                    UsageModel.api_key_id == api_key_id,
                    UsageModel.ts >= start_date,
                    UsageModel.ts <= end_date,
                )
                .group_by(bucket_expr)
                .order_by(bucket_expr.asc())
            )
            res = await session.execute(stmt)
            rows = res.mappings().all()
            return [
                UsageRollupPointGQLModel(
                    bucket=str(r["bucket"]),
                    requests=int(r["requests"] or 0),
                    total_tokens=int(r["total_tokens"] or 0),
                    total_cost=float(r["total_cost"] or 0.0),
                )
                for r in rows
            ]

# Input types for mutations
from uoishelpers.resolvers import InputModelMixin

@strawberry.input(
    description="""Input type for creating a Usage record"""
)
class UsageInsertGQLModel(InputModelMixin):
    getLoader = UsageGQLModel.getLoader
    
    api_key_id: IDType = strawberry.field(
        description="""API Key that was used for this request"""
    )
    
    ts: datetime.datetime = strawberry.field(
        description="""Timestamp of the usage event"""
    )
    
    route: typing.Optional[str] = strawberry.field(
        description="""API route that was called""",
        default=None
    )
    
    deployment: typing.Optional[str] = strawberry.field(
        description="""Deployment name""",
        default=None
    )
    
    status: typing.Optional[int] = strawberry.field(
        description="""HTTP status code""",
        default=None
    )
    
    stream: typing.Optional[bool] = strawberry.field(
        description="""Whether the request was streamed""",
        default=False
    )
    
    prompt_tokens: typing.Optional[int] = strawberry.field(
        description="""Number of tokens in the prompt""",
        default=None
    )
    
    completion_tokens: typing.Optional[int] = strawberry.field(
        description="""Number of tokens in the completion""",
        default=None
    )
    
    total_tokens: typing.Optional[int] = strawberry.field(
        description="""Total number of tokens used""",
        default=None
    )
    
    cost_usd: typing.Optional[float] = strawberry.field(
        description="""Cost of the request in USD""",
        default=None
    )
    
    model: typing.Optional[str] = strawberry.field(
        description="""Model name used for the request""",
        default=None
    )
    
    request_id: typing.Optional[str] = strawberry.field(
        description="""Unique request identifier""",
        default=None
    )
    
    user_agent: typing.Optional[str] = strawberry.field(
        description="""User agent string from the request""",
        default=None
    )
    
    ip_address: typing.Optional[str] = strawberry.field(
        description="""IP address of the client""",
        default=None
    )
    
    error_code: typing.Optional[str] = strawberry.field(
        description="""Error code if the request failed""",
        default=None
    )
    
    error_message: typing.Optional[str] = strawberry.field(
        description="""Error message if the request failed""",
        default=None
    )

    id: typing.Optional[IDType] = strawberry.field(
        description="""Usage record id""",
        default=None
    )

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for updating a Usage record"""
)
class UsageUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""Usage record id"""
    )
    
    lastchange: datetime.datetime = strawberry.field(
        description="timestamp"
    )
    
    status: typing.Optional[int] = strawberry.field(
        description="""HTTP status code""",
        default=None
    )
    
    error_code: typing.Optional[str] = strawberry.field(
        description="""Error code if the request failed""",
        default=None
    )
    
    error_message: typing.Optional[str] = strawberry.field(
        description="""Error message if the request failed""",
        default=None
    )

    changedby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for deleting a Usage record"""
)
class UsageDeleteGQLModel:
    id: IDType = strawberry.field(
        description="""Usage record id"""
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""last change"""
    )

# Mutation interface
@strawberry.interface(
    description="""Usage mutations"""
)
class UsageMutation:
    @strawberry.mutation(
        description="""Insert a Usage record""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            UserAccessControlExtension[InsertError, UsageGQLModel](
                roles=[
                    "api_key_administrator", 
                    "usage_tracker"
                ]
            ),
            UserRoleProviderExtension[InsertError, UsageGQLModel](),
            RbacProviderExtension[InsertError, UsageGQLModel](),
            LoadDataExtension[InsertError, UsageGQLModel]()
        ],
    )
    async def usage_insert(
        self,
        info: strawberry.types.Info,
        usage: UsageInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[UsageGQLModel, InsertError[UsageGQLModel]]:
        return await Insert[UsageGQLModel].DoItSafeWay(info=info, entity=usage)

    @strawberry.mutation(
        description="""Update a Usage record""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            LoadDataExtension[UpdateError, UsageGQLModel]()
        ],
    )
    async def usage_update(
        self,
        info: strawberry.types.Info,
        usage: UsageUpdateGQLModel,
        db_row: typing.Any
    ) -> typing.Union[UsageGQLModel, UpdateError[UsageGQLModel]]:
        return await Update[UsageGQLModel].DoItSafeWay(info=info, entity=usage)

    @strawberry.mutation(
        description="""Delete a Usage record""",
        permission_classes=[
            SimpleDeletePermission[UsageGQLModel](roles=["administrátor"])
        ]
    )   
    async def usage_delete(
        self,
        info: strawberry.types.Info,
        usage: UsageDeleteGQLModel
    ) -> typing.Optional[DeleteError[UsageGQLModel]]:
        return await Delete[UsageGQLModel].DoItSafeWay(info=info, entity=usage)

