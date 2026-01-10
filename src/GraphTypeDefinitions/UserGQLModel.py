import typing
import datetime
import strawberry
import re
from strawberry.types import Info

from .BaseGQLModel import BaseGQLModel, IDType
from uoishelpers.resolvers import (
    getLoadersFromInfo, 
    createInputs2,
    PageResolver,
    VectorResolver
)
from src.DBDefinitions import UserModel

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_email(email: typing.Optional[str]) -> bool:
    """Validate email format using regex."""
    if not email:
        return True  # Email is optional
    return bool(EMAIL_REGEX.match(email))

async def check_duplicate_email(
    session,
    email: str,
    exclude_user_id: typing.Optional[IDType] = None
) -> bool:
    """Check if email already exists in database."""
    from sqlalchemy import select
    from src.DBDefinitions import UserModel
    
    stmt = select(UserModel).where(UserModel.email == email)
    if exclude_user_id:
        stmt = stmt.where(UserModel.id != exclude_user_id)
    
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    return existing is not None


@strawberry.federation.type(
    keys=["id"],
    description="""Entity representing a user in the system"""
)
class UserGQLModel(BaseGQLModel):
    """
    User GraphQL model for Task 11
    
    Represents external users who own API keys and have access to AI models.
    This is the main entity that connects to API keys and usage tracking.
    """
    
    # Základní informace
    name: typing.Optional[str] = strawberry.field(
        description="Display name of the user"
    )
    
    email: typing.Optional[str] = strawberry.field(
        description="Email address of the user"
    )
    
    # Autentizace a autorizace
    is_active: bool = strawberry.field(
        name="is_active",
        description="Whether the user account is active"
    )
    
    is_verified: bool = strawberry.field(
        name="is_verified",
        description="Whether the user email is verified"
    )
    
    # Metadata
    last_login_at: typing.Optional[datetime.datetime] = strawberry.field(
        name="last_login_at",
        description="Last time the user logged in"
    )
    
    login_count: typing.Optional[int] = strawberry.field(
        name="login_count",
        description="Total number of logins"
    )
    
    # Externí identifikátory
    external_string: typing.Optional[str] = strawberry.field(
        name="external_string",
        description="External system user ID"
    )
    
    external_provider: typing.Optional[str] = strawberry.field(
        name="external_provider",
        description="External provider (e.g., 'google', 'microsoft', 'azure')"
    )
    
    # Poznámky a metadata
    notes: typing.Optional[str] = strawberry.field(
        name="notes",
        description="Administrative notes about the user"
    )
    
    # Timezone a lokalizace
    timezone: typing.Optional[str] = strawberry.field(
        name="timezone",
        description="User's timezone (e.g., 'Europe/Prague')"
    )
    
    # API limits
    max_api_keys: typing.Optional[int] = strawberry.field(
        name="max_api_keys",
        description="Maximum number of API keys this user can have"
    )
    
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).UserModel
    
    # Hybrid properties
    @strawberry.field(description="Is the user recently active?")
    def is_recently_active(self) -> bool:
        """Check if user was active in the last 7 days"""
        if not self.last_login_at:
            return False
        
        week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        return self.last_login_at > week_ago
    
    @strawberry.field(description="User's status description")
    def status_description(self) -> str:
        """Get human-readable status"""
        if not self.is_active:
            return "Inactive"
        elif not self.is_verified:
            return "Unverified"
        elif self.is_recently_active():
            return "Active"
        else:
            return "Dormant"
    
    @strawberry.field(description="Formatted display name")
    def display_name(self) -> str:
        """Get formatted display name"""
        if self.name:
            return self.name
        elif self.email:
            return self.email.split('@')[0]
        else:
            return f"User {str(self.id)[:8]}"


# Input filters pro User
from uoishelpers.gqlpermissions import OnlyForAuthentized

@createInputs2
class UserInputFilter:
    id: IDType
    name: str
    email: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime.datetime
    login_count: int
    external_string: str
    external_provider: str
    notes: str
    timezone: str
    max_api_keys: int

UserWhereFilter = UserInputFilter
UserOrderByFilter = UserInputFilter


