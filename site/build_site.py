#!/usr/bin/env python3
"""Render logs/week-*.md into a static public site under _site/."""

import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
SITE_DIR = ROOT / "site"
OUT_DIR = ROOT / "_site"

SECTION_ORDER = ["Goals", "Approach and Implementation", "Results", "Notes"]

WEEK_RE = re.compile(r"^#\s*Week\s*(\d+)", re.IGNORECASE)
DATES_RE = re.compile(r"\*\*Dates:\*\*\s*(.+)")
SECTION_RE = re.compile(r"^##\s*(.+)$")


def parse_log(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    week_num = None
    dates = ""
    sections = {name: [] for name in SECTION_ORDER}
    current = None

    for line in lines:
        m = WEEK_RE.match(line)
        if m:
            week_num = int(m.group(1))
            continue
        m = DATES_RE.search(line)
        if m:
            dates = m.group(1).strip()
            continue
        m = SECTION_RE.match(line)
        if m:
            name = m.group(1).strip()
            current = name if name in sections else None
            continue
        if current:
            sections[current].append(line)

    for name in sections:
        sections[name] = "\n".join(sections[name]).strip()

    dates_filled = bool(dates) and "MM-DD" not in dates
    required_filled = all(sections[name] for name in ["Goals", "Approach and Implementation", "Results"])

    if not dates_filled:
        status = "not-started"
    elif required_filled:
        status = "complete"
    else:
        status = "in-progress"

    return {
        "week_num": week_num,
        "dates": dates if dates_filled else None,
        "sections": sections,
        "status": status,
    }


def parse_student_info():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    student = re.search(r"\*\*Student:\*\*\s*(.+?)\s{2,}", readme)
    mentor = re.search(r"\*\*Mentor:\*\*\s*(.+?)\s{2,}", readme)

    def clean(m, placeholder):
        if not m:
            return None
        value = m.group(1).strip()
        return None if value == placeholder else value

    return {
        "student": clean(student, "Your Full Name"),
        "mentor": clean(mentor, "Mentor Full Name"),
    }


STATUS_LABEL = {
    "complete": "Complete",
    "in-progress": "In progress",
    "not-started": "Not started",
}

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <a class="site-title" href="index.html">{student} - DREU Log</a>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>Public research progress log for the <a href="https://cra.org/cra-wp/active-programs/dreu/" target="_blank" rel="noopener">DREU program</a>. Built from <a href="https://github.com/cra-wp/dreu" target="_blank" rel="noopener">cra-wp/dreu</a>.</p>
</footer>
</body>
</html>
"""


def render_index(weeks, info):
    student = info["student"] or "DREU Student"
    mentor_html = f'<p class="mentor">Mentor: {info["mentor"]}</p>' if info["mentor"] else ""

    cards = []
    for week in weeks:
        n = week["week_num"]
        status = week["status"]
        label = STATUS_LABEL[status]
        dates = week["dates"] or "&mdash;"
        goals_preview = week["sections"]["Goals"].splitlines()
        preview = goals_preview[0].lstrip("- ").strip() if goals_preview else ""
        cards.append(f"""
  <a class="week-card status-{status}" href="week-{n:02d}.html">
    <div class="week-card-head">
      <span class="week-num">Week {n}</span>
      <span class="status-badge status-{status}">{label}</span>
    </div>
    <div class="week-dates">{dates}</div>
    <div class="week-preview">{preview}</div>
  </a>""")

    body = f"""
<section class="hero">
  <h1>{student} - DREU Log</h1>
  {mentor_html}
  <p class="hero-sub">Weekly progress across the 10-week Distributed Research Experiences for Undergraduates program.</p>
</section>
<section class="week-grid">
{''.join(cards)}
</section>
"""
    html = PAGE_TEMPLATE.format(
        title=f"{student} - DREU Log",
        student=student,
        body=body,
    )
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")


def render_week(week, info, prev_n, next_n, total):
    n = week["week_num"]
    student = info["student"] or "DREU Student"

    if week["status"] == "not-started":
        body_sections = '<p class="empty-note">This week has not been logged yet.</p>'
    else:
        parts = []
        for name in SECTION_ORDER:
            content = week["sections"][name]
            if not content:
                continue
            html_content = markdown.markdown(content, extensions=["extra"])
            parts.append(f'<section class="log-section"><h2>{name}</h2>{html_content}</section>')
        body_sections = "\n".join(parts)

    nav_parts = []
    if prev_n:
        nav_parts.append(f'<a class="nav-link" href="week-{prev_n:02d}.html">&larr; Week {prev_n}</a>')
    else:
        nav_parts.append('<span class="nav-link disabled">&larr; Week</span>')
    nav_parts.append('<a class="nav-link" href="index.html">All weeks</a>')
    if next_n:
        nav_parts.append(f'<a class="nav-link" href="week-{next_n:02d}.html">Week {next_n} &rarr;</a>')
    else:
        nav_parts.append('<span class="nav-link disabled">Week &rarr;</span>')

    dates_line = f'<p class="week-dates-full">{week["dates"]}</p>' if week["dates"] else ""

    body = f"""
<nav class="week-nav">{''.join(nav_parts)}</nav>
<article>
  <h1>Week {n} of {total}</h1>
  {dates_line}
  {body_sections}
</article>
<nav class="week-nav">{''.join(nav_parts)}</nav>
"""
    html = PAGE_TEMPLATE.format(
        title=f"Week {n} - {student} - DREU Log",
        student=student,
        body=body,
    )
    (OUT_DIR / f"week-{n:02d}.html").write_text(html, encoding="utf-8")


def main():
    log_paths = sorted(LOGS_DIR.glob("week-*.md"))
    if not log_paths:
        print("No log files found in logs/", file=sys.stderr)
        sys.exit(1)

    weeks = [parse_log(p) for p in log_paths]
    weeks.sort(key=lambda w: w["week_num"])
    info = parse_student_info()

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "style.css").write_text((SITE_DIR / "style.css").read_text(encoding="utf-8"), encoding="utf-8")

    render_index(weeks, info)

    total = len(weeks)
    for i, week in enumerate(weeks):
        prev_n = weeks[i - 1]["week_num"] if i > 0 else None
        next_n = weeks[i + 1]["week_num"] if i < total - 1 else None
        render_week(week, info, prev_n, next_n, total)

    started = sum(1 for w in weeks if w["status"] != "not-started")
    print(f"Built {total} week page(s) + index into {OUT_DIR} ({started} started).")


if __name__ == "__main__":
    main()
