from fintrace.schema import Signal, WatchItem
from fintrace.source_ingest import (
    Source,
    build_query_terms,
    discover_page_links,
    fetch_documents,
    ingest_sources,
    load_sources,
    parse_feed,
    parse_page,
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


def test_score_relevance_uses_cjk_query_terms():
    signal = Signal(title="阿里云需求", hypothesis="云收入增长")
    query_terms = build_query_terms(signal)
    source = Source(id="demo", name="Demo", url="memory://feed", reliability=0.8)
    document = parse_feed(
        """
        <rss version="2.0"><channel><item>
          <title>阿里云收入增长</title>
          <description>企业需求改善。</description>
        </item></channel></rss>
        """,
        source=source,
    )[0]

    assert "云收入增长" in query_terms
    assert score_relevance(document, source=source, query_terms=query_terms) >= 3


def test_score_relevance_uses_word_boundaries_for_latin_terms():
    source = Source(
        id="demo",
        name="Demo",
        url="memory://feed",
        reliability=0.8,
        include_terms=["risk"],
        exclude_terms=["ban"],
    )
    document = parse_feed(
        """
        <rss version="2.0"><channel><item>
          <title>Urbanization update</title>
          <description>Brisk sales improved.</description>
        </item></channel></rss>
        """,
        source=source,
    )[0]

    assert score_relevance(document, source=source, query_terms={"risk"}) == 2


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


def test_parse_page_filters_boilerplate_and_discovers_relevant_links(tmp_path):
    linked = tmp_path / "results.html"
    linked.write_text(
        """
        <html><head><title>Quarterly Results</title></head>
        <body><article><h1>Revenue growth improved</h1>
        <p>Revenue growth accelerated as guidance increased.</p></article></body></html>
        """,
        encoding="utf-8",
    )
    index = tmp_path / "index.html"
    index.write_text(
        """
        <html><head><title>Investor Relations</title></head>
        <body>
          <nav>Careers Contact Subscribe</nav>
          <main>
            <h1>Investor Relations</h1>
            <p>Data center demand remains a core investor topic.</p>
            <a href="results.html">Quarterly financial results</a>
          </main>
          <footer>Privacy Terms</footer>
        </body></html>
        """,
        encoding="utf-8",
    )
    source = Source(
        id="ir",
        name="IR",
        url=str(index),
        kind="page",
        reliability=0.9,
        include_terms=["revenue", "guidance", "results"],
    )

    documents = fetch_documents(source, limit=3, query_terms={"revenue", "guidance"})

    assert [document.title for document in documents] == ["Investor Relations", "Quarterly Results"]
    assert "Careers Contact Subscribe" not in documents[0].text
    assert "Revenue growth accelerated" in documents[1].text


def test_ingest_page_can_extract_from_discovered_link(tmp_path):
    linked = tmp_path / "earnings.html"
    linked.write_text(
        """
        <html><head><title>Earnings Release</title></head>
        <body><article><p>Revenue growth accelerated as AI demand improved.</p></article></body></html>
        """,
        encoding="utf-8",
    )
    index = tmp_path / "index.html"
    index.write_text(
        """
        <html><body>
          <p>Investor relations home.</p>
          <a href="earnings.html">Earnings release and financial results</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    signal = Signal(title="AI Demand", hypothesis="AI demand supports revenue growth")
    source = Source(
        id="ir",
        name="IR",
        url=str(index),
        kind="page",
        reliability=0.9,
        include_terms=["earnings", "revenue", "AI"],
    )

    items = ingest_sources(signal, [source], query="earnings revenue", max_items=3)

    assert any(item.document_title == "Earnings Release" for item in items)
    assert any("Revenue growth accelerated" in item.candidate.text for item in items)


def test_discover_page_links_rejects_cross_domain_and_assets():
    links = discover_page_links(
        [
            ("https://example.com/investors/results.html", "Financial results"),
            ("https://other.example.com/results.html", "Financial results"),
            ("https://example.com/logo.png", "Financial results image"),
        ],
        base_url="https://example.com/",
        terms={"results"},
        limit=5,
    )

    assert [link.url for link in links] == ["https://example.com/investors/results.html"]


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


def test_source_registry_accepts_custom_language_terms():
    source = Source.from_dict(
        {
            "id": "zh",
            "name": "Chinese Source",
            "url": "feed.xml",
            "support_terms": ["续约率改善"],
            "counter_terms": ["坏账上升"],
            "finance_terms": ["客户"],
        }
    )

    assert source.support_terms == ["续约率改善"]
    assert source.counter_terms == ["坏账上升"]
    assert source.finance_terms == ["客户"]


def test_ingest_sources_skips_bad_sources_with_warning(tmp_path):
    signal = Signal(title="Test", hypothesis="Revenue demand is improving")
    sources = [
        Source(id="bad", name="Bad Source", url=str(tmp_path / "missing.xml")),
    ]
    warnings: list[str] = []

    items = ingest_sources(signal, sources, warnings=warnings)

    assert items == []
    assert len(warnings) == 1
    assert "Bad Source" in warnings[0]
