"""Contract tests for self-assessed Gold quality requirements."""

from pathlib import Path

import yaml

from custom_components.beatbot import binary_sensor, select, sensor, switch, vacuum

SILVER_RULES = {
    "action-exceptions",
    "config-entry-unloading",
    "docs-configuration-parameters",
    "docs-installation-parameters",
    "entity-unavailable",
    "integration-owner",
    "log-when-unavailable",
    "parallel-updates",
    "reauthentication-flow",
    "test-coverage",
}

GOLD_RULES = {
    "devices",
    "diagnostics",
    "discovery-update-info",
    "discovery",
    "docs-data-update",
    "docs-examples",
    "docs-known-limitations",
    "docs-supported-devices",
    "docs-supported-functions",
    "docs-troubleshooting",
    "docs-use-cases",
    "dynamic-devices",
    "entity-category",
    "entity-device-class",
    "entity-disabled-by-default",
    "entity-translations",
    "exception-translations",
    "icon-translations",
    "reconfiguration-flow",
    "repair-issues",
    "stale-devices",
}


def test_platforms_declare_parallel_update_limits() -> None:
    """Every entity platform must explicitly choose its concurrency limit."""
    assert binary_sensor.PARALLEL_UPDATES == 0
    assert sensor.PARALLEL_UPDATES == 0
    assert select.PARALLEL_UPDATES == 1
    assert switch.PARALLEL_UPDATES == 1
    assert vacuum.PARALLEL_UPDATES == 1


def test_quality_scale_declares_every_silver_rule_done() -> None:
    """The self-assessed Silver claim must have no missing or pending rule."""
    quality_scale = yaml.safe_load(
        Path("custom_components/beatbot/quality_scale.yaml").read_text(encoding="utf-8")
    )["rules"]

    assert SILVER_RULES <= quality_scale.keys()
    for rule in SILVER_RULES:
        value = quality_scale[rule]
        status = value if isinstance(value, str) else value["status"]
        assert status in {"done", "exempt"}, rule


def test_quality_scale_declares_every_gold_rule_complete() -> None:
    """The self-assessed Gold claim must have no missing or pending rule."""
    quality_scale = yaml.safe_load(
        Path("custom_components/beatbot/quality_scale.yaml").read_text(encoding="utf-8")
    )["rules"]

    assert GOLD_RULES <= quality_scale.keys()
    for rule in GOLD_RULES:
        value = quality_scale[rule]
        status = value if isinstance(value, str) else value["status"]
        assert status in {"done", "exempt"}, rule
