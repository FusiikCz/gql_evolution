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

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from .VectorFilters import VectorFilter

DocumentGQLModel = typing.Annotated["DocumentGQLModel", strawberry.lazy(".DocumentGQLModel")]


@createInputs2
class DocumentFragmentInputFilter:
    id: IDType
    document_id: IDType
    title: str
    summary: str
    order_index: int
    
    embedding: typing.Optional[VectorFilter] = strawberry.field(
        default=None,
        description="""Vector similarity filter for AI embeddings.
        Use _similarity to find document fragments similar to a given embedding vector.
        Use _distance to find fragments within a certain distance.
        Example: {"embedding": {"_similarity": {"vector": [...], "threshold": 0.8}}}
        This enables semantic search: find fragments with similar meaning to a query vector.
        The vector dimension must match stored embeddings (typically 768 or 1536 dimensions).
        Useful for AI-powered content discovery: "Find fragments similar to this text".""",
    )


@strawberry.federation.type(
    description="""Entity representing a Document Fragment - a semantic chunk of a larger Document.
Fragments are used to break down large documents into smaller, manageable pieces for processing.
Each fragment has its own embedding vector for semantic similarity search.
Fragments maintain order within their parent document via order_index.
Fragments are useful for AI-powered search: finding similar content, semantic matching, etc.
Example use cases:
- "Find fragments similar to a query vector"
- "Get all fragments of a document in order"
- "Search fragments by content or title"
- "Find related fragments using embedding similarity"
Use DocumentFragmentInputFilter with filters like title, content, and vector similarity filters.""",
    keys=["id"]
)
class DocumentFragmentGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).DocumentFragmentModel

    document_id: IDType = strawberry.field(
        description="""Parent document identifier - foreign key to Document entity that owns this fragment.
        @relation(to: DocumentGQLModel, field: 'id')""",
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="DocumentGQLModel")],
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
        description="""Parent document id - foreign key to Document entity that owns this fragment.
        @relation(to: DocumentGQLModel, field: 'id')"""
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
    lastchange: datetime.datetime = strawberry.field(
        description="""Last modification timestamp for optimistic locking.
        Must match the lastchange value from the current entity to prevent concurrent modification conflicts."""
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
    lastchange: datetime.datetime = strawberry.field(
        description="""Last modification timestamp for optimistic locking.
        Must match the lastchange value from the current entity to prevent concurrent modification conflicts."""
    )


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

