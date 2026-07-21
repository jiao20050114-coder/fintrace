from __future__ import annotations

import json
from html import escape
from datetime import datetime, timezone
from pathlib import Path

from fintrace.schema import Evidence, EvidenceKind, Signal, SignalStatus, UpdateEvent


def load_signal(path: str | Path) -> Signal:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Signal.from_dict(data)


def save_signal(signal: Signal, path: str | Path) -> None:
    signal.updated_at = datetime.now(timezone.utc).isoformat()
    Path(path).write_text(
        json.dumps(signal.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def evaluate_signal(signal: Signal) -> tuple[SignalStatus, float, str]:
    support_score = sum(item.weight for item in signal.evidence if item.kind == EvidenceKind.SUPPORT)
    counter_score = sum(item.weight for item in signal.evidence if item.kind == EvidenceKind.COUNTER)
    neutral_count = sum(1 for item in signal.evidence if item.kind == EvidenceKind.NEUTRAL)
    total_score = support_score + counter_score

    if total_score == 0:
        return SignalStatus.DRAFT, 0.0, "No evidence has been recorded yet."

    net = support_score - counter_score
    confidence = max(0.05, min(0.95, 0.5 + (net / (2 * total_score))))

    if counter_score >= 2.0 and counter_score >= support_score + 1.0:
        status = SignalStatus.FALSIFIED
    elif counter_score >= 1.0 and counter_score >= support_score * 1.25:
        status = SignalStatus.WEAKENED
    elif support_score >= 2.0 and support_score >= counter_score * 1.5:
        status = SignalStatus.STRENGTHENED
    else:
        status = SignalStatus.ACTIVE

    summary = (
        f"Support score {support_score:.1f}, counter score {counter_score:.1f}, "
        f"neutral evidence {neutral_count}. Net evidence points to '{status.value}'."
    )
    return status, confidence, summary


def record_evaluation(signal: Signal) -> UpdateEvent:
    previous = signal.status
    status, confidence, summary = evaluate_signal(signal)
    signal.status = status
    signal.confidence = confidence
    event = UpdateEvent(previous_status=previous, current_status=status, summary=summary)
    signal.updates.append(event)
    return event


def add_evidence(
    signal: Signal,
    *,
    text: str,
    source: str,
    kind: EvidenceKind,
    url: str | None,
    observed_at: str | None,
    weight: float,
    reason: str | None = None,
) -> Evidence:
    evidence = Evidence(
        text=text,
        source=source,
        kind=kind,
        url=url,
        reason=reason,
        observed_at=observed_at or datetime.now(timezone.utc).date().isoformat(),
        weight=weight,
    )
    signal.evidence.append(evidence)
    return evidence


def render_markdown(signal: Signal) -> str:
    supporting = [item for item in signal.evidence if item.kind == EvidenceKind.SUPPORT]
    counter = [item for item in signal.evidence if item.kind == EvidenceKind.COUNTER]
    neutral = [item for item in signal.evidence if item.kind == EvidenceKind.NEUTRAL]

    lines = [
        f"# {signal.title}",
        "",
        f"- **Status:** {signal.status.value}",
        f"- **Confidence:** {signal.confidence:.2f}",
        f"- **Topic:** {signal.topic or 'n/a'}",
        f"- **Ticker:** {signal.ticker or 'n/a'}",
        "",
        "## Core Hypothesis",
        "",
        signal.hypothesis,
        "",
    ]
    lines.extend(_evidence_section("Supporting Evidence", supporting))
    lines.extend(_evidence_section("Counter Evidence", counter))
    lines.extend(_evidence_section("Neutral Evidence", neutral))

    lines.extend(["## Watchlist", ""])
    if signal.watchlist:
        for item in signal.watchlist:
            source = f" Source hint: {item.source_hint}." if item.source_hint else ""
            lines.append(f"- **{item.metric}:** {item.why}.{source}")
    else:
        lines.append("- No watch items yet.")

    lines.extend(["", "## Update History", ""])
    if signal.updates:
        for item in signal.updates[-10:]:
            lines.append(
                f"- {item.created_at}: {item.previous_status.value} -> "
                f"{item.current_status.value}. {item.summary}"
            )
    else:
        lines.append("- No evaluations recorded yet.")

    return "\n".join(lines).rstrip() + "\n"


def render_html_graph(signal: Signal) -> str:
    supporting = [item for item in signal.evidence if item.kind == EvidenceKind.SUPPORT]
    counter = [item for item in signal.evidence if item.kind == EvidenceKind.COUNTER]
    neutral = [item for item in signal.evidence if item.kind == EvidenceKind.NEUTRAL]
    support_score = sum(item.weight for item in supporting)
    counter_score = sum(item.weight for item in counter)
    neutral_score = sum(item.weight for item in neutral)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(signal.title)} - FinTrace Evidence Graph</title>
  <style>
    :root {{
      --paper: #f6f8f4;
      --ink: #191c20;
      --muted: #66706b;
      --line: #d7ddd5;
      --panel: #ffffff;
      --support: #007a5c;
      --counter: #b23a48;
      --neutral: #6d7280;
      --watch: #bd7b00;
      --accent: #335cbb;
      --shadow: 0 18px 50px rgba(25, 28, 32, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        linear-gradient(90deg, rgba(25, 28, 32, 0.035) 1px, transparent 1px),
        linear-gradient(180deg, rgba(25, 28, 32, 0.035) 1px, transparent 1px),
        var(--paper);
      background-size: 28px 28px;
      color: var(--ink);
      font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 34px 0 42px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 24px;
      align-items: end;
      border-bottom: 2px solid var(--ink);
      padding-bottom: 22px;
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 4.5vw, 4.8rem);
      line-height: 0.92;
      letter-spacing: 0;
      max-width: 820px;
    }}
    .meta {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.78rem;
      text-transform: uppercase;
    }}
    .pill {{
      border: 1px solid var(--ink);
      background: var(--panel);
      padding: 7px 9px;
      box-shadow: 3px 3px 0 var(--ink);
    }}
    .status-strengthened {{ color: var(--support); }}
    .status-weakened, .status-falsified {{ color: var(--counter); }}
    .status-active {{ color: var(--accent); }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(220px, 0.9fr) minmax(360px, 1.35fr) minmax(240px, 0.95fr);
      gap: 18px;
      align-items: start;
    }}
    section {{
      min-width: 0;
    }}
    .block {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0;
      color: var(--muted);
    }}
    p {{
      margin: 0;
      line-height: 1.45;
      font-size: 1.02rem;
    }}
    .scoreboard {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 16px;
    }}
    .score {{
      border-top: 3px solid var(--neutral);
      padding-top: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .score strong {{
      display: block;
      font-size: 1.35rem;
    }}
    .score span {{
      display: block;
      color: var(--muted);
      font-size: 0.72rem;
      text-transform: uppercase;
    }}
    .score.support {{ border-color: var(--support); }}
    .score.counter {{ border-color: var(--counter); }}
    .score.neutral {{ border-color: var(--neutral); }}
    .evidence-grid {{
      display: grid;
      gap: 12px;
    }}
    .node {{
      position: relative;
      background: var(--panel);
      border: 1px solid var(--line);
      border-left: 6px solid var(--neutral);
      padding: 14px 14px 12px;
    }}
    .node.support {{ border-left-color: var(--support); }}
    .node.counter {{ border-left-color: var(--counter); }}
    .node.neutral {{ border-left-color: var(--neutral); }}
    .node p {{
      font-size: 0.98rem;
    }}
    .source {{
      margin-top: 10px;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.72rem;
      line-height: 1.35;
    }}
    .source a {{
      color: var(--accent);
      text-decoration-thickness: 2px;
    }}
    .rail {{
      display: grid;
      gap: 12px;
    }}
    .watch {{
      border-left: 5px solid var(--watch);
    }}
    .timeline {{
      display: grid;
      gap: 10px;
    }}
    .event {{
      border-left: 3px solid var(--accent);
      padding-left: 10px;
    }}
    .event time {{
      display: block;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.7rem;
      margin-bottom: 4px;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.74rem;
    }}
    @media (max-width: 900px) {{
      header, .layout {{
        grid-template-columns: 1fr;
      }}
      .meta {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{escape(signal.title)}</h1>
      </div>
      <div class="meta">
        <span class="pill status-{escape(signal.status.value)}">{escape(signal.status.value)}</span>
        <span class="pill">confidence {signal.confidence:.2f}</span>
        <span class="pill">{escape(signal.ticker or signal.topic or "unlabeled")}</span>
      </div>
    </header>
    <div class="layout">
      <section class="block">
        <h2>Core Hypothesis</h2>
        <p>{escape(signal.hypothesis)}</p>
        <div class="scoreboard">
          <div class="score support"><strong>{support_score:.1f}</strong><span>support</span></div>
          <div class="score counter"><strong>{counter_score:.1f}</strong><span>counter</span></div>
          <div class="score neutral"><strong>{neutral_score:.1f}</strong><span>neutral</span></div>
        </div>
      </section>
      <section>
        <div class="evidence-grid">
          {_html_evidence_group("Supporting Evidence", supporting, "support")}
          {_html_evidence_group("Counter Evidence", counter, "counter")}
          {_html_evidence_group("Neutral Evidence", neutral, "neutral")}
        </div>
      </section>
      <section class="rail">
        <div class="block">
          <h2>Watchlist</h2>
          {_html_watchlist(signal)}
        </div>
        <div class="block">
          <h2>Update History</h2>
          {_html_timeline(signal)}
        </div>
      </section>
    </div>
    <footer>Generated by FinTrace. Research workflow output, not investment advice.</footer>
  </main>
</body>
</html>
"""


def _evidence_section(title: str, items: list[Evidence]) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.append("- None recorded.")
        lines.append("")
        return lines

    for item in items:
        url = f" ([source]({item.url}))" if item.url else ""
        lines.append(f"- {item.text}{url}")
        if item.reason:
            lines.append(f"  - Reason: {item.reason}")
        lines.append(f"  - Source: {item.source}; observed: {item.observed_at}; weight: {item.weight:.1f}")
    lines.append("")
    return lines


def _html_evidence_group(title: str, items: list[Evidence], kind_class: str) -> str:
    if not items:
        body = '<p class="empty">None recorded.</p>'
    else:
        body = "\n".join(_html_evidence_node(item, kind_class) for item in items)
    return f'<div class="block"><h2>{escape(title)}</h2>{body}</div>'


def _html_evidence_node(item: Evidence, kind_class: str) -> str:
    link = f' <a href="{escape(item.url)}">source link</a>' if item.url else ""
    reason = f'<div class="source">Reason: {escape(item.reason)}</div>' if item.reason else ""
    return f"""
          <article class="node {kind_class}">
            <p>{escape(item.text)}</p>
            {reason}
            <div class="source">Source: {escape(item.source)}{link}<br>Observed: {escape(item.observed_at)} | Weight: {item.weight:.1f}</div>
          </article>
"""


def _html_watchlist(signal: Signal) -> str:
    if not signal.watchlist:
        return '<p class="empty">No watch items yet.</p>'
    items = []
    for item in signal.watchlist:
        source = f"<br>Source hint: {escape(item.source_hint)}" if item.source_hint else ""
        items.append(
            f"""
          <article class="node watch">
            <p><strong>{escape(item.metric)}</strong></p>
            <div class="source">{escape(item.why)}{source}</div>
          </article>
"""
        )
    return "\n".join(items)


def _html_timeline(signal: Signal) -> str:
    if not signal.updates:
        return '<p class="empty">No evaluations recorded yet.</p>'
    events = []
    for item in signal.updates[-8:]:
        events.append(
            f"""
          <div class="event">
            <time>{escape(item.created_at)}</time>
            <p>{escape(item.previous_status.value)} -> {escape(item.current_status.value)}</p>
            <div class="source">{escape(item.summary)}</div>
          </div>
"""
        )
    return f'<div class="timeline">{"".join(events)}</div>'
