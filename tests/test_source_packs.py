import json
import subprocess
import sys

import pytest

from fintrace.source_packs import get_source_pack, list_source_packs, render_source_pack, write_source_pack


def test_list_source_packs_contains_core_packs():
    ids = {pack.id for pack in list_source_packs()}

    assert {"sec-us", "hkex", "nvda", "dymon-asia", "fund-manager"}.issubset(ids)


def test_render_sec_source_pack_requires_cik():
    with pytest.raises(ValueError, match="requires"):
        render_source_pack("sec-us", ticker="NVDA")


def test_render_sec_source_pack_substitutes_ticker_and_cik():
    registry = render_source_pack("sec-us", ticker="NVDA", cik="1045810")
    source = registry["sources"][0]

    assert source["id"] == "sec-edgar-nvda"
    assert "CIK=1045810" in source["url"]
    assert "NVDA" in source["include_terms"]


def test_render_dymon_source_pack_has_agent_instructions():
    registry = render_source_pack("dymon-asia")

    assert registry["sources"][0]["url"] == "https://www.dymonasia.com/"
    assert registry["agent_instructions"]


def test_write_source_pack_round_trips(tmp_path):
    path = tmp_path / "sources.json"
    registry = render_source_pack("nvda")

    write_source_pack(path, registry)

    assert json.loads(path.read_text(encoding="utf-8"))["sources"][0]["id"] == "nvidia-ir-rss"


def test_get_source_pack_rejects_unknown_pack():
    with pytest.raises(ValueError, match="Unknown source pack"):
        get_source_pack("missing")


def test_source_pack_cli_create(tmp_path):
    out = tmp_path / "sources.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fintrace.cli",
            "source-pack",
            "create",
            "sec-us",
            "--ticker",
            "NVDA",
            "--cik",
            "1045810",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote source pack 'sec-us'" in result.stdout
    assert "CIK=1045810" in out.read_text(encoding="utf-8")
