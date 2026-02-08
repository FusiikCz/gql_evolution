import typing
import datetime
import strawberry

from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
    SimpleInsertPermission,
    SimpleUpdatePermission,
    SimpleDeletePermission,
)
from uoishelpers.resolvers import (
    getLoadersFromInfo,
    createInputs2,
    Insert,
    InsertError,
    Update,
    UpdateError,
    Delete,
    DeleteError,
    PageResolver,
    ScalarResolver,
    VectorResolver,
)

from .BaseGQLModel import BaseGQLModel, IDType, Relation


EventInvitationStateGQLModel = typing.Annotated["EventInvitationStateGQLModel", strawberry.lazy(".EventInvitationStateGQLModel")]


@createInputs2
class EventInvitationStateInputFilter:
    id: IDType
    name: str
    name_en: str
    parent_id: IDType
    is_final: bool



@strawberry.federation.type(
    keys=["id"],
    description="""Tree-structured lookup for Event Invitation states.
States define the lifecycle of invitations (invited, accepted, declined, attended, excused, organizer).
These are hierarchical (tree) to support grouping and AI-friendly selection."""
)
class EventInvitationStateGQLModel(BaseGQLModel):

    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).EventInvitationStateModel

    name: str = strawberry.field(
        description="State code (invited, accepted, declined, ...)",
        permission_classes=[OnlyForAuthentized]
    )

    name_en: typing.Optional[str] = strawberry.field(
        description="English display name",
        default=None,
        permission_classes=[OnlyForAuthentized]
    )

    description: typing.Optional[str] = strawberry.field(
        description="State description",
        default=None,
        permission_classes=[OnlyForAuthentized]
    )

    parent_id: typing.Optional[IDType] = strawberry.field(
        description="""Parent state id - foreign key to EventInvitationState.
        @relation(to: EventInvitationStateGQLModel, field: 'id')""",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="EventInvitationStateGQLModel")]
    )

    is_final: typing.Optional[bool] = strawberry.field(
        description="True if this state is terminal",
        default=False,
        permission_classes=[OnlyForAuthentized]
    )

    parent: typing.Optional[EventInvitationStateGQLModel] = strawberry.field(
        description="Parent state",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[EventInvitationStateGQLModel](fkey_field_name="parent_id")
    )

    children: typing.List[EventInvitationStateGQLModel] = strawberry.field(
        description="Child states",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[EventInvitationStateGQLModel](
            fkey_field_name="parent_id",
            whereType=EventInvitationStateInputFilter
        )
    )


@strawberry.type(description="EventInvitationState queries")
class EventInvitationStateQuery:

    event_invitation_state_by_id: typing.Optional[EventInvitationStateGQLModel] = strawberry.field(
        description="Invitation state by id",
        permission_classes=[OnlyForAuthentized],
        resolver=EventInvitationStateGQLModel.load_with_loader
    )

    event_invitation_state_page: typing.List[EventInvitationStateGQLModel] = strawberry.field(
        description="Invitation states page",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[EventInvitationStateGQLModel](whereType=EventInvitationStateInputFilter)
    )


from uoishelpers.resolvers import InputModelMixin


@strawberry.input(description="EventInvitationState insert mutation")
class EventInvitationStateInsertGQLModel(InputModelMixin):
    getLoader = EventInvitationStateGQLModel.getLoader
    name: str = strawberry.field(description="State code")
    name_en: typing.Optional[str] = strawberry.field(default=None, description="English display name")
    description: typing.Optional[str] = strawberry.field(default=None, description="State description")
    parent_id: typing.Optional[IDType] = strawberry.field(
        default=None,
        description="""Parent state id.
        @relation(to: EventInvitationStateGQLModel, field: 'id')"""
    )
    is_final: typing.Optional[bool] = strawberry.field(default=False, description="True if terminal")


@strawberry.input(description="EventInvitationState update mutation")
class EventInvitationStateUpdateGQLModel(InputModelMixin):
    getLoader = EventInvitationStateGQLModel.getLoader
    id: IDType = strawberry.field(description="State id")
    lastchange: datetime.datetime = strawberry.field(
        description="""Last modification timestamp for optimistic locking.
        Must match the lastchange value from the current entity to prevent concurrent modification conflicts."""
    )
    name: typing.Optional[str] = strawberry.field(default=None, description="State code")
    name_en: typing.Optional[str] = strawberry.field(default=None, description="English display name")
    description: typing.Optional[str] = strawberry.field(default=None, description="State description")
    parent_id: typing.Optional[IDType] = strawberry.field(default=None, description="Parent state id")
    is_final: typing.Optional[bool] = strawberry.field(default=None, description="True if terminal")


@strawberry.input(description="EventInvitationState delete mutation")
class EventInvitationStateDeleteGQLModel(InputModelMixin):
    getLoader = EventInvitationStateGQLModel.getLoader
    id: IDType = strawberry.field(description="State id")
    lastchange: datetime.datetime = strawberry.field(
        description="""Last modification timestamp for optimistic locking.
        Must match the lastchange value from the current entity to prevent concurrent modification conflicts."""
    )


@strawberry.interface(description="EventInvitationState mutations")
class EventInvitationStateMutation:

    @strawberry.mutation(
        description="Insert an invitation state",
        permission_classes=[
            OnlyForAuthentized,
            SimpleInsertPermission[EventInvitationStateGQLModel](roles=["administrátor"])
        ],
    )
    async def event_invitation_state_insert(
        self, info: strawberry.types.Info, state: EventInvitationStateInsertGQLModel
    ) -> typing.Union[EventInvitationStateGQLModel, InsertError[EventInvitationStateGQLModel]]:
        return await Insert[EventInvitationStateGQLModel].DoItSafeWay(info=info, entity=state)

    @strawberry.mutation(
        description="Update an invitation state",
        permission_classes=[
            OnlyForAuthentized,
            SimpleUpdatePermission[EventInvitationStateGQLModel](roles=["administrátor"])
        ],
    )
    async def event_invitation_state_update(
        self, info: strawberry.types.Info, state: EventInvitationStateUpdateGQLModel
    ) -> typing.Union[EventInvitationStateGQLModel, UpdateError[EventInvitationStateGQLModel]]:
        return await Update[EventInvitationStateGQLModel].DoItSafeWay(info=info, entity=state)

    @strawberry.mutation(
        description="Delete an invitation state",
        permission_classes=[
            OnlyForAuthentized,
            SimpleDeletePermission[EventInvitationStateGQLModel](roles=["administrátor"])
        ],
    )
    async def event_invitation_state_delete(
        self, info: strawberry.types.Info, state: EventInvitationStateDeleteGQLModel
    ) -> typing.Optional[DeleteError[EventInvitationStateGQLModel]]:
        return await Delete[EventInvitationStateGQLModel].DoItSafeWay(info=info, entity=state)
