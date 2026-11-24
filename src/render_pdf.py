"""Render the final Markdown deliverables to PDF (Markdown stays the source of truth).

    uv run python -m src.render_pdf

A small, dependency-free Markdown -> HTML converter covering the constructs used in outputs/final/*.md
(headings, paragraphs, nested lists, tables, block quotes, code, bold/italic/inline code, rules), styled with
print CSS (A4, page numbers in the footer) and printed with the local headless Google Chrome.
Writes outputs/final/pdf/<name>.pdf and reports page counts. The executive memo must fit on one page.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FINAL = Path("outputs/final")
PDF_DIR = FINAL / "pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MEMO_CSS = """
@page { margin: 11mm 14mm 13mm 14mm; }
body { line-height: 1.3; }
h1 { margin-bottom: .3em; }
h2 { margin: .75em 0 .3em; }
p { margin: .25em 0 .35em; }
ul, ol { margin: .15em 0 .35em; }
li { margin: .06em 0; }
table { margin: .3em 0 .45em; }
th, td { padding: 2.6px 5px; }
"""
DOCS = {  # file: (title in footer, base font size pt, extra css)
    "Executive_Product_Memo.md": ("TalentFlow Q3 · Executive Product Memo", 9.2, MEMO_CSS),
    "Q3_Product_Roadmap.md": ("TalentFlow Q3 · Product Roadmap", 9.4, ""),
    "Metrics_Specification.md": ("TalentFlow Q3 · Metrics Specification", 9.4, ""),
}


def inline(t: str) -> str:
    codes = []

    def keep(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", keep, t)
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?:(?<=^)|(?<=[\s(]))\*(?![\s*)])(.+?)(?<![\s*\-])\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], t)


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells, cur, in_code = [], "", False
    for ch in line:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return cells


def md_to_html(md: str) -> str:
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            i += 1
            continue
        if re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            head = split_row(line)
            aligns = ["right" if c.strip().endswith(":") and not c.strip().startswith(":") else "left" for c in split_row(lines[i + 1])]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            if any(c.strip() for c in head):
                t = ["<table><thead><tr>" + "".join(f'<th style="text-align:{aligns[k] if k < len(aligns) else "left"}">{inline(c)}</th>'
                                                   for k, c in enumerate(head)) + "</tr></thead><tbody>"]
            else:   # key/value table with an empty header row: no header, bold first column
                t = ['<table class="kv"><tbody>']
            for r in rows:
                t.append("<tr>" + "".join(f'<td style="text-align:{aligns[k] if k < len(aligns) else "left"}">{inline(c)}</td>'
                                          for k, c in enumerate(r)) + "</tr>")
            out.append("".join(t) + "</tbody></table>")
            i = j
            continue
        if line.startswith(">"):
            j, buf = i, []
            while j < len(lines) and lines[j].startswith(">"):
                buf.append(lines[j][1:].lstrip())
                j += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf)) + "</blockquote>")
            i = j
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            j, block = i, []
            while j < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]) or (lines[j].startswith("  ") and lines[j].strip())):
                block.append(lines[j])
                j += 1
            out.append(render_list(block))
            i = j
            continue
        j, buf = i, []
        while j < len(lines) and lines[j].strip() and not re.match(r"^(#{1,6}\s|\||>|```|\s*([-*]|\d+\.)\s)", lines[j]):
            buf.append(lines[j].strip())
            j += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")
        i = j
    return "\n".join(out)


def render_list(block: list[str]) -> str:
    items, base = [], len(block[0]) - len(block[0].lstrip())
    ordered = bool(re.match(r"^\s*\d+\.", block[0]))
    for ln in block:
        ind = len(ln) - len(ln.lstrip())
        m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)", ln)
        if m and ind == base:
            items.append([m.group(2), []])
        elif items:
            items[-1][1].append(ln[base + 2:] if len(ln) > base + 2 else ln.strip())
    tag = "ol" if ordered else "ul"
    parts = []
    for text, sub in items:
        inner = inline(text)
        if sub:
            sub_md = "\n".join(sub)
            inner += md_to_html(sub_md) if not re.match(r"^\s*([-*]|\d+\.)\s", sub[0]) else render_list(sub)
        parts.append(f"<li>{inner}</li>")
    return f"<{tag}>" + "".join(parts) + f"</{tag}>"


CSS = """
@page { size: A4; margin: 14mm 15mm 16mm 15mm;
  @bottom-left { content: "%(title)s"; font: 7.5pt -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #6b7280; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 7.5pt -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #6b7280; } }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; font-size: %(size)spt; line-height: 1.38; color: #1f2937; margin: 0; }
h1 { font-size: 1.75em; color: #0f2a4a; margin: 0 0 .35em; padding-bottom: .25em; border-bottom: 2px solid #0f2a4a; }
h2 { font-size: 1.22em; color: #0f2a4a; margin: 1.05em 0 .4em; padding-bottom: .15em; border-bottom: 1px solid #d6dde8; break-after: avoid; }
h3 { font-size: 1.07em; color: #17406d; margin: .95em 0 .35em; break-after: avoid; }
h4 { font-size: 1em; color: #17406d; margin: .8em 0 .3em; break-after: avoid; }
p { margin: .35em 0 .5em; }
ul, ol { margin: .25em 0 .55em; padding-left: 1.35em; }
li { margin: .12em 0; }
table { width: 100%%; border-collapse: collapse; margin: .45em 0 .75em; font-size: .9em; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #eef2f8; color: #0f2a4a; font-weight: 600; border: 1px solid #c9d3e1; padding: 3.5px 5px; vertical-align: bottom; }
td { border: 1px solid #d6dde8; padding: 3.5px 5px; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f8fafc; }
code { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: .86em; background: #f1f4f8; padding: 0 .2em; border-radius: 2px; }
pre { background: #f1f4f8; padding: 6px 8px; border-radius: 3px; font-size: .85em; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
table.kv td:first-child { font-weight: 600; color: #0f2a4a; background: #f4f7fb; width: 17%%; }
blockquote { margin: .5em 0; padding: .35em .8em; border-left: 3px solid #17406d; background: #f4f7fb; color: #374151; }
blockquote p { margin: .2em 0; }
strong { color: #111827; }
hr { border: 0; border-top: 1px solid #d6dde8; margin: .8em 0; }
"""


def render(name: str, title: str, size: float, extra: str = "") -> tuple[Path, int]:
    md = (FINAL / name).read_text()
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
           f"<style>{CSS % {'title': title.replace(chr(34), ''), 'size': size}}{extra}</style></head><body>{md_to_html(md)}</body></html>")
    PDF_DIR.mkdir(exist_ok=True)
    out = PDF_DIR / name.replace(".md", ".pdf")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "doc.html"
        src.write_text(doc, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
                        f"--user-data-dir={td}/profile", f"--print-to-pdf={out.resolve()}", src.as_uri()],
                       check=True, capture_output=True, timeout=120)
    return out, page_count(out)


def page_count(p: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", p.read_bytes()))


def main() -> int:
    ok = True
    for name, (title, size, extra) in DOCS.items():
        out, n = render(name, title, size, extra)
        print(f"{out}  pages={n}")
        if name == "Executive_Product_Memo.md" and n != 1:
            ok = False
            print("FAIL: executive memo is not one page")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
