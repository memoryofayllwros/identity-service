#!/usr/bin/env python3
"""Export Identity collections for a single tenant into JSON files."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pymongo import AsyncMongoClient

from src.infrastructure.settings import get_settings
from src.models import IDENTITY_DOCUMENT_MODELS

IDENTITY_COLLECTIONS = tuple(model.Settings.name for model in IDENTITY_DOCUMENT_MODELS)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Export identity_db tenant data.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    settings = get_settings()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.resolved_database_name()]
    try:
        for name in IDENTITY_COLLECTIONS:
            if name in ("users",):
                docs = await db[name].find({}).to_list(length=None)
            else:
                docs = await db[name].find({"tenant_id": args.tenant_id}).to_list(length=None)
            path = out / f"{name}.json"
            serializable = [{k: v for k, v in doc.items() if k != "_id"} for doc in docs]
            path.write_text(json.dumps(serializable, indent=2, default=str), encoding="utf-8")
            print(f"  {name}: exported {len(serializable)} -> {path}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
