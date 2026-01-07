import datetime
import typing
import strawberry

import strawberry.types
from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
)
from uoishelpers.resolvers import (
    getLoadersFromInfo,
    createInputs2,
    InputModelMixin,
    InsertError,
    Insert,
    UpdateError,
    Update,
    DeleteError,
    Delete,
    PageResolver,
    ScalarResolver,
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType

DocumentGQLModel = typing.Annotated["DocumentGQLModel", strawberry.lazy(".DocumentGQLModel")]


@createInputs2
class DocumentFragmentInputFilter:
    id: IDType
    document_id: IDType
    title: str
    summary: str
    order_index: int


@strawberry.federation.type(
    description="""Atomic fragment of a document with semantic embedding""",
    keys=["id"]
)
class DocumentFragmentGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).DocumentFragmentModel

    document_id: IDType = strawberry.field(
        description="""Parent document identifier""",
        permission_classes=[OnlyForAuthentized],
    )

    title: typing.Optional[str] = strawberry.field(
        description="""Fragment title or heading""",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    summary: typing.Optional[str] = strawberry.field(
        description="""Short fragment summary""",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    content: typing.Optional[str] = strawberry.field(
        description="""Full fragment content""",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    order_index: int = strawberry.field(
        description="""Order of fragment within the document""",
        permission_classes=[OnlyForAuthentized],
    )

    embedding: typing.Optional[typing.List[float]] = strawberry.field(
        description="""Semantic embedding vector""",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    document: typing.Optional[DocumentGQLModel] = strawberry.field(
        description="""Parent document""",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[DocumentGQLModel](fkey_field_name="document_id"),
    )


@strawberry.interface(description="""Document fragment queries""")
class DocumentFragmentQuery:
    document_fragment_by_id: typing.Optional[DocumentFragmentGQLModel] = strawberry.field(
        description="""Get a document fragment by its id""",
        permission_classes=[OnlyForAuthentized],
        resolver=DocumentFragmentGQLModel.load_with_loader,
    )

    document_fragment_page: typing.List[DocumentFragmentGQLModel] = strawberry.field(
        description="""Get a page of document fragments""",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[DocumentFragmentGQLModel](whereType=DocumentFragmentInputFilter),
    )


@strawberry.input(description="""Input type for creating a document fragment""")
class DocumentFragmentInsertGQLModel(InputModelMixin):
    getLoader = DocumentFragmentGQLModel.getLoader

    document_id: IDType = strawberry.field(
        description="""Parent document id"""
    )
    title: typing.Optional[str] = strawberry.field(
        description="""Fragment title""",
        default=None,
    )
    summary: typing.Optional[str] = strawberry.field(
        description="""Fragment summary""",
        default=None,
    )
    content: typing.Optional[str] = strawberry.field(
        description="""Fragment content""",
        default=None,
    )
    order_index: int = strawberry.field(
        description="""Order of fragment within the document""",
        default=0,
    )
    embedding: typing.Optional[typing.List[float]] = strawberry.field(
        description="""Semantic embedding vector""",
        default=None,
    )

    id: typing.Optional[IDType] = strawberry.field(
        description="""Fragment id""",
        default=None,
    )

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None


@strawberry.input(description="""Input type for updating a document fragment""")
class DocumentFragmentUpdateGQLModel(InputModelMixin):
    id: IDType = strawberry.field(description="""Fragment id""")
    lastchange: datetime.datetime = strawberry.field(description="""Last change token""")

    title: typing.Optional[str] = strawberry.field(
        description="""Fragment title""",
        default=None,
    )
    summary: typing.Optional[str] = strawberry.field(
        description="""Fragment summary""",
        default=None,
    )
    content: typing.Optional[str] = strawberry.field(
        description="""Fragment content""",
        default=None,
    )
    order_index: typing.Optional[int] = strawberry.field(
        description="""Order of fragment within the document""",
        default=None,
    )
    embedding: typing.Optional[typing.List[float]] = strawberry.field(
        description="""Semantic embedding vector""",
        default=None,
    )

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="""Input type for deleting a document fragment""")
class DocumentFragmentDeleteGQLModel(InputModelMixin):
    id: IDType = strawberry.field(description="""Fragment id""")
    lastchange: datetime.datetime = strawberry.field(description="""Last change token""")


@strawberry.interface(description="""Document fragment mutations""")
class DocumentFragmentMutation:
    @strawberry.mutation(
        description="""Insert a document fragment""",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[InsertError, DocumentFragmentGQLModel](
                roles=["dokumentarista"]
            ),
            UserRoleProviderExtension[InsertError, DocumentFragmentGQLModel](),
            RbacProviderExtension[InsertError, DocumentFragmentGQLModel](),
            LoadDataExtension[InsertError, DocumentFragmentGQLModel](),
        ],
    )
    async def document_fragment_insert(
        self,
        info: strawberry.Info,
        fragment: DocumentFragmentInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[DocumentFragmentGQLModel, InsertError[DocumentFragmentGQLModel]]:
        return await Insert[DocumentFragmentGQLModel].DoItSafeWay(info=info, entity=fragment)

    @strawberry.mutation(
        description="""Update a document fragment""",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[UpdateError, DocumentFragmentGQLModel](
                roles=["dokumentarista"]
            ),
            UserRoleProviderExtension[UpdateError, DocumentFragmentGQLModel](),
            RbacProviderExtension[UpdateError, DocumentFragmentGQLModel](),
            LoadDataExtension[UpdateError, DocumentFragmentGQLModel](),
        ],
    )
    async def document_fragment_update(
        self,
        info: strawberry.Info,
        fragment: DocumentFragmentUpdateGQLModel,
    ) -> typing.Union[DocumentFragmentGQLModel, UpdateError[DocumentFragmentGQLModel]]:
        return await Update[DocumentFragmentGQLModel].DoItSafeWay(info=info, entity=fragment)

    @strawberry.mutation(
        description="""Delete a document fragment""",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[DeleteError, DocumentFragmentGQLModel](
                roles=["dokumentarista"]
            ),
            UserRoleProviderExtension[DeleteError, DocumentFragmentGQLModel](),
            RbacProviderExtension[DeleteError, DocumentFragmentGQLModel](),
            LoadDataExtension[DeleteError, DocumentFragmentGQLModel](),
        ],
    )
    async def document_fragment_delete(
        self,
        info: strawberry.Info,
        fragment: DocumentFragmentDeleteGQLModel,
    ) -> typing.Optional[DeleteError[DocumentFragmentGQLModel]]:
        return await Delete[DocumentFragmentGQLModel].DoItSafeWay(info=info, entity=fragment)

