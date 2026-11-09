"""Reads the shop's live eBay listings and writes data/live.tsv (one line per listing:
ebayItemId <TAB> title <TAB> £price <TAB> photoKey), which build.py turns into the website.

It uses eBay's official Browse API with an application key (no eBay sign-in, read only).
The keys come from two environment variables, which GitHub fills from the repository Secrets:
    EBAY_CLIENT_ID      (eBay developer "App ID")
    EBAY_CLIENT_SECRET  (eBay developer "Cert ID")

Safety: if eBay can't be reached, returns an error, or suddenly reports far fewer listings than
last time, the script stops WITHOUT touching data/live.tsv, so the website keeps its last good copy.

Run locally:  EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python3 scripts/fetch_ebay.py
Test without eBay:  python3 scripts/fetch_ebay.py --from-json page1.json [page2.json ...]
"""
import base64, json, os, re, sys, time, pathlib, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/live.tsv"
SELLER = os.environ.get("EBAY_SELLER", "al-farash")
# 11700 = Home, Furniture & DIY on eBay UK: covers cushions, curtains and table linen together.
CATEGORIES = os.environ.get("EBAY_CATEGORIES", "11700").split(",")
MIN_LISTINGS = 50          # fewer than this almost certainly means something went wrong
MAX_DROP = 0.25            # stop if more than 25% of last time's listings vanish in one go
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def fail(msg):
    print("STOPPED: " + msg, file=sys.stderr)
    print("data/live.tsv was not changed, so the website keeps its last good copy.", file=sys.stderr)
    sys.exit(1)


def http(url, data=None, headers=None, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and n < tries - 1:
                time.sleep(5 * (n + 1)); continue
            fail(f"eBay answered {e.code} for {url.split('?')[0]}: {body}")
        except (urllib.error.URLError, TimeoutError) as e:
            if n < tries - 1:
                time.sleep(5 * (n + 1)); continue
            fail(f"couldn't reach eBay ({e})")


def get_token():
    cid, secret = os.environ.get("EBAY_CLIENT_ID", "").strip(), os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        fail("the EBAY_CLIENT_ID / EBAY_CLIENT_SECRET secrets are not set")
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    r = http(TOKEN_URL, body, {"Authorization": "Basic " + basic,
                               "Content-Type": "application/x-www-form-urlencoded"})
    return r["access_token"]


def api_pages():
    tok = get_token()
    headers = {"Authorization": "Bearer " + tok, "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
               "Accept-Language": "en-GB"}
    for cat in CATEGORIES:
        offset = 0
        while True:
            q = urllib.parse.urlencode({"category_ids": cat.strip(), "filter": f"sellers:{{{SELLER}}}",
                                        "limit": 200, "offset": offset})
            page = http(f"{SEARCH_URL}?{q}", headers=headers)
            yield page
            offset += 200
            if not page.get("next") or offset >= page.get("total", 0) or offset >= 9800:
                break
            time.sleep(0.5)


def photo_key(url):
    m = re.search(r"/images/g/([^/]+)/", url or "")
    return m.group(1) if m else ""


def parse(pages):
    """API pages -> {id: (title, price, key)}. Listings with options (variations) appear once, at the lowest price."""
    items = {}
    for page in pages:
        for it in page.get("itemSummaries", []) or []:
            seller = (it.get("seller") or {}).get("username", SELLER)
            if seller.lower() != SELLER.lower():
                continue
            iid = it.get("legacyItemId") or (it.get("itemId", "").split("|") + ["", ""])[1]
            price = (it.get("price") or {}).get("value")
            if not iid or price is None:
                continue
            title = re.sub(r"\s+", " ", it.get("title", "")).strip()
            key = photo_key((it.get("image") or {}).get("imageUrl")) or \
                next((photo_key(a.get("imageUrl")) for a in it.get("additionalImages") or [] if photo_key(a.get("imageUrl"))), "")
            price = float(price)
            if iid in items and items[iid][1] <= price:
                continue
            items[iid] = (title, price, key)
    return items


def previous():
    old = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) == 4 and not line.startswith("#"):
                old[p[0]] = p
    return old


def main():
    if sys.argv[1:2] == ["--from-json"]:
        items = parse(json.load(open(f, encoding="utf-8")) for f in sys.argv[2:])
    else:
        items = parse(api_pages())
    old = previous()
    if len(items) < MIN_LISTINGS:
        fail(f"eBay returned only {len(items)} listings")
    if old and len(items) < len(old) * (1 - MAX_DROP):
        fail(f"eBay returned {len(items)} listings, down from {len(old)} last time - too big a drop to trust. "
             "If the shop really ended that many listings, delete data/live.tsv in GitHub and run again.")
    lines = ["# Live eBay listings, written by scripts/fetch_ebay.py - don't edit by hand: id<TAB>title<TAB>price<TAB>photo key"]
    no_photo = []
    for iid in sorted(items, reverse=True):
        title, price, key = items[iid]
        if not key and iid in old:
            key = old[iid][3]            # keep last known photo rather than show none
        if not key:
            no_photo.append(iid); continue
        title = title.replace("\t", " ")
        lines.append(f"{iid}\t{title}\t£{price:.2f}\t{key}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written = {l.split("\t")[0] for l in lines[1:]}
    new, gone = written - set(old), set(old) - written
    print(f"{len(lines) - 1} listings written to data/live.tsv")
    if old:
        print(f"new since last time: {len(new)} {sorted(new)}")
        print(f"ended since last time: {len(gone)} {sorted(gone)}")
    if no_photo:
        print(f"skipped (no photo): {no_photo}")


if __name__ == "__main__":
    main()
