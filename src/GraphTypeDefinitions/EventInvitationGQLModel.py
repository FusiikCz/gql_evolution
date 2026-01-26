import asyncio
import dataclasses
import datetime
import typing
import strawberry

from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
    SimpleInsertPermission, 
    SimpleUpdatePermission, 
    SimpleDeletePermission
)    
from uoishelpers.resolvers import (
    getLoadersFromInfo, 
    getUserFromInfo,
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
from uoishelpers.gqlpermissions.UserAbsoluteAccessControlExtension import UserAbsoluteAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from src.Utils.error_codes import get_error_code


EventGQLModel = typing.Annotated["EventGQLModel", strawberry.lazy(".EventGQLModel")]
EventInputFilter = typing.Annotated["EventInputFilter", strawberry.lazy(".EventGQLModel")]
UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]
EventInvitationStateGQLModel = typing.Annotated["EventInvitationStateGQLModel", strawberry.lazy(".EventInvitationStateGQLModel")]

@createInputs2
class EventInvitationInputFilter:
    id: IDType
    event_id: IDType
    user_id: IDType
    state_id: IDType

    event: typing.Optional[EventInputFilter] = strawberry.field(description="""Event filter operators, 
for field "event" the filters could be
{"event": {"start_date": {"_ge": "2025-06-30T18:01:59"}}}
{"event": {"end_date": {"_le": "2025-06-30T18:01:59"}}}
{"event": {"_and": [{"start_date": {"_ge": "2025-06-30T18:01:59"}}, {"end_date": {"_le": "2025-06-30T18:01:59"}}]}}
""", default=None)

@strawberry.federation.type(
    keys=["id"], 
    description="""Entity representing an Invitation to an Event and user presence tracking.
Event invitations link users to events and track invitation state (invited, accepted, declined, etc.).
Each invitation connects a user (via user_id) to an event (via event_id) with a specific state (via state_id).
Invitations manage user participation and presence in events for scheduling and attendance tracking.
Example use cases:
- "Find all invitations for a specific event"
- "Get all events where user is invited"
- "List accepted invitations for a user"
- "Find invitations by state (invited, accepted, declined)"
Use EventInvitationInputFilter with filters like event_id, user_id, state_id, and nested event/user filters."""
)
class EventInvitationGQLModel(BaseGQLModel):

    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).EventInvitationModel

    event_id: typing.Optional[IDType] = strawberry.field(
        description="""Event assigned to the invitation - foreign key to Event entity.
        @relation(to: EventGQLModel, field: 'id')""",
        default=None,
        permission_classes=[
            OnlyForAuthentized
        ],
        directives=[Relation(to="EventGQLModel")]
    )

    user_id: typing.Optional[IDType] = strawberry.field( 
        description="""User assigned to the invitation - foreign key to User entity.
        @relation(to: UserGQLModel, field: 'id')""",
        default=None,
        permission_classes=[
            OnlyForAuthentized
        ],
        directives=[Relation(to="UserGQLModel")]
    )

    state_id: typing.Optional[IDType] = strawberry.field(
        description="""State assigned to the invitation - foreign key to EventInvitationState.
        @relation(to: EventInvitationStateGQLModel, field: 'id')""",
        default=None,
        permission_classes=[
            OnlyForAuthentized  
        ],
        directives=[Relation(to="EventInvitationStateGQLModel")]
    )

    event: typing.Optional[EventGQLModel] = strawberry.field(
        description="""Event assigned to the invitation""",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=ScalarResolver[EventGQLModel](fkey_field_name="event_id")
    )

    user: typing.Optional[UserGQLModel] = strawberry.field(
        description="""User assigned to the invitation""",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="user_id")
    )

    state: typing.Optional[EventInvitationStateGQLModel] = strawberry.field(
        description="""Invitation state""",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=ScalarResolver[EventInvitationStateGQLModel](fkey_field_name="state_id")
    )

@strawberry.type(description="EventInvitation queries for fetching invitations by id or by filter")
class EventInvitationQuery:

    event_invitation_by_id: typing.Optional[EventInvitationGQLModel] = strawberry.field(
        description="Invitation by its id",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=EventInvitationGQLModel.load_with_loader
    )

    event_invitation_page: typing.List[EventInvitationGQLModel] = strawberry.field(
        description="selected invitations to events",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=PageResolver[EventInvitationGQLModel](whereType=EventInvitationInputFilter)
    )


