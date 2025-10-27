import strawberry


from .EventGQLModel import EventMutation
from .EventInvitationGQLModel import EventInvitationMutation
from .ApiKeyGQLModel import ApiKeyMutation
from .UsageGQLModel import UsageMutation

@strawberry.type(description="""Type for mutation root""")
class Mutation(EventMutation, EventInvitationMutation, ApiKeyMutation, UsageMutation):
    pass