# Query interface
@strawberry.interface
class UserQuery:
    """
    User query interface - provides read operations for User entities
    """
    getLoader = UserGQLModel.getLoader
    
    user_by_id: typing.Optional[UserGQLModel] = strawberry.field(
        description="Get user by ID",
        permission_classes=[OnlyForAuthentized],
        resolver=UserGQLModel.load_with_loader
    )
    
    user_page: typing.List[UserGQLModel] = strawberry.field(
        description="Get users with pagination and filtering",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[UserGQLModel](whereType=UserWhereFilter)
    )
    
    @strawberry.field(
        description="Get active users only",
        permission_classes=[OnlyForAuthentized]
    )
    async def active_users(
        self, 
        info: Info,
        skip: typing.Optional[int] = 0,
        limit: typing.Optional[int] = 10
    ) -> typing.List[UserGQLModel]:
        loader = getLoadersFromInfo(info).UserModel
        where = {"is_active": {"_eq": True}}
        
        result = await loader.page(skip=skip, limit=limit, where=where)
        # Convert UserModel instances to UserGQLModel instances
        return [UserGQLModel.from_dataclass(db_row=user) for user in result]
    
    @strawberry.field(
        description="Search users by email or name",
        permission_classes=[OnlyForAuthentized]
    )
    async def search_users(
        self, 
        info: Info,
        search_term: str,
        skip: typing.Optional[int] = 0,
        limit: typing.Optional[int] = 10
    ) -> typing.List[UserGQLModel]:
        loader = getLoadersFromInfo(info).UserModel
        
        # Search in both email and name fields
        where = {
            "_or": [
                {"email": {"_ilike": f"%{search_term}%"}},
                {"name": {"_ilike": f"%{search_term}%"}}
            ]
        }
        
        result = await loader.page(skip=skip, limit=limit, where=where)
        # Convert UserModel instances to UserGQLModel instances
        return [UserGQLModel.from_dataclass(db_row=user) for user in result]


# Input types for mutations
from uoishelpers.resolvers import (
    InsertError,
    Insert,
    UpdateError,
    Update,
    DeleteError,
    Delete,
    InputModelMixin
)
from uoishelpers.gqlpermissions import (
    SimpleInsertPermission,
    SimpleUpdatePermission,
    SimpleDeletePermission
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension

@strawberry.input(
    description="""Input type for creating a User"""
)
class UserInsertGQLModel(InputModelMixin):
    getLoader = UserGQLModel.getLoader
    
    name: typing.Optional[str] = strawberry.field(
        description="""Display name of the user""",
        default=None
    )
    
    email: typing.Optional[str] = strawberry.field(
        description="""Email address of the user""",
        default=None
    )
    
    is_active: typing.Optional[bool] = strawberry.field(
        description="""Whether the user account is active""",
        default=True
    )
    
    is_verified: typing.Optional[bool] = strawberry.field(
        description="""Whether the user email is verified""",
        default=False
    )
    
    external_string: typing.Optional[str] = strawberry.field(
        description="""External system user ID""",
        default=None
    )
    
    external_provider: typing.Optional[str] = strawberry.field(
        description="""External provider (e.g., 'google', 'microsoft', 'azure')""",
        default=None
    )
    
    notes: typing.Optional[str] = strawberry.field(
        description="""Administrative notes about the user""",
        default=None
    )
    
    timezone: typing.Optional[str] = strawberry.field(
        description="""User's timezone (e.g., 'Europe/Prague')""",
        default=None
    )
    
    max_api_keys: typing.Optional[int] = strawberry.field(
        description="""Maximum number of API keys this user can have""",
        default=10
    )
    
    id: typing.Optional[IDType] = strawberry.field(
        description="""User id""",
        default=None
    )
    
    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for updating a User"""
)
class UserUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""User id"""
    )
    
    lastchange: datetime.datetime = strawberry.field(
        description="timestamp for optimistic locking"
    )
    
    name: typing.Optional[str] = strawberry.field(
        description="""Display name of the user""",
        default=None
    )
    
    email: typing.Optional[str] = strawberry.field(
        description="""Email address of the user""",
        default=None
    )
    
    is_active: typing.Optional[bool] = strawberry.field(
        description="""Whether the user account is active""",
        default=None
    )
    
    is_verified: typing.Optional[bool] = strawberry.field(
        description="""Whether the user email is verified""",
        default=None
    )
    
    external_string: typing.Optional[str] = strawberry.field(
        description="""External system user ID""",
        default=None
    )
    
    external_provider: typing.Optional[str] = strawberry.field(
        description="""External provider (e.g., 'google', 'microsoft', 'azure')""",
        default=None
    )
    
    notes: typing.Optional[str] = strawberry.field(
        description="""Administrative notes about the user""",
        default=None
    )
    
    timezone: typing.Optional[str] = strawberry.field(
        description="""User's timezone (e.g., 'Europe/Prague')""",
        default=None
    )
    
    max_api_keys: typing.Optional[int] = strawberry.field(
        description="""Maximum number of API keys this user can have""",
        default=None
    )
    
    changedby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for deleting a User"""
)
class UserDeleteGQLModel:
    id: IDType = strawberry.field(
        description="""User id"""
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""last change"""
    )

