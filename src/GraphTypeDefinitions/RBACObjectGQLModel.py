"""
Wrapper for RBACObjectGQLModel from uoishelpers to make it a base type in Federation.
This is needed because Apollo Federation requires base type definitions, not just extensions.
"""
import strawberry
import typing
from uoishelpers.gqlpermissions import RBACObjectGQLModel as _RBACObjectGQLModel

# Create a base type definition with @key directive for Federation
# This ensures Apollo Federation sees it as a base type, not an extension
@strawberry.federation.type(keys=["id"])
class RBACObjectGQLModel:
    """RBAC Object model for Federation - base type definition"""
    id: strawberry.ID
    
    def __init__(self, id: typing.Union[strawberry.ID, str, None] = None):
        if id is None:
            raise ValueError("RBACObjectGQLModel requires an id")
        self.id = strawberry.ID(id) if not isinstance(id, strawberry.ID) else id
    
    @classmethod
    def from_original(cls, original: _RBACObjectGQLModel):
        """Convert from original uoishelpers RBACObjectGQLModel"""
        return cls(id=original.id)
