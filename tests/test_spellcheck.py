import json
from pathlib import Path

from mempalace.spellcheck import _load_known_names, spellcheck_user_text


def test_load_known_names_reads_people_and_aliases():
    registry_path = Path.home() / ".mempalace" / "entity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "personal",
                "people": {
                    "Maxwell": {
                        "source": "onboarding",
                        "contexts": ["personal"],
                        "aliases": ["Max"],
                        "confidence": 1.0,
                    },
                    "Max": {
                        "source": "onboarding",
                        "contexts": ["personal"],
                        "aliases": ["Maxwell"],
                        "canonical": "Maxwell",
                        "confidence": 1.0,
                    },
                },
                "projects": [],
                "ambiguous_flags": [],
                "wiki_cache": {},
            }
        )
    )

    known_names = _load_known_names()

    assert {"max", "maxwell"} <= known_names


def test_spellcheck_helper_preserves_registered_names_and_aliases(monkeypatch):
    registry_path = Path.home() / ".mempalace" / "entity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "personal",
                "people": {
                    "Sam": {
                        "source": "onboarding",
                        "contexts": ["personal"],
                        "aliases": ["Sammie"],
                        "confidence": 1.0,
                    }
                },
                "projects": [],
                "ambiguous_flags": [],
                "wiki_cache": {},
            }
        )
    )

    class AggressiveSpeller:
        def __call__(self, token):
            replacements = {"sammie": "sammy", "functionalityy": "functionality"}
            return replacements.get(token.lower(), token)

    monkeypatch.setattr("mempalace.spellcheck._get_speller", lambda: AggressiveSpeller())

    corrected = spellcheck_user_text("Sammie fixed functionalityy")

    assert corrected == "Sammie fixed functionality"
