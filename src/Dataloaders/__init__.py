# from uoishelpers.dataloaders import createIdLoader, createFkeyLoader
# from functools import cache

from src.DBDefinitions import BaseModel
from src.DBDefinitions import (
    EventModel,
    EventInvitationModel,
    ApiKeyModel,
    UsageModel,
    UserModel,
    DocumentModel,
)

from uoishelpers.dataloaders.LoaderMapBase import LoaderMapBase
from uoishelpers.dataloaders.IDLoader import IDLoader
import src.DBDefinitions

class LoaderMap(LoaderMapBase[BaseModel]):
    """LoaderMap is a map of IDLoaders for all models in the BaseModel registry.
    It is used to create loaders for all models in the BaseModel registry.
    """
    BaseModel = BaseModel

    EventModel: IDLoader[src.DBDefinitions.EventModel] = None
    EventInvitationModel: IDLoader[src.DBDefinitions.EventInvitationModel] = None
    ApiKeyModel: IDLoader[src.DBDefinitions.ApiKeyModel] = None
    UsageModel: IDLoader[src.DBDefinitions.UsageModel] = None
    UserModel: IDLoader[src.DBDefinitions.UserModel] = None
    DocumentModel: IDLoader[src.DBDefinitions.DocumentModel] = None


    def __init__(self, session):
        super().__init__(session)

        self.EventModel = self.get(EventModel)
        self.EventInvitationModel = self.get(EventInvitationModel)
        self.ApiKeyModel = self.get(ApiKeyModel)
        self.UsageModel = self.get(UsageModel)
        self.UserModel = self.get(UserModel)
        self.DocumentModel = self.get(DocumentModel)

        # print(f"LoaderMap created with session: {session}")

def createLoadersContext(session):
    return {
        "loaders": LoaderMap(session)
    }
