from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .BaseModel import BaseModel, UUIDFKey, IDType


class EventInvitationStateModel(BaseModel):
    __tablename__ = "event_invitation_states"

    name: Mapped[str] = mapped_column(
        default="",
        nullable=False,
        comment="State code (invited, accepted, declined, ...)"
    )
    name_en: Mapped[Optional[str]] = mapped_column(
        default=None,
        nullable=True,
        comment="English display name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        default=None,
        nullable=True,
        comment="State description"
    )

    parent_id: Mapped[Optional[IDType]] = UUIDFKey(
        ForeignKey("event_invitation_states.id"),
        default=None,
        nullable=True,
        comment="Parent state for tree hierarchy"
    )

    is_final: Mapped[Optional[bool]] = mapped_column(
        default=False,
        nullable=True,
        comment="True if this state is terminal (no further transitions)"
    )

    parent = relationship(
        "EventInvitationStateModel",
        remote_side="EventInvitationStateModel.id",
        viewonly=True
    )

    children = relationship(
        "EventInvitationStateModel",
        primaryjoin="EventInvitationStateModel.id==foreign(EventInvitationStateModel.parent_id)",
        viewonly=True
    )

    event_invitations = relationship(
        "EventInvitationModel",
        primaryjoin="EventInvitationStateModel.id==EventInvitationModel.state_id",
        viewonly=True
    )
