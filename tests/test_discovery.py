import json

from fintrace.discovery import (
    discover_sources,
    parse_search_results,
    score_source_reliability,
    unwrap_search_url,
)


SEARCH_HTML = """
<html><body>
  <a class="result__a" href="/l/?kh=-1&uddg=https%3A%2F%2Fwww.dymonasia.com%2F">
    Dymon Asia Official Website
  </a>
  <a class="result__a" href="/l/?kh=-1&uddg=https%3A%2F%2Fwww.sec.gov%2FArchives%2Fedgar%2Fdata%2F1045810%2Ffiling.htm">
    SEC filing detail
  </a>
  <a class="result__a" href="https://reddit.com/r/funds/example">
    Reddit discussion
  </a>
</body></html>
"""


def test_unwrap_search_url_decodes_duckduckgo_redirect():
    assert (
        unwrap_search_url("/l/?kh=-1&uddg=https%3A%2F%2Fwww.sec.gov%2FArchives")
        == "https://www.sec.gov/Archives"
    )


def test_parse_search_results_extracts_candidate_links():
    results = parse_search_results(SEARCH_HTML, query="Dymon Asia AUM")

    assert [result.url for result in results][:2] == [
        "https://www.dymonasia.com/",
        "https://www.sec.gov/Archives/edgar/data/1045810/filing.htm",
    ]


def test_score_source_reliability_identifies_regulator_and_weak_sources():
    regulator = score_source_reliability(
        "https://www.sec.gov/Archives/edgar/data/1045810/filing.htm",
        title="SEC filing detail",
        subject="NVIDIA",
    )
    weak = score_source_reliability(
        "https://reddit.com/r/funds/example",
        title="Fund rumor discussion",
        subject="Dymon Asia",
    )

    assert regulator[0] >= 0.95
    assert regulator[1] == "regulator_or_exchange"
    assert weak[0] <= 0.4
    assert weak[1] == "weak_secondary"


def test_score_source_reliability_boosts_subject_matching_domain():
    score, category, reasons = score_source_reliability(
        "https://www.dymonasia.com/",
        title="Dymon Asia",
        subject="Dymon Asia",
    )

    assert score >= 0.9
    assert category == "official_or_primary"
    assert "domain strongly resembles subject" in reasons


def test_discover_sources_builds_scored_registry_from_search_html():
    result = discover_sources(
        "Track Dymon Asia AUM and regulatory risk",
        search_htmls=[SEARCH_HTML],
        max_results=3,
        max_queries=1,
    )

    sources = result.registry["sources"]
    assert any(
        source["url"] == "https://www.dymonasia.com/"
        and source["discovery"]["category"] == "official_or_primary"
        for source in sources
    )
    assert any(
        source["url"] == "https://www.sec.gov/Archives/edgar/data/1045810/filing.htm"
        and source["reliability"] >= 0.95
        for source in sources
    )
    assert result.registry["source_discovery"]["search_queries"]


def test_discovery_registry_is_json_serializable():
    result = discover_sources(
        "Track Dymon Asia AUM and regulatory risk",
        search_htmls=[SEARCH_HTML],
        max_results=2,
        max_queries=1,
    )

    assert json.loads(json.dumps(result.registry))["sources"]
