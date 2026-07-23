"""Pytest fixtures for Identity platform."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from src.infrastructure.persistence.mongo.documents import IDENTITY_DOCUMENT_MODELS
from src.shared.constants import DEFAULT_TENANT_ID
from src.shared.tenant_context import bind_tenant_id, reset_tenant_id

os.environ.setdefault("TENANT_INSTANCE_ID", DEFAULT_TENANT_ID)
os.environ.setdefault("DEPLOYMENT_ID", "test-deployment")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REFRESH_SECRET_KEY", "test-refresh-secret-key")


@pytest.fixture(autouse=True)
def _bind_default_tenant():
    token = bind_tenant_id(DEFAULT_TENANT_ID)
    try:
        yield
    finally:
        reset_tenant_id(token)


@pytest_asyncio.fixture(autouse=True)
async def _init_beanie_for_expressions():
    from beanie import init_beanie

    client = AsyncMongoMockClient()
    await init_beanie(
        database=client.get_database("test_identity"),
        document_models=IDENTITY_DOCUMENT_MODELS,
    )
    yield
