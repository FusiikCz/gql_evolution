import datetime
import strawberry

from .query import Query
from .mutation import Mutation

timedelta = strawberry.scalar(
    # NewType("TimeDelta", float),
    datetime.timedelta,
    name="timedelta",
    serialize=lambda v: v.total_seconds() / 60,
    parse_value=lambda v: datetime.timedelta(minutes=v),
)


from .BaseGQLModel import Relation
from .BaseGQLModel import BaseGQLModel
from .UserGQLModel import UserGQLModel
from .ApiKeyGQLModel import ApiKeyGQLModel, ApiKeyInsertResponse
from .UsageGQLModel import UsageGQLModel
from .DocumentGQLModel import DocumentGQLModel
from .DocumentFragmentGQLModel import DocumentFragmentGQLModel
from .EventGQLModel import EventGQLModel
from .EventInvitationGQLModel import EventInvitationGQLModel
from .EventInvitationStateGQLModel import EventInvitationStateGQLModel
from .VectorFilters import VectorFilter, VectorSimilarityFilter, VectorDistanceFilter
from .EndpointConfigGQLModel import EndpointConfigGQLModel

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    types=(UserGQLModel, BaseGQLModel, ApiKeyGQLModel, ApiKeyInsertResponse, UsageGQLModel, DocumentGQLModel, DocumentFragmentGQLModel, EventGQLModel, EventInvitationGQLModel, EventInvitationStateGQLModel, EndpointConfigGQLModel), 
    scalar_overrides={datetime.timedelta: timedelta._scalar_definition},

    extensions=[],
    schema_directives=[Relation]
    
)

import os
import logging

from uoishelpers.schema import WhoAmIExtension, ProfilingExtension, PrometheusExtension

disable_whoami = os.getenv("DISABLE_WHOAMI_EXTENSION", "").lower() in ["true", "1", "yes"]
if not disable_whoami:
    schema.extensions.append(WhoAmIExtension)
    logging.info("WhoAmIExtension enabled")
else:
    logging.info("WhoAmIExtension disabled via DISABLE_WHOAMI_EXTENSION")

# ProfilingExtension can be enabled for debugging/development
# schema.extensions.append(ProfilingExtension)  # Temporarily disabled for debugging

schema.extensions.append(PrometheusExtension(prefix="GQL_Evolution"))

from uoishelpers.gqlpermissions.RolePermissionSchemaExtension import RolePermissionSchemaExtension
schema.extensions.append(RolePermissionSchemaExtension)

