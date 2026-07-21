import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    return env


def test_agent_evidence_schema_and_example_are_aligned():
    schema = json.loads(open("schemas/agent_evidence.schema.json", encoding="utf-8").read())
    example = json.loads(open("examples/agent_evidence.example.json", encoding="utf-8").read())
    required = set(schema["$defs"]["evidence_item"]["required"])
    allowed = set(schema["$defs"]["evidence_item"]["properties"])

    assert required == {"kind", "text", "source"}
    for item in example["evidence"]:
        assert required.issubset(item)
        assert set(item).issubset(allowed)
        assert item["kind"] in {"support", "counter", "neutral"}
        assert 0 <= item.get("weight", 1.0) <= 2


def test_skill_metadata_and_references_exist():
    skill = open("skills/fintrace/SKILL.md", encoding="utf-8").read()
    metadata = yaml.safe_load(skill.split("---", 2)[1])

    assert metadata["name"] == "fintrace"
    assert "evidence" in metadata["description"].lower()
    assert "references/agent-evidence-contract.md" in skill
    assert "references/adversarial-checklist.md" in skill
    assert open("skills/fintrace/agents/openai.yaml", encoding="utf-8").read()


def test_import_evidence_dry_run_does_not_write_signal(tmp_path):
    signal = tmp_path / "signal.json"
    evidence = tmp_path / "evidence.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "init",
            str(signal),
            "--title",
            "Dry Run Signal",
            "--hypothesis",
            "Demand is improving",
        ],
        check=True,
        env=_cli_env(),
    )
    before = signal.read_text(encoding="utf-8")
    evidence.write_text(
        json.dumps(
            {
                "evidence": [
                    {
                        "kind": "support",
                        "text": "Revenue growth accelerated.",
                        "source": "Agent source",
                        "weight": 1.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "import-evidence",
            str(signal),
            "--file",
            str(evidence),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert "Dry run" in result.stdout
    assert signal.read_text(encoding="utf-8") == before


def test_ingest_empty_source_registry_warns(tmp_path):
    signal = tmp_path / "signal.json"
    sources = tmp_path / "sources.json"
    sources.write_text('{"sources": []}', encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "init",
            str(signal),
            "--title",
            "Empty Sources",
            "--hypothesis",
            "Demand is improving",
        ],
        check=True,
        env=_cli_env(),
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "ingest",
            str(signal),
            "--sources",
            str(sources),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert "No sources configured" in result.stderr
    assert "No relevant evidence" in result.stdout


def test_source_plan_cli_writes_agent_plan(tmp_path):
    out = tmp_path / "source_plan.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "source-plan",
            "Track Dymon Asia AUM and regulatory risk",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert "Wrote source plan" in result.stdout
    assert "Search Queries" in out.read_text(encoding="utf-8")
