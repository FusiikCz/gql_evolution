import strawberry


from .EventGQLModel import EventMutation
from .EventInvitationGQLModel import EventInvitationMutation
from .ApiKeyGQLModel import ApiKeyMutation
from .UsageGQLModel import UsageMutation
from .DocumentGQLModel import DocumentMutation
from .DocumentFragmentGQLModel import DocumentFragmentMutation
from .UserGQLModel import UserMutation
from .EndpointConfigGQLModel import EndpointConfigMutation

@strawberry.type(description="""Type for mutation root""")
class Mutation(EventMutation, EventInvitationMutation, ApiKeyMutation, UsageMutation, DocumentMutation, DocumentFragmentMutation, UserMutation, EndpointConfigMutation):
    pass

