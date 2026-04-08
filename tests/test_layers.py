import json
import os
import tempfile

import chromadb

from mempalace.config import MempalaceConfig
from mempalace.layers import MemoryStack


def _write_config(tmpdir: str, palace_path: str, collection_name: str = "mempalace_drawers") -> str:
    cfg_dir = os.path.join(tmpdir, "config")
    os.makedirs(cfg_dir)
    with open(os.path.join(cfg_dir, "config.json"), "w") as f:
        json.dump(
            {
                "palace_path": palace_path,
                "collection_name": collection_name,
            },
            f,
        )
    return cfg_dir


def test_memory_stack_uses_configured_collection_name(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    palace_path = os.path.join(tmpdir, "palace")
    cfg = MempalaceConfig(config_dir=_write_config(tmpdir, palace_path, "custom_drawers"))

    client = chromadb.PersistentClient(path=palace_path)
    collection = client.get_or_create_collection("custom_drawers")
    collection.add(
        ids=["drawer_custom_1", "drawer_custom_2"],
        documents=[
            "Billing memory stored in the configured custom collection.",
            "Planning memory stored in the configured custom collection.",
        ],
        metadatas=[
            {"wing": "project", "room": "finance", "source_file": "billing.md"},
            {"wing": "notes", "room": "planning", "source_file": "plan.md"},
        ],
    )

    monkeypatch.setattr("mempalace.drawer_store.MempalaceConfig", lambda: cfg)
    stack = MemoryStack()

    status = stack.status()
    assert status["total_drawers"] == 2
    assert "configured custom collection" in stack.recall(wing="project")
    assert "configured custom collection" in stack.search("planning")


def test_memory_stack_explicit_palace_path_uses_default_collection(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    default_palace_path = os.path.join(tmpdir, "explicit-palace")
    cfg = MempalaceConfig(
        config_dir=_write_config(tmpdir, os.path.join(tmpdir, "ignored"), "custom_drawers")
    )

    client = chromadb.PersistentClient(path=default_palace_path)
    collection = client.get_or_create_collection("mempalace_drawers")
    collection.add(
        ids=["drawer_default_1"],
        documents=["This drawer lives in the default collection for the explicit path."],
        metadatas=[{"wing": "project", "room": "backend", "source_file": "auth.py"}],
    )

    monkeypatch.setattr("mempalace.drawer_store.MempalaceConfig", lambda: cfg)
    stack = MemoryStack(palace_path=default_palace_path)

    assert stack.status()["total_drawers"] == 1
    assert "default collection for the explicit path" in stack.recall(wing="project")
