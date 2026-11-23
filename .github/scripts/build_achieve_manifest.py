#!/usr/bin/env python3
"""Scan achieve/*.html and generate achieve/manifest.json for the showcase portal."""
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACHIEVE_DIR = ROOT / "achieve"
MANIFEST_PATH = ACHIEVE_DIR / "manifest.json"


def strip_tags(raw: str) -> str:
    txt = re.sub(r"<[^>]+>", "", raw or "")
    return html.unescape(txt).strip()


def get_git_date(rel_path: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs", "--", rel_path],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            return out
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def detect_series(title: str, filename: str, labels: list[str]) -> str:
    joined = f"{title} {filename} {' '.join(labels)}"
    if "T++" in joined or "年華" in joined or "思辨" in joined:
        return "T++教育+年華"
    if "噗噗聊聊" in joined or re.search(r"EP\d+", filename, re.I):
        return "噗噗聊聊 Podcast"
    if "居久屋" in joined:
        return "居久屋課程筆記"
    return "精選專題"


def parse_html_entry(p: Path) -> dict:
    raw = p.read_text(encoding="utf-8", errors="replace")

    m_title_tag = re.search(r"<title>(.*?)</title>", raw, re.I | re.S)
    raw_html_title = strip_tags(m_title_tag.group(1)) if m_title_tag else p.stem
    raw_html_title = re.sub(r"\s*-\s*全媒體創作戰情室\s*$", "", raw_html_title).strip()

    m_blog_title = re.search(r"<b>📌\s*建議文章標題：</b>(.*?)</div>", raw, re.S)
    blog_title = strip_tags(m_blog_title.group(1)) if m_blog_title else ""

    m_desc = re.search(r"<b>🔍\s*Meta\s*搜尋描述.*?：</b>(.*?)</div>", raw, re.S)
    desc = strip_tags(m_desc.group(1)) if m_desc else ""

    m_labels = re.search(r"<b>🏷️\s*Blogger\s*分類標籤.*?：</b><code>(.*?)</code>", raw, re.S)
    labels = [t.strip() for t in strip_tags(m_labels.group(1)).split(",") if t.strip()] if m_labels else []

    title = blog_title or raw_html_title or p.stem
    series = detect_series(title, p.name, labels)
    rel_path = str(p.relative_to(ROOT)).replace("\\", "/")

    return {
        "id": p.stem,
        "file": p.name,
        "title": title,
        "source_name": raw_html_title,
        "description": desc,
        "labels": labels[:8],
        "series": series,
        "size_kb": round(p.stat().st_size / 1024.0, 1),
        "updated": get_git_date(rel_path),
    }


def main():
    ACHIEVE_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(ACHIEVE_DIR.glob("*.html")):
        if p.name.lower() == "index.html":
            continue
        items.append(parse_html_entry(p))

    # Sort newest/highest EP first
    items.sort(key=lambda x: (x["updated"], x["file"]), reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(items),
        "items": items,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {MANIFEST_PATH} with {len(items)} items.")


if __name__ == "__main__":
    main()
