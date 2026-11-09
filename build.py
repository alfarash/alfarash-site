"""Builds the Al Farash Home Decor site designs (designs/*.html -> out/) from data/all.txt.

Each line of data/all.txt is:  ebayItemId|Title|£price|imageKey
(the title may itself contain '|'). Re-run after updating the list:
    python3 build.py
"""
import json, re, pathlib
from collections import Counter
from html import escape

ROOT = pathlib.Path(__file__).parent
FEATURED = ["333948347360", "334597439540", "335057241650", "334374678438",
            "333765265257", "333765713516", "336778677719", "336393096850"]


def clean(t):
    t = re.sub(r"[\U0001F000-\U0001FFFF☀-➿️‍]", "", t)   # no emojis on the site
    t = t.replace("pattren", "pattern").replace("crushes", "crushed")
    t = t.replace("LuxuryCushion", "Luxury Cushion").replace("Luxury17", "Luxury 17")
    t = t.replace("sideDecorative", "side Decorative").replace("Brentford FC Be ", "Brentford FC Bee ")
    t = re.sub(r"\bCove$", "Cover", t)
    t = re.sub(r"\s*/\s*", " / ", t)
    t = re.sub(r"(\d)\"(?=[A-Za-z])", r'\1" ', t)
    t = re.sub(r"(\d)”(?=[A-Za-z])", r"\1” ", t)
    t = re.sub(r"\s+", " ", t).strip(" .")
    return t[0].upper() + t[1:]


# Categories checked by eye against every listing photo live in data/categories.txt:
#   ebayItemId|primaryCategory|comma,separated,categories
# A product can sit in more than one category (e.g. a Greek circle with crystal stones).
# The title rules below are only a fallback for new listings not yet in that file.
CHECKED = {}
for _line in (ROOT / "data/categories.txt").read_text(encoding="utf-8").splitlines():
    if _line and not _line.startswith("#"):
        _id, _prim, _all = _line.split("|")
        CHECKED[_id] = (_prim, _all.split(","))


def category(t):
    l = t.lower()
    if "curtain" in l or "blind" in l:
        return "curtains"
    if "table runner" in l or "mats" in l:
        return "table"
    if re.search(r"horse|tiger|peacock|\bbee\b|unicorn|butterfly|eiffel|\blion\b|scorpio", l):
        return "motifs"
    if "crystal" in l or "stone" in l:
        return "stones"
    if "greek" in l and "circle" in l:
        return "circles"
    if "greek" in l or "scorpio" in l:
        return "greek"
    return "geometric"


# ---- Colours --------------------------------------------------------------------------------------------
# Every product has ONE main colour (the velvet / fabric itself) and any number of detail colours (the Greek key,
# border or motif: usually gold or silver). Customers filter by main colour, and optionally by detail colour, so
# "Ivory" only shows ivory covers, never "Navy & Ivory". White has its own colour, separate from ivory and cream.
# The answers checked by eye against each listing photo live in data/colours.txt:  ebayItemId|main|detail,detail
# Anything not in that file falls back to reading the title (first fabric colour named = main), which is only a guess.
FABRIC = [
    ("grey", r"silver[\s/&-]*gr[ae]y|gr[ae]y[\s/&-]*silver|\bgr[ae]y\b|charcoal"),
    ("black", r"\bblack\b"),
    ("offwhite", r"off[- ]?white"),
    ("white", r"(?<!off[- ])\bwhite\b"),
    ("ivory", r"ivory|\bcream\b"),
    ("navy", r"\bnavy\b|\bblue\b"),
    ("red", r"\bred\b|maroon|\bwine\b|burgundy"),
    ("teal", r"turquoise|\bteal\b|\baqua\b"),
    ("brown", r"\bbrown\b|\bbeige\b|\bsand\b|\bjute\b|chocolate|\btaupe\b"),
    ("pink", r"\bpink\b|fuchsia|purple|lilac|mauve|\bplum\b"),
    ("yellow", r"yellow|mustard"),
    ("green", r"\bgreen\b|emerald|olive|\bsage\b"),
]
METAL = [("gold", r"\bgold(en)?\b"), ("silver", r"\bsilver\b")]
MAIN_KEYS = [k for k, _ in FABRIC] + ["gold"]
DETAIL_KEYS = ["gold", "silver"] + [k for k, _ in FABRIC]
CHECKED_COLOURS = {}
_cf = ROOT / "data/colours.txt"
if _cf.exists():
    for _line in _cf.read_text(encoding="utf-8").splitlines():
        if _line.strip() and not _line.startswith("#"):
            _id, _main, _det = (_line.split("|") + ["", ""])[:3]
            _dets = [d for d in _det.split(",") if d]
            assert _main in MAIN_KEYS, (_id, _main)
            assert all(d in DETAIL_KEYS for d in _dets), (_id, _dets)
            CHECKED_COLOURS[_id] = (_main, _dets)


