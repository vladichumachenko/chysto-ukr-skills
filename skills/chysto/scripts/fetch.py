"""Fetch a published article and convert its body to Markdown.

The body is the first <article>, else <main>, else <body>; navigation, scripts and
other page chrome are dropped. Only the structure the review needs is kept: headings,
paragraphs, lists, quotes, code.

Usage: python3 fetch.py URL [-o FILE.md]
"""
import argparse
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

DROP = {"script", "style", "button", "svg", "form", "noscript", "template", "iframe"}
# Page chrome: dropped when the body falls back to <main>/<body>; inside an <article>
# these elements are part of the text (e.g. a glossary in an <aside>).
CHROME = {"nav", "header", "footer", "aside"}
VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "base", "col", "embed", "track"}
BLOCKS = {"p", "div", "section", "figure", "figcaption", "dl", "dt", "dd", "table", "tr", "details", "summary"}
MIN_CHARS = 200
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126 Safari/537.36")


class FetchError(Exception):
    pass


class Node:
    def __init__(self, tag, parent=None):
        self.tag, self.parent, self.children = tag, parent, []


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def _find(node, tag):
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag:
                return c
            hit = _find(c, tag)
            if hit:
                return hit
    return None


def _text(node) -> str:
    """Raw text of a subtree (used for <pre>)."""
    return "".join(c if isinstance(c, str) else _text(c) for c in node.children
                   if isinstance(c, str) or c.tag not in DROP)


def _inline(node) -> str:
    out = []
    for c in node.children:
        if isinstance(c, str):
            out.append(c)
        elif c.tag in DROP:
            continue
        elif c.tag == "br":
            out.append("\n")
        elif c.tag == "code":
            out.append(f"`{_text(c).strip()}`")
        else:
            out.append(_inline(c))
    return "".join(out)


def _clean(s: str) -> str:
    return "\n".join(re.sub(r"[ \t\r\f\v ]+", " ", ln).strip() for ln in s.split("\n")).strip()


def _inline_node(node) -> str:
    if node.tag == "code":
        return f"`{_text(node).strip()}`"
    if node.tag == "br":
        return "\n"
    return _inline(node)


def _render(node, out: list, drop=DROP) -> None:
    """Append Markdown blocks for node's children to out."""
    inline_buf = []

    def flush():
        text = _clean("".join(inline_buf))
        if text:
            out.append(text)
        inline_buf.clear()

    for c in node.children:
        if isinstance(c, str):
            inline_buf.append(c)
            continue
        tag = c.tag
        if tag in drop:
            continue
        if re.fullmatch(r"h[1-6]", tag):
            flush()
            text = _clean(_inline(c))
            if text:
                out.append("#" * int(tag[1]) + " " + text)
        elif tag == "pre":
            flush()
            out.append("```\n" + _text(c).strip("\n") + "\n```")
        elif tag in ("ul", "ol"):
            flush()
            items = [_clean(_inline(li)) for li in c.children if isinstance(li, Node) and li.tag == "li"]
            marker = (lambda i: f"{i}.") if tag == "ol" else (lambda i: "-")
            lines = [f"{marker(i)} {t}" for i, t in enumerate(items, 1) if t]
            if lines:
                out.append("\n".join(lines))
        elif tag == "blockquote":
            flush()
            inner = []
            _render(c, inner, drop)
            if inner:
                out.append("\n".join("> " + ln if ln else ">" for ln in "\n\n".join(inner).split("\n")))
        elif tag in BLOCKS or tag in CHROME or tag in ("li", "main", "article", "body"):
            flush()
            _render(c, out, drop)
        else:
            inline_buf.append(_inline_node(c))
    flush()


def html_to_markdown(page: str) -> str:
    tb = _TreeBuilder()
    tb.feed(page)
    article = _find(tb.root, "article")
    body = article or _find(tb.root, "main") or _find(tb.root, "body") or tb.root
    blocks = []
    _render(body, blocks, DROP if article else DROP | CHROME)
    md = "\n\n".join(blocks).strip() + "\n"
    if len(re.sub(r"\s", "", md)) < MIN_CHARS:
        raise FetchError(f"extracted only {len(md.strip())} characters; the page body was not found")
    return md


def output_name(url: str) -> str:
    p = urlparse(url)
    segs = [s for s in p.path.split("/") if s]
    stem = segs[-1] if segs else p.netloc
    stem = re.sub(r"\.(html?|php|aspx?)$", "", stem) or "article"
    return f"{stem}.md"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "uk,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch an article and save its body as Markdown.")
    ap.add_argument("url")
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args(argv)
    try:
        md = html_to_markdown(fetch(a.url))
    except FetchError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    except OSError as err:  # urllib.error.URLError and HTTPError are OSError subclasses
        print(f"error: could not fetch {a.url}: {err}", file=sys.stderr)
        return 1
    out = Path(a.output or output_name(a.url))
    out.write_text(md, encoding="utf-8")
    print(f"{len(md)} characters -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
