import typing
import datetime
import strawberry
from strawberry.types import Info

from .BaseGQLModel import BaseGQLModel, IDType
from uoishelpers.resolvers import (
    getLoadersFromInfo, 
    createInputs2,
    PageResolver,
    VectorResolver
)
from src.DBDefinitions import UserModel


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


# Mutation interface (zatím prázdná, bude rozšířena později)
@strawberry.interface
class UserMutation:
    """
    User mutation interface - provides write operations for User entities
    """
    pass


# Resolver functions (using PageResolver pattern like ApiKeyGQLModel)
# user_by_id and user_page are handled by PageResolver automatically