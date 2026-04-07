import json
import tempfile
from pathlib import Path

import chromadb

from mempalace.convo_miner import mine_convos


def get_collection(palace_path: Path):
    client = chromadb.PersistentClient(path=str(palace_path))
    return client.get_collection("mempalace_drawers")


def test_convo_mining_refreshes_without_duplicates(capsys):
    tmpdir = Path(tempfile.mkdtemp())
    chat = tmpdir / "chat.txt"
    chat.write_text(
        "> What is memory?\nMemory is persistence.\n\n"
        "> Why does it matter?\nIt enables continuity.\n\n"
        "> How do we build it?\nWith structured storage.\n"
    )
    palace_path = tmpdir / "palace"

    mine_convos(str(tmpdir), str(palace_path), wing="test_convos")
    col = get_collection(palace_path)
    first_count = col.count()

    mine_convos(str(tmpdir), str(palace_path), wing="test_convos")
    output = capsys.readouterr().out

    assert first_count >= 2
    assert col.count() == first_count
    assert "Files unchanged: 1" in output


def test_same_convo_file_can_be_mined_in_exchange_and_general_modes():
    tmpdir = Path(tempfile.mkdtemp())
    chat = tmpdir / "chat.txt"
    chat.write_text(
        "> We should use Clerk because Auth0 is expensive.\n"
        "Agreed. Let's switch to Clerk.\n\n"
        "> The deploy bug is fixed now.\n"
        "Yes, the root cause was the token refresh path.\n\n"
        "> I prefer functional tests for auth flows.\n"
        "That preference makes sense.\n"
    )
    palace_path = tmpdir / "palace"

    mine_convos(str(tmpdir), str(palace_path), wing="test_convos", extract_mode="exchange")
    col = get_collection(palace_path)
    exchange_count = col.count()

    mine_convos(str(tmpdir), str(palace_path), wing="test_convos", extract_mode="general")
    results = col.get(where={"source_file": str(chat.resolve())}, include=["metadatas"])

    assert col.count() > exchange_count
    assert {meta["extract_mode"] for meta in results["metadatas"]} == {"exchange", "general"}


def test_chatgpt_export_exchange_mode_routes_each_conversation_separately():
    tmpdir = Path(tempfile.mkdtemp())
    export = [
        {
            "mapping": {
                "root": {"id": "root", "parent": None, "message": None, "children": ["u1"]},
                "u1": {
                    "id": "u1",
                    "parent": "root",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["The code bug is in the API layer."]}},
                    "children": ["a1"],
                },
                "a1": {
                    "id": "a1",
                    "parent": "u1",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["Let's debug the server and refactor it."]}},
                    "children": ["u2"],
                },
                "u2": {
                    "id": "u2",
                    "parent": "a1",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["The database error still blocks the deploy."]}},
                    "children": ["a2"],
                },
                "a2": {
                    "id": "a2",
                    "parent": "u2",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["We should test the fix once the server is stable."]}},
                    "children": ["u3"],
                },
                "u3": {
                    "id": "u3",
                    "parent": "a2",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["Please debug the failing function too."]}},
                    "children": ["a3"],
                },
                "a3": {
                    "id": "a3",
                    "parent": "u3",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["I will trace the code path."]}},
                    "children": [],
                },
            }
        },
        {
            "mapping": {
                "root": {"id": "root", "parent": None, "message": None, "children": ["p1"]},
                "p1": {
                    "id": "p1",
                    "parent": "root",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["We need a roadmap and milestone plan."]}},
                    "children": ["q1"],
                },
                "q1": {
                    "id": "q1",
                    "parent": "p1",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["Let's define the sprint scope and deadline."]}},
                    "children": ["p2"],
                },
                "p2": {
                    "id": "p2",
                    "parent": "q1",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["Set the backlog priority before the milestone review."]}},
                    "children": ["q2"],
                },
                "q2": {
                    "id": "q2",
                    "parent": "p2",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["The roadmap should stay in scope for this sprint."]}},
                    "children": ["p3"],
                },
                "p3": {
                    "id": "p3",
                    "parent": "q2",
                    "message": {"author": {"role": "user"}, "content": {"parts": ["Capture the requirement in the project plan."]}},
                    "children": ["q3"],
                },
                "q3": {
                    "id": "q3",
                    "parent": "p3",
                    "message": {"author": {"role": "assistant"}, "content": {"parts": ["I will update the roadmap."]}},
                    "children": [],
                },
            }
        },
    ]
    chat = tmpdir / "conversations.json"
    chat.write_text(json.dumps(export))
    palace_path = tmpdir / "palace"

    mine_convos(str(tmpdir), str(palace_path), wing="test_convos", extract_mode="exchange")
    col = get_collection(palace_path)
    results = col.get(where={"source_file": str(chat.resolve())}, include=["metadatas"])

    assert {meta["room"] for meta in results["metadatas"]} == {"technical", "planning"}
