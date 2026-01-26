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
from .EndpointConfigDBModel import EndpointConfigModel

async def startEngine(connectionstring, makeDrop=False, makeUp=True):
    """Provede nezbytne ukony a vrati asynchronni SessionMaker"""
    asyncEngine = create_async_engine(connectionstring)

    async with asyncEngine.begin() as conn:
        dialect_name = getattr(getattr(conn, "dialect", None), "name", None) or getattr(asyncEngine.dialect, "name", None)
        if makeDrop:
            await conn.run_sync(BaseModel.metadata.drop_all)
            logging.info("BaseModel.metadata.drop_all finished")

        # Create pgvector extension BEFORE creating tables (Postgres only)
        if dialect_name == "postgresql":
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Fix: Remove duplicate indexes that may have been created
        # This fixes the issue where token_prefix had both index=True and explicit Index in __table_args__
        try:
            await conn.exec_driver_sql("DROP INDEX IF EXISTS ix_endpoint_configs_token_prefix;")
            logging.debug("Removed duplicate index ix_endpoint_configs_token_prefix if it existed")
        except Exception as e:
            # Ignore errors - index might not exist
            logging.debug(f"Could not drop duplicate index (may not exist): {e}")

        if makeUp:
            try:
                await conn.run_sync(BaseModel.metadata.create_all, checkfirst=True)
                logging.info("BaseModel.metadata.create_all finished")
                
                # Fix: Ensure embedding columns are nullable (pgvector may create NOT NULL by default)
                if dialect_name == "postgresql":
                    try:
                        await conn.exec_driver_sql(
                            "ALTER TABLE document_evolution ALTER COLUMN embedding DROP NOT NULL;"
                        )
                        logging.info("Fixed document_evolution.embedding to be nullable")
                    except Exception as e:
                        # Table might not exist or column might already be nullable
                        logging.debug(f"Could not alter document_evolution.embedding: {e}")
                        pass
                        
                    try:
                        await conn.exec_driver_sql(
                            "ALTER TABLE document_fragments ALTER COLUMN embedding DROP NOT NULL;"
                        )
                        logging.info("Fixed document_fragments.embedding to be nullable")
                    except Exception as e:
                        # Table might not exist or column might already be nullable
                        logging.debug(f"Could not alter document_fragments.embedding: {e}")
                        pass
                    
            except sqlalchemy.exc.NoReferencedTableError as e:
                logging.error(f"Unable to automatically create tables: {e}")
                logging.error("Unable automatically create tables")
                return None
            except sqlalchemy.exc.ProgrammingError as e:
                # Handle duplicate index/table errors gracefully
                error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
                if "already exists" in error_str.lower() or "duplicate" in error_str.lower():
                    logging.warning(f"Database object already exists (ignoring): {error_str}")
                    # Continue - this is not a fatal error
                else:
                    # Re-raise if it's a different programming error
                    raise
            

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
