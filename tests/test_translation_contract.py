"""Translation contract tests that run with only the Python standard library."""

from __future__ import annotations

import json
from pathlib import Path

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "beatbot"
ERROR_PLACEHOLDER = "{" + "error" + "}"


def _load_json(path: Path) -> dict:
    """Load a JSON object from an integration resource."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_oauth_rejection_translations_include_error_placeholder() -> None:
    """Render the OAuth provider error in source and English strings."""
    resources = (
        INTEGRATION_DIR / "strings.json",
        INTEGRATION_DIR / "translations" / "en.json",
    )

    for resource in resources:
        message = _load_json(resource)["config"]["abort"]["user_rejected_authorize"]
        assert ERROR_PLACEHOLDER in message


def test_all_locales_include_translated_action_exceptions() -> None:
    """Keep action-error keys and placeholders complete in every locale."""
    expected_keys = set(_load_json(INTEGRATION_DIR / "strings.json")["exceptions"])

    for resource in (INTEGRATION_DIR / "translations").glob("*.json"):
        exceptions = _load_json(resource)["exceptions"]
        assert set(exceptions) == expected_keys
        assert "{device}" in exceptions["control_authentication_error"]["message"]
        assert "{option}" in exceptions["invalid_work_mode"]["message"]


if __name__ == "__main__":
    test_oauth_rejection_translations_include_error_placeholder()
    test_all_locales_include_translated_action_exceptions()