# Mutation interface
@strawberry.interface(
    description="""User mutations"""
)
class UserMutation:
    """
    User mutation interface - provides write operations for User entities
    """
    @strawberry.mutation(
        description="""Insert a User""",
        permission_classes=[
            OnlyForAuthentized,
            SimpleInsertPermission[UserGQLModel](roles=["administrátor"])
        ],
        extensions=[
            UserAccessControlExtension[InsertError, UserGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[InsertError, UserGQLModel](),
            RbacProviderExtension[InsertError, UserGQLModel](),
            LoadDataExtension[InsertError, UserGQLModel]()
        ],
    )
    async def user_insert(
        self,
        info: strawberry.Info,
        user: UserInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[UserGQLModel, InsertError[UserGQLModel]]:
        """
        Insert a new user with email validation and duplicate check.
        
        Validates:
        - Email format (if provided)
        - Email uniqueness (if provided)
        
        Error codes:
        - INVALID_EMAIL: Email format is invalid
        - EMAIL_ALREADY_EXISTS: Email already exists in database
        """
        # Validate email format if provided
        if user.email and not validate_email(user.email):
            return InsertError(
                msg=f"Invalid email format: {user.email}",
                _input=user,
                code="INVALID_EMAIL"
            )
        
        # Check for duplicate email if provided
        if user.email:
            async_session_maker = info.context["asyncSessionMaker"]
            async with async_session_maker() as session:
                if await check_duplicate_email(session, user.email):
                    return InsertError(
                        msg=f"Email already exists: {user.email}",
                        _input=user,
                        code="EMAIL_ALREADY_EXISTS"
                    )
        
        return await Insert[UserGQLModel].DoItSafeWay(info=info, entity=user)
    
    @strawberry.mutation(
        description="""Update a User""",
        permission_classes=[
            OnlyForAuthentized,
            SimpleUpdatePermission[UserGQLModel](roles=["administrátor"])
        ],
        extensions=[
            UserAccessControlExtension[UpdateError, UserGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[UpdateError, UserGQLModel](),
            RbacProviderExtension[UpdateError, UserGQLModel](),
            LoadDataExtension[UpdateError, UserGQLModel]()
        ],
    )
    async def user_update(
        self,
        info: strawberry.Info,
        user: UserUpdateGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[UserGQLModel, UpdateError[UserGQLModel]]:
        """
        Update an existing user with email validation and duplicate check.
        
        Validates:
        - Email format (if provided)
        - Email uniqueness (if provided, excluding current user)
        
        Error codes:
        - INVALID_EMAIL: Email format is invalid
        - EMAIL_ALREADY_EXISTS: Email already exists in database
        """
        # Validate email format if provided
        if user.email and not validate_email(user.email):
            return UpdateError(
                msg=f"Invalid email format: {user.email}",
                code="INVALID_EMAIL"
            )
        
        # Check for duplicate email if provided (excluding current user)
        if user.email:
            async_session_maker = info.context["asyncSessionMaker"]
            async with async_session_maker() as session:
                if await check_duplicate_email(session, user.email, exclude_user_id=user.id):
                    return UpdateError(
                        msg=f"Email already exists: {user.email}",
                        code="EMAIL_ALREADY_EXISTS"
                    )
        
        result = await Update[UserGQLModel].DoItSafeWay(info=info, entity=user)
        
        # Audit logging for critical operation
        if not isinstance(result, UpdateError):
            import logging
            from uoishelpers.resolvers import getUserFromInfo
            logger = logging.getLogger(__name__)
            current_user = getUserFromInfo(info)
            current_user_id = current_user.id if current_user and hasattr(current_user, 'id') else (current_user.get('id') if current_user and isinstance(current_user, dict) else None)
            logger.info(
                f"AUDIT: user_update - performed_by={current_user_id}, user_id={user.id}, "
                f"email={user.email}, is_active={user.is_active}"
            )
        
        return result
    
    @strawberry.mutation(
        description="""Delete a User""",
        permission_classes=[
            OnlyForAuthentized,
            SimpleDeletePermission[UserGQLModel](roles=["administrátor"])
        ],
        extensions=[
            UserAccessControlExtension[DeleteError, UserGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[DeleteError, UserGQLModel](),
            RbacProviderExtension[DeleteError, UserGQLModel](),
            LoadDataExtension[DeleteError, UserGQLModel]()
        ],
    )
    async def user_delete(
        self,
        info: strawberry.Info,
        user: UserDeleteGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Optional[DeleteError[UserGQLModel]]:
        return await Delete[UserGQLModel].DoItSafeWay(info=info, entity=user)


# Resolver functions (using PageResolver pattern like ApiKeyGQLModel)
# user_by_id and user_page are handled by PageResolver automatically