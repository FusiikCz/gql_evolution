import logging
import sqlalchemy

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from .BaseModel import BaseModel
from .EventDBModel import EventModel
from .EventInvitationModel import EventInvitationModel
from .ApiKeyDBModel import ApiKeyModel
from .UsageDBModel import UsageModel
from .UserDBModel import UserModel
from .DocumentDBModel import DocumentModel, DocumentFragmentModel

async def startEngine(connectionstring, makeDrop=False, makeUp=True):
    """Provede nezbytne ukony a vrati asynchronni SessionMaker"""
    asyncEngine = create_async_engine(connectionstring)

    async with asyncEngine.begin() as conn:
        if makeDrop:
            await conn.run_sync(BaseModel.metadata.drop_all)
            print("BaseModel.metadata.drop_all finished")

        # Create pgvector extension BEFORE creating tables
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")

        if makeUp:
            try:
                await conn.run_sync(BaseModel.metadata.create_all)
                print("BaseModel.metadata.create_all finished")
                
                # Fix: Ensure embedding columns are nullable (pgvector may create NOT NULL by default)
                try:
                    await conn.exec_driver_sql(
                        "ALTER TABLE document_evolution ALTER COLUMN embedding DROP NOT NULL;"
                    )
                    print("Fixed document_evolution.embedding to be nullable")
                except Exception as e:
                    # Table might not exist or column might already be nullable
                    pass
                    
                try:
                    await conn.exec_driver_sql(
                        "ALTER TABLE document_fragments ALTER COLUMN embedding DROP NOT NULL;"
                    )
                    print("Fixed document_fragments.embedding to be nullable")
                except Exception as e:
                    # Table might not exist or column might already be nullable
                    pass
                    
            except sqlalchemy.exc.NoReferencedTableError as e:
                print(e)
                print("Unable automaticaly create tables")
                return None
            

    async_sessionMaker = async_sessionmaker(
        asyncEngine, expire_on_commit=False
    )
    return async_sessionMaker

import os

def ComposeConnectionString():
    """Odvozuje connectionString z promennych prostredi (nebo z Docker Envs, coz je fakticky totez).
    Lze predelat na napr. konfiguracni file.
    """
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "example")
    database = os.environ.get("POSTGRES_DB", "data")
    hostWithPort = os.environ.get("POSTGRES_HOST", "localhost:5432")

    driver = "postgresql+asyncpg"  # "postgresql+psycopg2"
    connectionstring = f"{driver}://{user}:{password}@{hostWithPort}/{database}"
    connectionstring = os.environ.get("CONNECTION_STRING", connectionstring)

    return connectionstring
