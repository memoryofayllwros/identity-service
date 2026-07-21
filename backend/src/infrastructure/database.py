from typing import Optional

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from src.infrastructure.settings import get_settings
from src.infrastructure.persistence.mongo.documents import IDENTITY_DOCUMENT_MODELS

_client: Optional[AsyncMongoClient] = None


def get_mongodb_uri() -> str:
    return get_settings().mongodb_uri


def get_database_name() -> str:
    return get_settings().resolved_database_name()


async def init_database(
    *,
    mongodb_uri: Optional[str] = None,
    database_name: Optional[str] = None,
) -> AsyncDatabase:
    global _client

    settings = get_settings()
    uri = mongodb_uri or settings.mongodb_uri
    db_name = database_name or settings.resolved_database_name()

    _client = AsyncMongoClient(uri)
    database = _client[db_name]
    await init_beanie(database=database, document_models=IDENTITY_DOCUMENT_MODELS)
    return database


async def close_database() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
