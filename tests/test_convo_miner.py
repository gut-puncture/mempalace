import hashlib
import shutil
import tempfile
from pathlib import Path

import chromadb

from mempalace.convo_miner import mine_convos


def get_collection(palace_path: Path):
    client = chromadb.PersistentClient(path=str(palace_path))
    return client.get_collection("mempalace_drawers")


def get_source_rows(col, source_file: Path, wing: str):
    results = col.get(
        where={"$and": [{"source_file": str(source_file.resolve())}, {"wing": wing}]},
        include=["documents", "metadatas"],
    )
    return list(zip(results["ids"], results["documents"], results["metadatas"]))


def test_convo_mining_refreshes_without_duplicates(capsys):
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> What is memory?\nMemory is persistence.\n\n"
            "> Why does it matter?\nIt enables continuity.\n\n"
            "> How do we build it?\nWith structured storage.\n",
            encoding="utf-8",
        )

        palace_path = convo_root / "palace"
        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        col = get_collection(palace_path)
        first_rows = get_source_rows(col, source, "test_convos")
        assert first_rows
        assert all(meta["ingest_mode"] == "convos" for _, _, meta in first_rows)
        assert all(meta["extract_mode"] == "exchange" for _, _, meta in first_rows)
        assert all(meta["refresh_owner"] == "convos:exchange" for _, _, meta in first_rows)

        capsys.readouterr()
        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        output = capsys.readouterr().out
        second_rows = get_source_rows(col, source, "test_convos")

        assert "Files unchanged: 1" in output
        assert {row[0] for row in first_rows} == {row[0] for row in second_rows}
    finally:
        shutil.rmtree(tmpdir)


def test_convo_mining_updates_changed_content(capsys):
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> Why switch auth?\nBecause Auth0 is expensive.\n\n"
            "> What next?\nWe should move to Clerk.\n",
            encoding="utf-8",
        )
        palace_path = convo_root / "palace"

        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        col = get_collection(palace_path)
        first_rows = get_source_rows(col, source, "test_convos")

        source.write_text(
            "> Why switch auth?\nBecause the token refresh path is broken.\n\n"
            "> What next?\nWe should fix the oauth flow first.\n",
            encoding="utf-8",
        )
        capsys.readouterr()
        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        output = capsys.readouterr().out
        updated_rows = get_source_rows(col, source, "test_convos")

        assert "Files updated: 1" in output
        assert {row[0] for row in first_rows} != {row[0] for row in updated_rows}
        assert any("oauth flow" in doc for _, doc, _ in updated_rows)
    finally:
        shutil.rmtree(tmpdir)


def test_same_convo_file_can_be_mined_in_exchange_and_general_modes():
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> We should use Clerk because Auth0 is expensive.\n"
            "Agreed. Let's switch to Clerk.\n\n"
            "> The deploy bug is fixed now.\n"
            "Yes, the root cause was the token refresh path.\n\n"
            "> I prefer functional tests for auth flows.\n"
            "That preference makes sense.\n",
            encoding="utf-8",
        )
        palace_path = convo_root / "palace"

        mine_convos(str(convo_root), str(palace_path), wing="test_convos", extract_mode="exchange")
        mine_convos(str(convo_root), str(palace_path), wing="test_convos", extract_mode="general")
        col = get_collection(palace_path)
        rows = get_source_rows(col, source, "test_convos")

        assert {meta["extract_mode"] for _, _, meta in rows} == {"exchange", "general"}
    finally:
        shutil.rmtree(tmpdir)


def test_same_convo_file_can_be_mined_into_two_wings():
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> What is memory?\nMemory is persistence.\n\n"
            "> Why does it matter?\nIt enables continuity.\n",
            encoding="utf-8",
        )
        palace_path = convo_root / "palace"

        mine_convos(str(convo_root), str(palace_path), wing="alpha")
        mine_convos(str(convo_root), str(palace_path), wing="beta")
        col = get_collection(palace_path)
        results = col.get(where={"source_file": str(source.resolve())}, include=["metadatas"])

        assert {meta["wing"] for meta in results["metadatas"]} == {"alpha", "beta"}
    finally:
        shutil.rmtree(tmpdir)


