from fintrace.brief import create_brief_pack, infer_include_terms, infer_subject, infer_topic


def test_infer_subject_from_latin_entity():
    assert infer_subject("Track Dymon Asia recent fund performance and risk signals") == "Dymon Asia"


def test_infer_subject_from_chinese_brief():
    assert infer_subject("帮我跟踪机器人行业订单变化") == "机器人行业订单变化"


def test_infer_topic_for_asset_manager():
    assert infer_topic("Track Dymon Asia AUM and fund performance", "Dymon Asia") == "asset management"


def test_infer_include_terms_keeps_chinese_and_finance_terms():
    terms = infer_include_terms("跟踪机器人行业订单变化", subject="机器人行业", ticker=None)

    assert "机器人行业" in terms
    assert "announcement" in terms


def test_infer_include_terms_removes_stopwords():
    terms = infer_include_terms("Track Dymon Asia AUM and risk signals", subject="Dymon Asia", ticker=None)

    assert "and" not in terms
    assert "Track" not in terms


def test_infer_include_terms_extracts_clean_chinese_research_terms():
    terms = infer_include_terms(
        "帮我跟踪 Dymon Asia 的 AUM、基金表现、资金流入流出和监管风险，重点关注支持或削弱平台实力的证据",
        subject="Dymon Asia",
        ticker=None,
    )

    assert "基金表现" in terms
    assert "资金流入流出" in terms
    assert "监管风险" in terms
    assert "平台实力" in terms
    assert "帮我跟踪" not in terms
    assert "弱平台实力的证据" not in terms


def test_create_brief_pack_writes_workspace(tmp_path):
    pack = create_brief_pack(
        "Track Dymon Asia AUM, fund performance, and regulatory risk",
        out_dir=tmp_path,
        source_urls=["Official=https://example.com/rss.xml"],
    )

    assert pack.slug == "dymon-asia"
    assert (tmp_path / "dymon-asia.signal.json").exists()
    assert (tmp_path / "dymon-asia.sources.json").exists()
    assert (tmp_path / "dymon-asia.agent_brief.md").exists()
    assert pack.sources["sources"][0]["name"] == "Official"