from uoishelpers.resolvers import InputModelMixin
@strawberry.input(
    description="""EventInvitation insert mutation"""
)
class EventInvitationInsertGQLModel(InputModelMixin):
    getLoader = EventInvitationGQLModel.getLoader
    event_id: typing.Optional[IDType] = strawberry.field(
        description="""Event id to which invitation is sent - foreign key to Event entity.
        @relation(to: EventGQLModel, field: 'id')""",
        default=None,
    )

    user_id: typing.Optional[IDType] = strawberry.field(
        description="""User id who receive invitation - foreign key to User entity.
        @relation(to: UserGQLModel, field: 'id')""",
        default=None,
    )

    state_id: typing.Optional[IDType] = strawberry.field(
        description="""Invitation state identifier - foreign key to EventInvitationState.
        Represents invitation kind and presence type (invited, accepted, declined, etc.).""",
        default=None
    )

    id: typing.Optional[IDType] = strawberry.field(
        description="""client generated id""",
        default=None,
    )

@strawberry.input(
    description="""EventInvitation update mutation"""
)
class EventInvitationUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""id"""
    )

    lastchange: datetime.datetime = strawberry.field(
        description="""timestamp"""
    )

    state_id: typing.Optional[IDType] = strawberry.field(
        description="""Invitation state identifier - foreign key to EventInvitationState.
        Represents invitation kind and presence type (invited, accepted, declined, etc.).""",
        default=None
    )

    # user_id: typing.Optional[IDType] = strawberry.field(
    #     description="user id who receive invitation",
    #     default=None,
    # )

    changedby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""EventInvitation delete mutation"""
)
class EventInvitationDeleteGQLModel:
    id: IDType = strawberry.field(
        description="""EventInvitation id"""
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""EventInvitation lastchange"""
    )


@strawberry.type(
    description="""EventInvitation mutation"""
)
class EventInvitationMutation:
    from .EventGQLModel import EventGQLModel
    @strawberry.mutation(
        description="""Insert a EventInvitation""",
        permission_classes=[
            OnlyForAuthentized
            # SimpleInsertPermission[EventGQLModel](roles=["administrátor"])
        ],
        extensions=[
            # UpdatePermissionCheckRoleFieldExtension[GroupGQLModel](roles=["administrátor", "personalista"]),
            UserAccessControlExtension[InsertError, EventInvitationGQLModel](
                roles=[
                    "plánovací administrátor", 
                    # "personalista"
                ]
            ),
            UserRoleProviderExtension[InsertError, EventInvitationGQLModel](),
            RbacProviderExtension[InsertError, EventInvitationGQLModel](),
            LoadDataExtension[InsertError, EventInvitationGQLModel](
                getLoader=EventGQLModel.getLoader,
                primary_key_name="event_id"
            )
        ],
    )
    async def event_invitation_insert(
        self,
        info: strawberry.types.Info,
        invitation: EventInvitationInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[EventInvitationGQLModel, InsertError[EventInvitationGQLModel]]:
        from sqlalchemy import select
        from src.DBDefinitions import EventInvitationModel
        
        # Check if invitation already exists for this event and user
        if invitation.event_id and invitation.user_id:
            async_session_maker = info.context["asyncSessionMaker"]
            async with async_session_maker() as session:
                stmt = select(EventInvitationModel).where(
                    EventInvitationModel.event_id == invitation.event_id,
                    EventInvitationModel.user_id == invitation.user_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    return InsertError(
                        msg=f"Invitation for user {invitation.user_id} to event {invitation.event_id} already exists",
                        _input=invitation,
                        code=get_error_code("DUPLICATE_INVITATION")
                    )
        
        return await Insert[EventInvitationGQLModel].DoItSafeWay(info=info, entity=invitation)
    
    @strawberry.mutation(
        description="""Allows invited user to accept or decline the invitation""",
        permission_classes=[
            OnlyForAuthentized
            # SimpleInsertPermission[EventGQLModel](roles=["administrátor"])
        ],
        extensions=[
            LoadDataExtension[UpdateError, EventInvitationGQLModel]()
        ],
    )
    async def event_invitation_accept_decline(
        self,
        info: strawberry.types.Info,
        invitation: EventInvitationUpdateGQLModel,
        db_row: typing.Any,
    ) -> typing.Union[EventInvitationGQLModel, UpdateError[EventInvitationGQLModel]]:
        """
        Allows invited user to accept or decline the invitation.
        
        Only the invited user can change their invitation state to 'accepted' or 'declined'.
        Other state changes require organizer permissions.
        
        Args:
            invitation: Contains state_id to set (must be 'accepted' or 'declined')
            db_row: Loaded EventInvitationModel instance
            
        Returns:
            Updated EventInvitationGQLModel or UpdateError with authorization error
        """
        user = getUserFromInfo(info=info)
        if not user:
            return UpdateError[EventInvitationGQLModel](
                _entity=db_row,
                msg="User not found in context",
                code=get_error_code("USER_NOT_FOUND"),
                location="event_invitation_accept_decline",
                _input=invitation
            )
        
        # Handle both dict and object user types
        user_id = user["id"] if isinstance(user, dict) else (user.id if hasattr(user, "id") else None)
        if user_id is None:
            return UpdateError[EventInvitationGQLModel](
                _entity=db_row,
                msg="User missing ID attribute",
                code=get_error_code("USER_INVALID"),
                location="event_invitation_accept_decline",
                _input=invitation
            )
        
        if user_id == db_row.user_id:
            possible_values = set(
                IDType('7d2ef223-b60e-4e6d-b7d5-5fdc1f8e2ec2'), # 'accepted'
                IDType('d6a5e9e4-3e47-4c95-a4aa-b194dd2bc3a7'), # 'declined',  
            )
            if invitation.state_id in possible_values:
                return await Update[EventInvitationGQLModel].DoItSafeWay(info=info, entity=invitation)
        return UpdateError[EventInvitationGQLModel](
            _entity=db_row,
            msg="You are not authorized",
            code=get_error_code("NOT_AUTHORIZED"),
            location="event_invitation_accept_decline",
            _input=invitation
        )
        

    @strawberry.mutation(
        description="""Update the EventInvitation, caller must be organizer of the event""",
        permission_classes=[
            OnlyForAuthentized
        ],
        extensions=[
            LoadDataExtension[UpdateError, EventInvitationGQLModel]()
        ],
    )
    async def event_invitation_update(
        self,
        info: strawberry.types.Info,
        invitation: EventInvitationUpdateGQLModel,
        db_row: typing.Any,
        # rbacobject_id: IDType,
        # user_roles: typing.List[dict],
    ) -> typing.Union[EventInvitationGQLModel, UpdateError[EventInvitationGQLModel]]:
        """
        Update the EventInvitation - caller must be organizer of the event.
        
        Only users with organizer role for the event can update invitations.
        Regular users can only accept/decline their own invitations via event_invitation_accept_decline.
        
        Args:
            invitation: Update data for the invitation
            db_row: Loaded EventInvitationModel instance
            
        Returns:
            Updated EventInvitationGQLModel or UpdateError if not authorized
        """
        loader = EventInvitationGQLModel.getLoader(info=info)
        event_invitations = await loader.filter_by(event_id=db_row.event_id)
        user = getUserFromInfo(info=info)
        
        if not user:
            return UpdateError[EventInvitationGQLModel](
                _entity=db_row,
                msg="User not found in context",
                code=get_error_code("USER_NOT_FOUND"),
                location="event_invitation_update",
                _input=invitation
            )
        
        # Handle both dict and object user types
        user_id = user["id"] if isinstance(user, dict) else (user.id if hasattr(user, "id") else None)
        if user_id is None:
            return UpdateError[EventInvitationGQLModel](
                _entity=db_row,
                msg="User missing ID attribute",
                code=get_error_code("USER_INVALID"),
                location="event_invitation_update",
                _input=invitation
            )
        organizer_id = IDType("3265a488-bbfa-4c59-946c-7a7b059ee4f0")
        user_organizer_invitations = list(filter(
            lambda row: row.user_id == user_id and row.state_id == organizer_id,
            event_invitations
        ))
        if user_organizer_invitations:
            return await Update[EventInvitationGQLModel].DoItSafeWay(info=info, entity=invitation)        
        return UpdateError[EventInvitationGQLModel](
            _entity=db_row,
            msg="You are not organizer",
            code=get_error_code("NOT_ORGANIZER"),
            location="event_invitation_update",
            _input=invitation
        )


    @strawberry.mutation(
        description="""Delete a EventInvitation""",
        permission_classes=[
            SimpleDeletePermission[EventInvitationGQLModel](roles=["administrátor"])
        ]
    )
    async def event_invitation_delete(
        self,
        info: strawberry.types.Info,
        invitation: EventInvitationDeleteGQLModel
    ) -> typing.Optional[DeleteError[EventInvitationGQLModel]]:
        return await Delete[EventInvitationGQLModel].DoItSafeWay(info=info, entity=invitation)        