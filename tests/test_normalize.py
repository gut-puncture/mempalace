import json
import tempfile
from pathlib import Path

from mempalace.normalize import normalize


def write_temp_file(suffix: str, content: str) -> str:
    path = Path(tempfile.mkdtemp()) / f"sample{suffix}"
    path.write_text(content)
    return str(path)


def test_plain_text_passes_through():
    path = write_temp_file(".txt", "Hello world\nSecond line\n")

    result = normalize(path)

    assert result == "Hello world\nSecond line\n"


def test_claude_json_normalizes():
    path = Path(tempfile.mkdtemp()) / "claude.json"
    path.write_text(
        json.dumps(
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ]
        )
    )

    result = normalize(str(path))

    assert "> Hi" in result
    assert "Hello" in result


def test_chatgpt_export_array_normalizes_multiple_conversations():
    export = [
        {
            "mapping": {
                "root": {"id": "root", "parent": None, "message": None, "children": ["u1"]},
                "u1": {
                    "id": "u1",
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["First question"]},
                    },
                    "children": ["a1"],
                },
                "a1": {
                    "id": "a1",
                    "parent": "u1",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["First answer"]},
                    },
                    "children": [],
                },
            }
        },
        {"title": "broken entry"},
        {
            "mapping": {
                "root": {"id": "root", "parent": None, "message": None, "children": ["u2"]},
                "u2": {
                    "id": "u2",
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Second question"]},
                    },
                    "children": ["a2"],
                },
                "a2": {
                    "id": "a2",
                    "parent": "u2",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Second answer"]},
                    },
                    "children": [],
                },
            }
        },
    ]
    path = Path(tempfile.mkdtemp()) / "conversations.json"
    path.write_text(json.dumps(export))

    result = normalize(str(path))

    assert "> First question" in result
    assert "First answer" in result
    assert "> Second question" in result
    assert "Second answer" in result
    assert "\n---\n" in result


def test_normalize_preserves_user_typos_verbatim():
    path = Path(tempfile.mkdtemp()) / "chat.json"
    path.write_text(
        json.dumps(
            [
                {"role": "user", "content": "lsresdy knoe the question befor"},
                {"role": "assistant", "content": "I will keep it verbatim."},
            ]
        )
    )

    result = normalize(str(path))

    assert "> lsresdy knoe the question befor" in result


def test_empty_file_returns_empty_string():
    path = write_temp_file(".txt", "")

    result = normalize(path)

    assert result == ""
