from __future__ import annotations

import argparse
from pathlib import Path

from fintrace.agent_import import import_agent_evidence, load_agent_evidence
from fintrace.brief import create_brief_pack
from fintrace.extractor import extract_evidence_candidates, read_source_text
from fintrace.ledger import (
    add_evidence,
    load_signal,
    record_evaluation,
    render_html_graph,
    render_markdown,
    save_signal,
)
from fintrace.schema import EvidenceKind, Signal, WatchItem
from fintrace.source_ingest import ingest_sources, load_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fintrace",
        description="Build auditable financial signal cards with evidence ledgers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new signal card JSON file.")
    init_parser.add_argument("path", help="Where to write the signal card.")
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--hypothesis", required=True)
    init_parser.add_argument("--topic")
    init_parser.add_argument("--ticker")
    init_parser.set_defaults(func=cmd_init)

    add_parser = subparsers.add_parser("add-evidence", help="Append evidence to a signal card.")
    add_parser.add_argument("path")
    add_parser.add_argument("--kind", choices=[item.value for item in EvidenceKind], default=EvidenceKind.SUPPORT.value)
    add_parser.add_argument("--source", required=True)
    add_parser.add_argument("--text", required=True)
    add_parser.add_argument("--url")
    add_parser.add_argument("--observed-at")
    add_parser.add_argument("--weight", type=float, default=1.0)
    add_parser.set_defaults(func=cmd_add_evidence)

    watch_parser = subparsers.add_parser("add-watch", help="Append a watchlist metric to a signal card.")
    watch_parser.add_argument("path")
    watch_parser.add_argument("--metric", required=True)
    watch_parser.add_argument("--why", required=True)
    watch_parser.add_argument("--source-hint")
    watch_parser.set_defaults(func=cmd_add_watch)

    status_parser = subparsers.add_parser("status", help="Evaluate and record the current signal status.")
    status_parser.add_argument("path")
    status_parser.set_defaults(func=cmd_status)

    report_parser = subparsers.add_parser("report", help="Render a Markdown signal report.")
    report_parser.add_argument("path")
    report_parser.add_argument("--out", required=True)
    report_parser.set_defaults(func=cmd_report)

    graph_parser = subparsers.add_parser("graph", help="Render a standalone HTML evidence graph.")
    graph_parser.add_argument("path")
    graph_parser.add_argument("--out", required=True)
    graph_parser.set_defaults(func=cmd_graph)

    extract_parser = subparsers.add_parser("extract", help="Extract evidence candidates from text, a file, or a URL.")
    extract_parser.add_argument("path")
    source_group = extract_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--text")
    source_group.add_argument("--file")
    source_group.add_argument("--url")
    extract_parser.add_argument("--source", required=True)
    extract_parser.add_argument("--max-items", type=int, default=8)
    extract_parser.add_argument("--min-score", type=int, default=1)
    extract_parser.add_argument("--support-term", action="append", default=[], help="Extra support evidence term. Can be repeated.")
    extract_parser.add_argument("--counter-term", action="append", default=[], help="Extra counter evidence term. Can be repeated.")
    extract_parser.add_argument("--finance-term", action="append", default=[], help="Extra finance/domain term. Can be repeated.")
    extract_parser.add_argument("--apply", action="store_true", help="Append extracted candidates to the signal card.")
    extract_parser.set_defaults(func=cmd_extract)

    ingest_parser = subparsers.add_parser("ingest", help="Fetch configured sources and extract relevant evidence.")
    ingest_parser.add_argument("path")
    ingest_parser.add_argument("--sources", required=True, help="JSON source registry path.")
    ingest_parser.add_argument("--query", help="Extra topic, company, ticker, or keyword filter.")
    ingest_parser.add_argument("--max-items", type=int, default=12)
    ingest_parser.add_argument("--per-source-limit", type=int, default=8)
    ingest_parser.add_argument("--min-score", type=int, default=1)
    ingest_parser.add_argument("--apply", action="store_true", help="Append ingested evidence to the signal card.")
    ingest_parser.set_defaults(func=cmd_ingest)

    brief_parser = subparsers.add_parser("from-brief", help="Create a signal workspace from a natural-language user brief.")
    brief_parser.add_argument("brief", help="User request or research brief.")
    brief_parser.add_argument("--out-dir", required=True)
    brief_parser.add_argument("--slug")
    brief_parser.add_argument("--title")
    brief_parser.add_argument("--topic")
    brief_parser.add_argument("--ticker")
    brief_parser.add_argument(
        "--source-url",
        action="append",
        default=[],
        help="Optional source URL, or NAME=URL. Can be repeated.",
    )
    brief_parser.set_defaults(func=cmd_from_brief)

    import_parser = subparsers.add_parser("import-evidence", help="Import structured evidence produced by an agent or LLM.")
    import_parser.add_argument("path")
    import_parser.add_argument("--file", required=True, help="Evidence JSON file.")
    import_parser.add_argument("--default-source")
    import_parser.add_argument("--dry-run", action="store_true", help="Preview import without changing the signal card.")
    import_parser.add_argument("--allow-duplicates", action="store_true", help="Import duplicate evidence items.")
    import_parser.add_argument("--evaluate", action="store_true", help="Evaluate signal status after import.")
    import_parser.set_defaults(func=cmd_import_evidence)

    demo_parser = subparsers.add_parser("demo", help="Create a runnable NVDA demo signal.")
    demo_parser.add_argument("--out-dir", default=".")
    demo_parser.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


