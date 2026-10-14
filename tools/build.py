# Builds index.html from data/pages.json.
#
# Every book page becomes a section with its Canva artwork behind it.
# On wide screens the text sits exactly where it does in Canva, sized to the page.
# On phones the same text reflows into a readable column over the artwork.
# The words themselves are copied straight from Canva and never edited here.

import html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE_W, PAGE_H = 1728, 2304

# Canva font references -> web fonts that match them
FONTS = {
    "YAFdJhX-538,0": "body",      # main serif (lowercase renders as small capitals)
    "YAFcfkb7jcU,0": "title",     # large title serif
    "YADrvjt3J6s,0": "sans",      # bold diagram letters
    "YAFdJjTk5UU,0": "sans",
}

def pct(v, total):
    return f"{v / total * 100:.4f}%"

def region_html(r):
    style = [
        f"--fs:{r['fontSize']:.2f}",
        f"color:{r['color']}",
    ]
    if r.get("fontStyle") == "italic":
        style.append("font-style:italic")
    if r.get("fontWeight") == "bold":
        style.append("font-weight:700")
    if r.get("decoration") == "underline":
        style.append("text-decoration:underline")
    if r.get("letterSpacing"):
        style.append(f"letter-spacing:{r['letterSpacing'] / 1000:.3f}em")
    family = FONTS.get(r.get("fontRef"), "body")
    text = html.escape(r["text"])
    return f'<span class="f-{family}" style="{";".join(style)}">{text}</span>'

def box_html(b):
    first = b["regions"][0]
    align = {"start": "left", "end": "right"}.get(first.get("textAlign"), first.get("textAlign") or "left")
    style = [
        f"top:{pct(b['top'], PAGE_H)}",
        f"left:{pct(b['left'], PAGE_W)}",
        f"width:{pct(b['width'], PAGE_W)}",
        f"text-align:{align}",
        f"line-height:{first.get('lineHeight') or 1.3}",
        # Base size is the smallest text in the box, so small lines aren't spaced
        # as if they were headings
        f"--fs:{min(r['fontSize'] for r in b['regions']):.2f}",
        f"--h:{b['height'] / PAGE_H:.5f}",
    ]
    if b.get("rotation"):
        style.append(f"transform:rotate({b['rotation']:.2f}deg)")
    # A box that is one line tall in Canva stays one line on wide screens
    one_line = b["height"] < first["fontSize"] * (first.get("lineHeight") or 1.3) * 1.6
    text = "".join(r["text"] for r in b["regions"])
    lines = [l for l in text.split("\n") if l.strip()]
    # Verse: many short lines broken by hand, like the poems. Each line stays whole.
    # Only when Canva didn't wrap any line: the box is no taller than its hand-broken lines
    canva_lines = b["height"] / (min(r["fontSize"] for r in b["regions"]) * (first.get("lineHeight") or 1.3))
    fits = canva_lines <= len(text.rstrip("\n").split("\n")) * 1.08
    verse = len(lines) >= 4 and max(len(l) for l in lines) <= 45 and fits
    if one_line and "\n" not in text:
        cls = "tb one-line"
    elif verse:
        cls = "tb verse"
    else:
        cls = "tb"
    if b.get("opacity", 1) < 1:
        style.append(f"opacity:{b['opacity']:.2f}")
    inner = "".join(region_html(r) for r in b["regions"])
    return f'<div class="{cls}" style="{";".join(style)}">{inner}</div>'

def reading_order(boxes):
    # Reading order on phones. Wide or centred blocks go top to bottom; between them,
    # side-by-side columns are read down the left column first, then the right, like
    # the book. Columns made of many matching rows (a saying beside its meaning) are
    # read row by row instead.
    def spanning(b):
        centre = b["left"] + b["width"] / 2
        return b["width"] > PAGE_W * 0.6 or abs(centre - PAGE_W / 2) < PAGE_W * 0.04
    def right(b):
        return b["left"] + b["width"] / 2 >= PAGE_W / 2
    ordered, band = [], []
    def flush():
        lefts = [b for b in band if not right(b)]
        rights = [b for b in band if right(b)]
        paired = sum(any(abs(l["top"] - r["top"]) < 80 for r in rights) for l in lefts)
        if paired >= 3 and paired >= len(lefts) - 1:
            band.sort(key=lambda b: (round(b["top"] / 80), right(b)))
        else:
            band.sort(key=lambda b: (right(b), b["top"], b["left"]))
        ordered.extend(band)
        band.clear()
    for b in sorted(boxes, key=lambda b: (b["top"], b["left"])):
        if spanning(b):
            flush()
            ordered.append(b)
        else:
            band.append(b)
    flush()
    return ordered

def page_html(p):
    pid = f"p{p['book_page']:02d}"
    title = html.escape(p["title"].title())
    art = f"art/{pid}.webp"
    if p.get("mode") == "image":
        # Diagram pages keep their lettering baked into the artwork; the text is
        # repeated invisibly for screen readers and search
        words = " ".join(r["text"] for b in p["boxes"] for r in b["regions"])
        return (f'<section class="page page-image" id="{pid}" aria-label="{title}">'
                f'<div class="sheet"><img class="art" src="{art}" alt="{html.escape(words)}" loading="lazy"></div>'
                f'</section>')
    boxes = reading_order(p["boxes"])
    inner = "".join(box_html(b) for b in boxes)
    lazy = "eager" if p["book_page"] == 1 else "lazy"
    cls = "page"
    full = ""
    if p.get("mode") == "diagram":
        # Diagrams: on phones the whole picture (with its lettering) comes first,
        # then the same words reflowed underneath so they stay readable
        cls += " page-diagram"
        full = f'<img class="full" src="art/{pid}-full.webp" alt="" loading="lazy">'
    if not boxes:
        cls += " page-art"
    return (f'<section class="{cls}" id="{pid}" aria-label="{title}">'
            f'<div class="sheet">{full}<img class="art" src="{art}" alt="" loading="{lazy}">{inner}</div>'
            f'</section>')

def build():
    pages = json.loads((ROOT / "data" / "pages.json").read_text())
    template = (ROOT / "tools" / "template.html").read_text()
    toc = "".join(f'<option value="p{p["book_page"]:02d}">{p["book_page"]} · {html.escape(p["title"].title())}</option>'
                  for p in pages)
    body = "\n".join(page_html(p) for p in pages)
    out = template.replace("{{TOC}}", toc).replace("{{PAGES}}", body)
    (ROOT / "index.html").write_text(out)
    print(f"Built index.html with {len(pages)} pages")

if __name__ == "__main__":
    build()
