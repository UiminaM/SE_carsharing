"""Async MongoDB client factory with connection pooling."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

def create_mongo_client(
    uri: str,
    max_pool_size: int = 50,
    min_pool_size: int = 10,
) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
        uri,
        maxPoolSize=max_pool_size,
        minPoolSize=min_pool_size,
        serverSelectionTimeoutMS=5000,
    )

def get_mongo_database(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    return client[db_name]