def colours_from_title(t):
    """Best guess from the title: (main, details, sure)."""
    l = t.lower()
    found = []
    for k, rx in FABRIC:
        m = re.search(rx, l)
        if m:
            found.append((m.start(), k))
            l = l[:m.start()] + " " * (m.end() - m.start()) + l[m.end():]   # "silver grey" counts once
    fabric = [k for _, k in sorted(found)]
    metals = [k for k, rx in METAL if re.search(rx, l)]
    if fabric:
        main = fabric[0]
    elif metals == ["gold"]:
        main = "gold"
    elif metals == ["silver"]:
        main = "grey"
    else:
        main = ""
    details = [("silver" if k == "grey" else k) for k in fabric[1:] + metals if k != main]
    details = list(dict.fromkeys(details))
    return main, details, len(fabric) == 1


def colours(pid, t):
    if pid in CHECKED_COLOURS:
        main, dets = CHECKED_COLOURS[pid]
        return main, dets, True
    return colours_from_title(t)


def size(t, cat):
    if cat in ("curtains", "table"):
        return None
    for m in re.finditer(r"(\d{2})\s*(?:\"|”|“|inch|in\b|x|×|\s*Inch)", t):
        n = int(m.group(1))
        if 16 <= n <= 24:
            return n
    m = re.search(r"\b(1[6-9]|2[0-4])\b", t)
    return int(m.group(1)) if m else None


# Cushion sizes checked against each listing's eBay item details, description and title live in
# data/sizes.txt (ebayItemId|inches|note). Titles often leave the size out, so the title rule above
# is only a fallback for new listings not yet in that file.
SIZES = {}
for _line in (ROOT / "data/sizes.txt").read_text(encoding="utf-8").splitlines():
    if _line and not _line.startswith("#"):
        _id, _in = _line.split("|")[:2]
        SIZES[_id] = int(_in)
UNSIZED = []

# Listings deliberately kept off the website (still live on eBay). Remove an ID here to show it.
EXCLUDE = {
    "336850765520",  # black cushion showing the Chanel "CC" logo in crystals - brand logo, held back
}


def table_label(t):
    l = t.lower()
    runner, mats = "runner" in l, ("placemat" in l or "mats" in l)
    m = re.search(r"(\d+)\s*(?:pcs|pieces)", l)
    if runner and mats:
        n = re.search(r"\+\s*(\d+)\s*[x×]", l)
        return f"Runner + {n.group(1)} placemats" if n else "Runner & placemats set"
    if mats:
        if m:
            return f"{m.group(1)}-piece mats set"
        n = re.search(r"set of (\d+)", l)
        return f"Set of {n.group(1)} placemats" if n else "Placemats"
    if runner:
        d = re.search(r"(\d{2,3})\s*cm\s*[x×]\s*(\d{2,3})\s*cm", t)
        return f"Runner {d.group(1)} × {d.group(2)} cm" if d else "Table runner"
    return "Table set"


# Live eBay titles (data/titles_ebay.txt) replace the old ones; the old title is kept as search keywords ("k").
NEW_TITLE = {}
for _line in (ROOT / "data/titles_ebay.txt").read_text(encoding="utf-8").splitlines():
    if _line and not _line.startswith("#"):
        _id, _t, _w = (_line.split("|", 2) + [""])[:3]
        NEW_TITLE[_id] = (_t, _w)

# Where the listings come from:
#  - data/live.tsv (written every day by scripts/fetch_ebay.py from eBay itself): the live titles, prices and photos.
#    New listings appear on the site and ended ones disappear automatically.
#  - data/all.txt: the older hand-made list. Used on its own only if live.tsv is missing; otherwise its titles are
#    kept as hidden search words, so visitors searching the old wording still find the cushion.
OLD = {}
for line in (ROOT / "data/all.txt").read_text(encoding="utf-8").splitlines():
    parts = line.split("|")
    if len(parts) >= 4:
        OLD[parts[0]] = (clean(" · ".join(p.strip() for p in parts[1:-2])), parts[-2], parts[-1])

LIVE_FILE = ROOT / "data/live.tsv"
SOURCE = []    # (id, title shown on the site, older title or "", price, photo key)
if LIVE_FILE.exists():
    for line in LIVE_FILE.read_text(encoding="utf-8").splitlines():
        p = line.split("\t")
        if len(p) == 4 and not line.startswith("#"):
            SOURCE.append((p[0], clean(p[1]), OLD.get(p[0], ("",))[0], p[2], p[3]))
else:
    for pid, (title, price, img) in OLD.items():
        SOURCE.append((pid, NEW_TITLE[pid][0] if pid in NEW_TITLE else title, title, price, img))