def cmd_init(args: argparse.Namespace) -> None:
    signal = Signal(
        title=args.title,
        hypothesis=args.hypothesis,
        topic=args.topic,
        ticker=args.ticker,
    )
    save_signal(signal, args.path)
    print(f"Created signal card: {args.path}")


def cmd_add_evidence(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    evidence = add_evidence(
        signal,
        text=args.text,
        source=args.source,
        kind=EvidenceKind(args.kind),
        url=args.url,
        observed_at=args.observed_at,
        weight=args.weight,
    )
    save_signal(signal, args.path)
    print(f"Added {evidence.kind.value} evidence {evidence.id} to {args.path}")


def cmd_add_watch(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    signal.watchlist.append(
        WatchItem(metric=args.metric, why=args.why, source_hint=args.source_hint)
    )
    save_signal(signal, args.path)
    print(f"Added watch item to {args.path}: {args.metric}")


def cmd_status(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    event = record_evaluation(signal)
    save_signal(signal, args.path)
    print(f"Signal: {signal.title}")
    print(f"Previous: {event.previous_status.value}")
    print(f"Current: {event.current_status.value}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Why: {event.summary}")


def cmd_report(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    Path(args.out).write_text(render_markdown(signal), encoding="utf-8")
    print(f"Wrote report: {args.out}")


def cmd_graph(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    Path(args.out).write_text(render_html_graph(signal), encoding="utf-8")
    print(f"Wrote evidence graph: {args.out}")


def cmd_extract(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    text = read_source_text(text=args.text, file=args.file, url=args.url)
    candidates = extract_evidence_candidates(
        text,
        max_items=args.max_items,
        min_score=args.min_score,
        support_terms=args.support_term,
        counter_terms=args.counter_term,
        finance_terms=args.finance_term,
    )

    if not candidates:
        print("No evidence candidates found.")
        return

    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}] {candidate.kind.value} | weight {candidate.weight:.1f} | score {candidate.score}")
        print(candidate.text)
        print()

    if args.apply:
        for candidate in candidates:
            add_evidence(
                signal,
                text=candidate.text,
                source=args.source,
                kind=candidate.kind,
                url=args.url,
                observed_at=None,
                weight=candidate.weight,
            )
        save_signal(signal, args.path)
        print(f"Applied {len(candidates)} evidence candidates to {args.path}")


def cmd_ingest(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    sources = load_sources(args.sources)
    items = ingest_sources(
        signal,
        sources,
        query=args.query,
        max_items=args.max_items,
        per_source_limit=args.per_source_limit,
        min_score=args.min_score,
    )

    if not items:
        print("No relevant evidence found from configured sources.")
        return

    for index, item in enumerate(items, start=1):
        candidate = item.candidate
        print(
            f"[{index}] {candidate.kind.value} | weight {item.adjusted_weight:.1f} "
            f"| relevance {item.relevance_score} | source {item.source.name} ({item.source.reliability:.2f})"
        )
        print(f"Document: {item.document_title}")
        if item.document_url:
            print(f"URL: {item.document_url}")
        print(candidate.text)
        print()

    if args.apply:
        for item in items:
            add_evidence(
                signal,
                text=item.candidate.text,
                source=f"{item.source.name}: {item.document_title}",
                kind=item.candidate.kind,
                url=item.document_url,
                observed_at=None,
                weight=item.adjusted_weight,
            )
        save_signal(signal, args.path)
        print(f"Applied {len(items)} ingested evidence items to {args.path}")


def cmd_from_brief(args: argparse.Namespace) -> None:
    pack = create_brief_pack(
        args.brief,
        out_dir=args.out_dir,
        slug=args.slug,
        title=args.title,
        topic=args.topic,
        ticker=args.ticker,
        source_urls=args.source_url,
    )
    target_dir = Path(args.out_dir)
    print(f"Created signal workspace: {target_dir}")
    print(f"Signal: {target_dir / f'{pack.slug}.signal.json'}")
    print(f"Sources: {target_dir / f'{pack.slug}.sources.json'}")
    print(f"Agent brief: {target_dir / f'{pack.slug}.agent_brief.md'}")
    print(f"Include terms: {', '.join(pack.include_terms[:12])}")


def cmd_import_evidence(args: argparse.Namespace) -> None:
    signal = load_signal(args.path)
    raw_items = load_agent_evidence(args.file)
    result = import_agent_evidence(
        signal,
        raw_items,
        default_source=args.default_source,
        dedupe=not args.allow_duplicates,
        evaluate=args.evaluate and not args.dry_run,
    )
    for index, evidence in enumerate(result.evidence, start=1):
        print(f"[{index}] {evidence.kind.value} | weight {evidence.weight:.1f} | source {evidence.source}")
        print(evidence.text)
        if evidence.reason:
            print(f"Reason: {evidence.reason}")
        if evidence.url:
            print(f"URL: {evidence.url}")
        print()
    if args.dry_run:
        print(f"Dry run: {len(result.evidence)} evidence items would be imported into {args.path}")
        return
    save_signal(signal, args.path)
    print(f"Imported {len(result.evidence)} evidence items into {args.path}")
    if result.update_event:
        print(
            f"Evaluated: {result.update_event.previous_status.value} -> "
            f"{result.update_event.current_status.value}"
        )
        print(f"Why: {result.update_event.summary}")


def cmd_demo(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    signal_path = out_dir / "nvda_ai_demand.signal.json"
    report_path = out_dir / "nvda_ai_demand.report.md"
    graph_path = out_dir / "nvda_ai_demand.graph.html"

    signal = Signal(
        title="NVDA AI Demand",
        hypothesis="AI infrastructure demand continues to support NVDA data center revenue growth.",
        topic="AI infrastructure",
        ticker="NVDA",
        watchlist=[
            WatchItem(
                metric="Data center revenue growth",
                why="Confirms whether AI accelerator demand is still translating into reported revenue",
                source_hint="Quarterly earnings release",
            ),
            WatchItem(
                metric="Hyperscaler capex guidance",
                why="Tests whether major customers are still expanding AI infrastructure budgets",
                source_hint="Earnings calls from MSFT, AMZN, GOOGL, META",
            ),
        ],
    )
    add_evidence(
        signal,
        text="Management commentary indicates continued demand for accelerated computing capacity.",
        source="Example earnings call note",
        kind=EvidenceKind.SUPPORT,
        url=None,
        observed_at="2026-07-21",
        weight=1.2,
    )
    add_evidence(
        signal,
        text="Export restrictions remain a potential headwind for China-related revenue.",
        source="Example regulatory risk note",
        kind=EvidenceKind.COUNTER,
        url=None,
        observed_at="2026-07-21",
        weight=0.7,
    )
    add_evidence(
        signal,
        text="Cloud capex plans from major customers remain elevated.",
        source="Example peer capex tracker",
        kind=EvidenceKind.SUPPORT,
        url=None,
        observed_at="2026-07-21",
        weight=1.1,
    )
    record_evaluation(signal)
    save_signal(signal, signal_path)
    report_path.write_text(render_markdown(signal), encoding="utf-8")
    graph_path.write_text(render_html_graph(signal), encoding="utf-8")
    print(f"Wrote demo signal: {signal_path}")
    print(f"Wrote demo report: {report_path}")
    print(f"Wrote demo graph: {graph_path}")


if __name__ == "__main__":
    raise SystemExit(main())
