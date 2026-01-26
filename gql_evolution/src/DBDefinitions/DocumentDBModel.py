import typing
import datetime
import dataclasses
import sqlalchemy
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, synonym

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property
from pgvector.sqlalchemy import Vector

from .BaseModel import BaseModel, UUIDColumn, UUIDFKey, IDType

###########################################################################################################################
#
# zde definujte sve SQLAlchemy modely
# je-li treba, muzete definovat modely obsahujici jen id polozku, na ktere se budete odkazovat
#
###########################################################################################################################
class DocumentModel(BaseModel):
    __tablename__ = "document_evolution"

    path_attribute_name = "path"
    parent_attribute_name = "masterdocument"
    parent_id_attribute_name = "masterdocument_id"
    children_attribute_name = "subdocuments"

    # Materialized path technique
    path: Mapped[typing.Optional[str]] = mapped_column(
        index=True,
        nullable=True,
        default=None,
        comment="Materialized path technique, not implemented"
    )

    name: Mapped[typing.Optional[str]] = mapped_column(default=None, nullable=True)
    name_en: Mapped[typing.Optional[str]] = mapped_column(default=None, nullable=True)
    description: Mapped[typing.Optional[str]] = mapped_column(default=None, nullable=True)
    url: Mapped[typing.Optional[str]] = mapped_column(default=None, nullable=True)
    embedding: Mapped[typing.Optional[list[float]]] = mapped_column(Vector(1536), nullable=True, default=None)
    embedding_location: Mapped[typing.Optional[str]] = mapped_column(default=None, nullable=True)
    
    # the real column in the DB
    masterdocument_id: Mapped[IDType] = mapped_column(
        ForeignKey("document_evolution.id"),
        nullable=True,
        default=None,
        index=True,
    )

    masterdocument = relationship(
        "DocumentModel",
        viewonly=True, 
        remote_side="DocumentModel.id",
        uselist=False,
        back_populates="subdocuments",
    ) # https://docs.sqlalchemy.org/en/20/orm/self_referential.html

    subdocuments = relationship(
        "DocumentModel", 
        back_populates="masterdocument",
        uselist=True,
        init=True,
        cascade="save-update"
    ) # https://docs.sqlalchemy.org/en/20/orm/self_referential.html
    # https://docs.sqlalchemy.org/en/20/_modules/examples/materialized_paths/materialized_paths.html

    fragments = relationship(
        "DocumentFragmentModel",
        back_populates="document",
        primaryjoin="DocumentModel.id==DocumentFragmentModel.document_id",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class DocumentFragmentModel(BaseModel):
    __tablename__ = "document_fragments"

    document_id: Mapped[IDType] = UUIDFKey(
        ForeignKey("document_evolution.id"),
        nullable=False,
        comment="Parent document"
    )

    title: Mapped[typing.Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    summary: Mapped[typing.Optional[str]] = mapped_column(String(1024), default=None, nullable=True)
    content: Mapped[typing.Optional[str]] = mapped_column(Text, default=None, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[typing.Optional[list[float]]] = mapped_column(Vector(1536), nullable=True, default=None)

    document = relationship(
        "DocumentModel",
        back_populates="fragments",
        primaryjoin="DocumentFragmentModel.document_id==DocumentModel.id",
        lazy="joined"
    )
