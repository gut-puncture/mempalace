"""
test_searcher.py — Tests for the programmatic search_memories API.

Tests the library-facing search interface (not the CLI print variant).
"""

import json
import os
import tempfile

import chromadb

from mempalace.config import MempalaceConfig
from mempalace.searcher import search_memories


class TestSearchMemories:
    def test_basic_search(self, palace_path, seeded_collection):
        result = search_memories("JWT authentication", palace_path)
        assert "results" in result
        assert len(result["results"]) > 0
        assert result["query"] == "JWT authentication"

    def test_wing_filter(self, palace_path, seeded_collection):
        result = search_memories("planning", palace_path, wing="notes")
        assert all(r["wing"] == "notes" for r in result["results"])

    def test_room_filter(self, palace_path, seeded_collection):
        result = search_memories("database", palace_path, room="backend")
        assert all(r["room"] == "backend" for r in result["results"])

    def test_wing_and_room_filter(self, palace_path, seeded_collection):
        result = search_memories("code", palace_path, wing="project", room="frontend")
        assert all(r["wing"] == "project" and r["room"] == "frontend" for r in result["results"])

    def test_n_results_limit(self, palace_path, seeded_collection):
        result = search_memories("code", palace_path, n_results=2)
        assert len(result["results"]) <= 2

    def test_no_palace_returns_error(self):
        result = search_memories("anything", "/nonexistent/path")
        assert "error" in result

    def test_result_fields(self, palace_path, seeded_collection):
        result = search_memories("authentication", palace_path)
        hit = result["results"][0]
        assert "text" in hit
        assert "wing" in hit
        assert "room" in hit
        assert "source_file" in hit
        assert "similarity" in hit
        assert isinstance(hit["similarity"], float)

    def test_search_uses_configured_collection_name_when_no_palace_override(self):
        tmpdir = tempfile.mkdtemp()
        palace_path = os.path.join(tmpdir, "palace")
        cfg_dir = os.path.join(tmpdir, "config")
        os.makedirs(cfg_dir)

        with open(os.path.join(cfg_dir, "config.json"), "w") as f:
            json.dump(
                {
                    "palace_path": palace_path,
                    "collection_name": "custom_drawers",
                },
                f,
            )

        client = chromadb.PersistentClient(path=palace_path)
        collection = client.get_or_create_collection("custom_drawers")
        collection.add(
            ids=["drawer_custom_backend_1"],
            documents=["JWT authentication lives in the custom collection."],
            metadatas=[
                {
                    "wing": "project",
                    "room": "backend",
                    "source_file": "auth.py",
                }
            ],
        )

        result = search_memories("JWT authentication", config=MempalaceConfig(config_dir=cfg_dir))
        assert len(result["results"]) == 1
        assert result["results"][0]["room"] == "backend"
