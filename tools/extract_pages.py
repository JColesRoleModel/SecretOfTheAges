# Pull each page's text boxes (exact characters, line breaks and styling) out of a
# Canva read-design result, so the website shows the book's words unchanged.
import json, sys

def text_boxes(page):
    boxes = []
    def walk(els):
        for e in els:
            if e["type"] == "text":
                boxes.append({
                    "top": e["top"], "left": e["left"], "width": e["width"], "height": e["height"],
                    "rotation": e.get("rotation", 0), "opacity": e.get("opacity", 1),
                    "regions": [{"text": r["characters"], **{k: r["formatting"].get(k) for k in
                                 ("fontSize", "fontWeight", "fontStyle", "color", "textAlign",
                                  "lineHeight", "letterSpacing", "decoration", "fontRef")}}
                                for r in e["textRegions"]],
                })
            elif e["type"] == "group":
                walk(e["children"])
    walk(page["elements"])
    return boxes

def extract(path):
    d = json.loads(open(path).read())
    return [{"canvaPageId": p["id"], "title": p.get("title", ""), "boxes": text_boxes(p)}
            for p in d["design_content"]["pages"]]

if __name__ == "__main__":
    out = extract(sys.argv[1])
    json.dump(out, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
    print(len(out), "pages:", [p["title"] for p in out])
