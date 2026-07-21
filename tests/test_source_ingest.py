from fintrace.schema import Signal, WatchItem
from fintrace.source_ingest import (
    Source,
    build_query_terms,
    ingest_sources,
    load_sources,
    parse_feed,
    score_relevance,
)


def test_parse_feed_returns_documents():
    source = Source(id="demo", name="Demo", url="memory://feed", reliability=0.8)
    xml = """
    <rss version="2.0">
      <channel>
        <item>
          <title>Revenue growth improved</title>
          <link>https://example.com/revenue</link>
          <description>Revenue growth accelerated as guidance increased.</description>
        </item>
      </channel>
    </rss>
    """

    documents = parse_feed(xml, source=source)

    assert len(documents) == 1
    assert documents[0].title == "Revenue growth improved"
    assert documents[0].url == "https://example.com/revenue"


def test_score_relevance_uses_signal_terms_and_source_terms():
    signal = Signal(
        title="NVDA AI Demand",
        hypothesis="AI infrastructure demand supports revenue growth",
        ticker="NVDA",
        watchlist=[WatchItem(metric="Data center revenue", why="Tracks demand")],
    )
    query_terms = build_query_terms(signal, query="cloud capex")
    source = Source(
        id="demo",
        name="Demo",
        url="memory://feed",
        reliability=0.9,
        include_terms=["capex"],
    )
    document = parse_feed(
        """
        <rss version="2.0"><channel><item>
          <title>Cloud capex remains strong for AI demand</title>
          <description>Data center revenue growth improved.</description>
        </item></channel></rss>
        """,
        source=source,
    )[0]

    assert score_relevance(document, source=source, query_terms=query_terms) >= 5


def test_ingest_sources_fetches_local_feed(tmp_path):
    feed = tmp_path / "feed.xml"
    feed.write_text(
        """
        <rss version="2.0"><channel><item>
          <title>Cloud capex remains strong for AI demand</title>
          <link>https://example.com/capex</link>
          <description>Revenue growth accelerated as cloud customers increased AI infrastructure capex.</description>
        </item></channel></rss>
        """,
        encoding="utf-8",
    )
    signal = Signal(
        title="NVDA AI Demand",
        hypothesis="AI infrastructure demand continues to support revenue growth",
        ticker="NVDA",
    )
    sources = [
        Source(
            id="demo",
            name="Demo Feed",
            url=str(feed),
            reliability=0.85,
            include_terms=["AI", "capex"],
        )
    ]

    items = ingest_sources(signal, sources, max_items=3)

    assert len(items) == 1
    assert items[0].source.name == "Demo Feed"
    assert items[0].document_url == "https://example.com/capex"
    assert items[0].adjusted_weight > 1.0


def test_load_sources_resolves_relative_paths(tmp_path):
    config = tmp_path / "sources.json"
    config.write_text(
        """
        {"sources": [{
          "id": "demo",
          "name": "Demo",
          "url": "feed.xml",
          "kind": "feed",
          "reliability": 0.8
        }]}
        """,
        encoding="utf-8",
    )

    sources = load_sources(config)

    assert sources[0].url == str(tmp_path / "feed.xml")
