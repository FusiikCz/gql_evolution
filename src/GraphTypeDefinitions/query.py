import strawberry

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .ApiKeyGQLModel import ApiKeyQuery
from .UsageGQLModel import UsageQuery
from .UserGQLModel import UserQuery
from .DocumentGQLModel import DocumentQuery
from .DocumentFragmentGQLModel import DocumentFragmentQuery

@strawberry.type(description="""Type for query root""")
class Query(EventQuery, EventInvitationQuery, ApiKeyQuery, UsageQuery, UserQuery, DocumentQuery, DocumentFragmentQuery):
    @strawberry.field(
        description="""Returns hello world"""
        )
    async def hello(
        self,
        info: strawberry.types.Info,
    ) -> str:
        return "hello world"
