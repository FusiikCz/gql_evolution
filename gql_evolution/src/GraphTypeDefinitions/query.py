import strawberry

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .EventInvitationStateGQLModel import EventInvitationStateQuery
from .ApiKeyGQLModel import ApiKeyQuery
from .UsageGQLModel import UsageQuery
from .UserGQLModel import UserQuery
from .DocumentGQLModel import DocumentQuery
from .DocumentFragmentGQLModel import DocumentFragmentQuery
from .EndpointConfigGQLModel import EndpointConfigQuery

@strawberry.type(description="""Type for query root""")
class Query(EventQuery, EventInvitationQuery, EventInvitationStateQuery, ApiKeyQuery, UsageQuery, UserQuery, DocumentQuery, DocumentFragmentQuery, EndpointConfigQuery):
    @strawberry.field(
        description="""Returns hello world"""
        )
    async def hello(
        self,
        info: strawberry.types.Info,
    ) -> str:
        return "hello world"