def test_convo_refresh_clears_empty_content_for_only_that_namespace(capsys):
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> We should use Clerk because Auth0 is expensive.\n"
            "Agreed. Let's switch to Clerk.\n\n"
            "> The deploy bug is fixed now.\n"
            "Yes, the root cause was the token refresh path.\n\n"
            "> I prefer functional tests for auth flows.\n"
            "That preference makes sense.\n",
            encoding="utf-8",
        )
        palace_path = convo_root / "palace"

        mine_convos(str(convo_root), str(palace_path), wing="test_convos", extract_mode="exchange")
        mine_convos(str(convo_root), str(palace_path), wing="test_convos", extract_mode="general")
        col = get_collection(palace_path)

        source.write_text("", encoding="utf-8")
        capsys.readouterr()
        mine_convos(str(convo_root), str(palace_path), wing="test_convos", extract_mode="exchange")
        output = capsys.readouterr().out

        rows = get_source_rows(col, source, "test_convos")
        assert "Files cleared: 1" in output
        assert {meta["extract_mode"] for _, _, meta in rows} == {"general"}
    finally:
        shutil.rmtree(tmpdir)


def test_convo_refresh_preserves_old_drawers_on_normalize_error(monkeypatch, capsys):
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        source.write_text(
            "> What is memory?\nMemory is persistence.\n\n"
            "> Why does it matter?\nIt enables continuity.\n",
            encoding="utf-8",
        )
        palace_path = convo_root / "palace"

        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        col = get_collection(palace_path)
        first_rows = get_source_rows(col, source, "test_convos")

        from mempalace import convo_miner
        original_normalize = convo_miner.normalize

        def broken_normalize(filepath: str) -> str:
            if filepath == str(source.resolve()):
                raise ValueError("bad export")
            return original_normalize(filepath)

        monkeypatch.setattr(convo_miner, "normalize", broken_normalize)
        capsys.readouterr()
        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        output = capsys.readouterr().out

        assert "Files errored: 1" in output
        assert {row[0] for row in get_source_rows(col, source, "test_convos")} == {
            row[0] for row in first_rows
        }
    finally:
        shutil.rmtree(tmpdir)


def test_legacy_convo_rows_are_upgraded_on_first_refresh():
    tmpdir = tempfile.mkdtemp()
    try:
        convo_root = Path(tmpdir).resolve()
        source = convo_root / "chat.txt"
        content = (
            "> What is memory?\nMemory is persistence.\n\n"
            "> Why does it matter?\nIt enables continuity.\n\n"
            "> How do we build it?\nWith structured storage.\n"
        )
        source.write_text(content, encoding="utf-8")
        palace_path = convo_root / "palace"

        from mempalace.convo_miner import chunk_exchanges, detect_convo_room

        client = chromadb.PersistentClient(path=str(palace_path))
        col = client.get_or_create_collection("mempalace_drawers")
        room = detect_convo_room(content)
        chunks = chunk_exchanges(content)
        col.upsert(
            ids=[
                f"drawer_test_convos_{room}_{hashlib.md5((str(source.resolve()) + str(chunk['chunk_index'])).encode(), usedforsecurity=False).hexdigest()[:16]}"
                for chunk in chunks
            ],
            documents=[chunk["content"] for chunk in chunks],
            metadatas=[
                {
                    "wing": "test_convos",
                    "room": room,
                    "source_file": str(source.resolve()),
                    "chunk_index": chunk["chunk_index"],
                    "added_by": "legacy",
                    "filed_at": "2026-01-01T00:00:00",
                    "ingest_mode": "convos",
                    "extract_mode": "exchange",
                }
                for chunk in chunks
            ],
        )

        mine_convos(str(convo_root), str(palace_path), wing="test_convos")
        rows = get_source_rows(col, source, "test_convos")

        assert rows
        assert all(meta["ingest_mode"] == "convos" for _, _, meta in rows)
        assert all(meta["extract_mode"] == "exchange" for _, _, meta in rows)
        assert all(meta["refresh_owner"] == "convos:exchange" for _, _, meta in rows)
        assert all(meta["source_signature"] for _, _, meta in rows)
        assert all(meta["pipeline_fingerprint"] for _, _, meta in rows)
    finally:
        shutil.rmtree(tmpdir)
