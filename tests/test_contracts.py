import json
import subprocess
import sys

import yaml


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
    )

    assert "No sources configured" in result.stderr
    assert "No relevant evidence" in result.stdout
