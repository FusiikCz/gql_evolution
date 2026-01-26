# from uoishelpers.dataloaders import createIdLoader, createFkeyLoader
# from functools import cache

from src.DBDefinitions import BaseModel
from src.DBDefinitions import (
    EventModel,
    EventInvitationModel,
    EventInvitationStateModel,
    ApiKeyModel,
    UsageModel,
    UserModel,
    DocumentModel,
    DocumentFragmentModel,
    EndpointConfigModel,
)

from uoishelpers.dataloaders.LoaderMapBase import LoaderMapBase
from uoishelpers.dataloaders.IDLoader import IDLoader
import src.DBDefinitions


def getUserFromInfo(info):
    """Return user from resolver info context, with fallback."""
    try:
        from uoishelpers.resolvers import getUserFromInfo as _get_user
        return _get_user(info)
    except Exception:
        context = getattr(info, "context", None) or {}
        return context.get("user")

class LoaderMap(LoaderMapBase[BaseModel]):
    """LoaderMap is a map of IDLoaders for all models in the BaseModel registry.
    It is used to create loaders for all models in the BaseModel registry.
    """
    BaseModel = BaseModel

    EventModel: IDLoader[src.DBDefinitions.EventModel] = None
    EventInvitationModel: IDLoader[src.DBDefinitions.EventInvitationModel] = None
    EventInvitationStateModel: IDLoader[src.DBDefinitions.EventInvitationStateModel] = None
    ApiKeyModel: IDLoader[src.DBDefinitions.ApiKeyModel] = None
    UsageModel: IDLoader[src.DBDefinitions.UsageModel] = None
    UserModel: IDLoader[src.DBDefinitions.UserModel] = None
    DocumentModel: IDLoader[src.DBDefinitions.DocumentModel] = None
    DocumentFragmentModel: IDLoader[src.DBDefinitions.DocumentFragmentModel] = None
    EndpointConfigModel: IDLoader[src.DBDefinitions.EndpointConfigModel] = None


    def __init__(self, session):
        super().__init__(session)

        self.EventModel = self.get(EventModel)
        self.EventInvitationModel = self.get(EventInvitationModel)
        self.EventInvitationStateModel = self.get(EventInvitationStateModel)
        self.ApiKeyModel = self.get(ApiKeyModel)
        self.UsageModel = self.get(UsageModel)
        self.UserModel = self.get(UserModel)
        self.DocumentModel = self.get(DocumentModel)
        self.DocumentFragmentModel = self.get(DocumentFragmentModel)
        self.EndpointConfigModel = self.get(EndpointConfigModel)

        # print(f"LoaderMap created with session: {session}")

def createLoadersContext(session):
    return {
        "loaders": LoaderMap(session)
    }


__all__ = [
    "LoaderMap",
    "createLoadersContext",
    "getUserFromInfo",
]
