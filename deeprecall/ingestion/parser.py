"""Step 1: Structural parsing.

Real DeepRecall would route PDFs/Word/HTML through LayoutLMv3 to recover
visual structure (headers, tables, figures, sidebars, footnotes). Here we
ship a fully-working Markdown parser that recovers the same *logical* tree
(Title → Section → Subsection → Paragraph → List → Table → Code) and
preserves parent-child relationships plus reading order.

The output is a list of DocNode objects, which downstream stages consume.
Other formats are intentionally stubbed with a clear extension point.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import DocNode, NodeType

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_FENCE = re.compile(r"^```")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")


def parse_markdown(text: str, source: str = "") -> list[DocNode]:
    """Parse markdown into an ordered tree of DocNodes."""
    lines = text.splitlines()
    nodes: list[DocNode] = []
    root = DocNode(node_type=NodeType.DOCUMENT, text=source or "document", title=source)
    nodes.append(root)

    # heading stack: (level, node_id) to resolve parent for any block
    stack: list[tuple[int, str]] = [(0, root.id)]
    order = 1

    def current_parent() -> tuple[str, str]:
        """Return (parent_id, nearest_heading_title)."""
        pid = stack[-1][1]
        title = next((n.title for n in reversed(nodes) if n.id == pid), source)
        return pid, title

    i = 0
    buf: list[str] = []

    def flush_paragraph():
        nonlocal order
        if not buf:
            return
        body = "\n".join(buf).strip()
        buf.clear()
        if not body:
            return
        pid, title = current_parent()
        node_type = NodeType.LIST if any(_LIST_ITEM.match(b) for b in body.splitlines()) else NodeType.PARAGRAPH
        node = DocNode(node_type=node_type, text=body, title=title, parent_id=pid, order=order)
        nodes.append(node)
        order += 1

    while i < len(lines):
        line = lines[i]

        m = _HEADING.match(line)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            title = m.group(2).strip()
            # pop stack to the right depth
            while stack and stack[-1][0] >= level:
                stack.pop()
            pid = stack[-1][1] if stack else root.id
            ntype = NodeType.SECTION if level <= 2 else NodeType.SUBSECTION
            node = DocNode(node_type=ntype, text=title, level=level, title=title,
                           parent_id=pid, order=order)
            nodes.append(node)
            order += 1
            stack.append((level, node.id))
            i += 1
            continue

        if _FENCE.match(line):
            flush_paragraph()
            code_lines = []
            i += 1
            while i < len(lines) and not _FENCE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            pid, title = current_parent()
            node = DocNode(node_type=NodeType.CODE, text="\n".join(code_lines),
                           title=title, parent_id=pid, order=order)
            nodes.append(node)
            order += 1
            continue

        if _TABLE_ROW.match(line):
            flush_paragraph()
            tbl = []
            while i < len(lines) and _TABLE_ROW.match(lines[i]):
                tbl.append(lines[i])
                i += 1
            pid, title = current_parent()
            node = DocNode(node_type=NodeType.TABLE, text="\n".join(tbl),
                           title=title, parent_id=pid, order=order)
            nodes.append(node)
            order += 1
            continue

        if line.strip() == "":
            flush_paragraph()
        else:
            buf.append(line)
        i += 1

    flush_paragraph()

    # wire up children lists from parent_id
    by_id = {n.id: n for n in nodes}
    for n in nodes:
        if n.parent_id and n.parent_id in by_id:
            by_id[n.parent_id].children.append(n.id)

    return nodes


def parse_file(path: str | Path) -> list[DocNode]:
    p = Path(path)
    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8", errors="replace")
    if suffix in {".md", ".markdown", ".txt"}:
        return parse_markdown(text, source=p.name)
    if suffix in {".html", ".htm"}:
        return _parse_html(text, source=p.name)
    # Extension point: PDF/Word via LayoutLMv3, unstructured, docling, etc.
    raise NotImplementedError(
        f"Parser for '{suffix}' not wired yet. Plug a LayoutLMv3/unstructured "
        f"backend here; it must return list[DocNode]."
    )


def _parse_html(text: str, source: str) -> list[DocNode]:
    """Minimal HTML→markdown shim so HTML works without extra deps."""
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    for lvl in range(1, 7):
        text = re.sub(rf"<\s*h{lvl}[^>]*>(.*?)<\s*/h{lvl}\s*>",
                      lambda m, l=lvl: f"\n{'#' * l} {m.group(1).strip()}\n",
                      text, flags=re.I | re.S)
    text = re.sub(r"<\s*li[^>]*>(.*?)<\s*/li\s*>", r"\n- \1", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "", text)  # strip remaining tags
    return parse_markdown(text, source=source)