products = []
UNCHECKED = []
for pid, shown, old_title, price, img in SOURCE:
    if pid in EXCLUDE:
        continue
    title = old_title or shown       # older wording drives the fallback rules for listings already checked by eye
    if pid in CHECKED:
        cat, cats = CHECKED[pid]
    else:
        cat = category(shown)
        cats = [cat]
        UNCHECKED.append(f"{pid} {shown}")
    products.append({
        "id": pid,
        "t": shown,
        "p": float(price.replace("£", "").replace(",", "")),
        "img": img,
        "c": cat,
        "cs": cats,
        "mc": colours(pid, title)[0],
        "dt": colours(pid, title)[1],
        "s": SIZES.get(pid) if cat not in ("curtains", "table") and pid in SIZES else size(title, cat),
        "f": FEATURED.index(pid) if pid in FEATURED else 999,
    })
    _w = NEW_TITLE.get(pid, ("", ""))[1]
    _k = " ".join(x for x in ([old_title] if old_title and old_title != shown else []) + [_w] if x)
    if _k:
        products[-1]["k"] = _k      # old wording, searchable but not shown
    if cat == "table":
        products[-1]["tl"] = table_label(title)
    elif cat != "curtains" and pid not in SIZES:
        UNSIZED.append(f"{pid} {shown}")

data = json.dumps(products, ensure_ascii=False, separators=(",", ":"))
app = (ROOT / "shared.js").read_text(encoding="utf-8").replace("/*__PRODUCTS__*/[]", data)
out = ROOT / "out"
out.mkdir(exist_ok=True)
BY_ID = {p["id"]: p for p in products}
CAT_COUNTS = Counter(c for p in products for c in p["cs"])


def prerender(html):
    """Write photos, links, prices and counts straight into the HTML, so the page looks
    right before (or without) JavaScript running. The script still fills them too."""
    def img_url(p, size):
        return f"https://i.ebayimg.com/images/g/{p['img']}/s-l{size}.webp"

    def link(m):
        block = m.group(0)
        pid = re.search(r'data-pid="(\d+)"', block)
        p = BY_ID.get(pid.group(1)) if pid else None
        if not p:
            return block
        has_text = re.sub(r"<[^>]+>", "", block).strip()
        attrs = f' href="https://www.ebay.co.uk/itm/{p["id"]}" target="_blank" rel="noopener"'
        if not has_text:
            attrs += f' aria-label="{escape(p["t"])} (opens eBay)"'
        return block.replace("<a ", "<a" + attrs + " ", 1) if " data-link" in block[:60] else block

    html = re.sub(r'<a\b[^>]*\bdata-link\b[^>]*>.*?</a>', link, html, flags=re.S)

    def img(m):
        tag = m.group(0)
        if " src=" in tag:
            return tag
        p = BY_ID.get(m.group(1))
        if not p:
            return tag
        size = int(re.search(r'data-size="(\d+)"', tag).group(1)) if 'data-size="' in tag else 640
        extra = ""
        if " sizes=" in tag:  # responsive photo: let the browser pick the right size for the screen
            widths = [w for w in (640, 960, 1600) if w <= size] or [size]
            extra = 'srcset="' + ", ".join(f"{img_url(p, w)} {w}w" for w in widths) + '" '
        return tag.replace("<img ", f'<img src="{img_url(p, size)}" {extra}', 1)

    html = re.sub(r'<img\b[^>]*\bdata-pid="(\d+)"[^>]*>', img, html)
    html = re.sub(r'(data-price-of="(\d+)"[^>]*>)(</)', lambda m: m.group(1) + (f"£{BY_ID[m.group(2)]['p']:.2f}" if m.group(2) in BY_ID else "") + m.group(3), html)
    html = re.sub(r'(data-title-of="(\d+)"[^>]*>)(</)', lambda m: m.group(1) + (escape(BY_ID[m.group(2)]["t"]) + " (opens eBay in a new tab)" if m.group(2) in BY_ID else "") + m.group(3), html)
    html = re.sub(r'(data-count="(\w+)"[^>]*>)(</)', lambda m: m.group(1) + str(len(products) if m.group(2) == "all" else CAT_COUNTS.get(m.group(2), 0)) + m.group(3), html)
    return html


for design in sorted((ROOT / "designs").glob("*.html")):
    html = design.read_text(encoding="utf-8").replace("/*__APP__*/", app).replace("__COUNT__", str(len(products)))
    html = prerender(html)
    (out / design.name).write_text(html, encoding="utf-8")
    print("built", out / design.name)

print(len(products), "products")
print(Counter(c for p in products for c in p["cs"]))
if UNCHECKED:
    print(f"{len(UNCHECKED)} products sorted by title only (add them to data/categories.txt):")
    for t in UNCHECKED:
        print("  ", t)
if UNSIZED:
    print(f"{len(UNSIZED)} cushions sized from the title only (add them to data/sizes.txt):")
    for t in UNSIZED:
        print("  ", t)
print("main colours:", Counter(p["mc"] or "(unknown)" for p in products))
print("details:", Counter(d for p in products for d in p["dt"]))
UNSURE = [p["id"] for p in products if not colours(p["id"], p["t"])[2]]
print(f"{len(products) - len(UNSURE)} colours checked or clear from the title, {len(UNSURE)} still to check against the photo")
print(Counter(p["s"] for p in products))
