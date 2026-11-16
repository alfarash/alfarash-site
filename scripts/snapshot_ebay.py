"""Daily snapshot of the eBay shop for the weekly checks (read only, official eBay Browse API).

The scheduled Claude tasks can't reach eBay themselves, so this script (run by GitHub Actions,
see .github/workflows/shop-snapshot.yml) saves everything they need into the "shop-data" branch:

  shop/items.json            every live listing: title, price, category, location, item specifics,
                             postage (incl. excluded locations), stock, estimated units sold, photo key
  shop/descriptions/<id>.html  each listing's description
  shop/photos/<id>.jpg       each listing's main photo (small), re-downloaded only when it changes
  shop/history.tsv           one line per listing per day: date, id, price, sold, available
  market/<search>.json       top eBay UK results for popular cushion/curtain searches, with
                             estimated units sold for the leading listings (for the sales research)
  snapshot.json              when this ran and how many listings it read

Nothing here signs in to eBay or changes anything; it only reads public listing data.
Keys: EBAY_CLIENT_ID / EBAY_CLIENT_SECRET (repository Secrets), same as fetch_ebay.py.
Output folder: SNAP_DIR (default ./snap).
"""
import datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_ebay as fe  # reuses the token, search and safety code

SNAP = pathlib.Path(os.environ.get("SNAP_DIR", "snap")).resolve()
BASE = "https://api.ebay.com/buy/browse/v1"
MARKET_TERMS = [
    "greek key cushion cover", "velvet cushion cover", "black and gold cushion covers",
    "crushed velvet cushion covers", "luxury cushion covers", "diamante cushion covers",
    "moroccan cushion covers", "crushed velvet curtains made to measure", "velvet table runner",
]
MARKET_RESULTS = 50     # listings kept per search
MARKET_DETAIL = 10      # of those, how many to look up for "units sold"
PAUSE = 0.25


def get(url, headers):
    return fe.http(url, headers=headers, missing_ok=True)


def aspects(r):
    out = {}
    for a in r.get("localizedAspects") or []:
        n, v = a.get("name"), a.get("value")
        if n:
            out[n] = v if n not in out else out[n] + ", " + v
    return out


def regions(lst):
    return [x.get("regionName") or x.get("regionId") for x in lst or []]


def record(r, iid):
    ship = r.get("shipToLocations") or {}
    avail = (r.get("estimatedAvailabilities") or [{}])[0]
    loc = r.get("itemLocation") or {}
    img = (r.get("image") or {}).get("imageUrl")
    return {
        "id": iid,
        "title": re.sub(r"\s+", " ", r.get("title", "")).strip(),
        "price": float((r.get("price") or {}).get("value") or 0),
        "currency": (r.get("price") or {}).get("currency"),
        "categoryId": r.get("categoryId"),
        "categoryPath": r.get("categoryPath"),
        "location": ", ".join(x for x in [loc.get("city"), loc.get("stateOrProvince"), loc.get("postalCode"), loc.get("country")] if x),
        "condition": r.get("condition"),
        "itemSpecifics": aspects(r),
        "shipToIncluded": regions(ship.get("regionIncluded")),
        "shipToExcluded": regions(ship.get("regionExcluded")),
        "postage": [{"service": s.get("shippingServiceCode"), "type": s.get("type"),
                     "cost": (s.get("shippingCost") or {}).get("value")} for s in r.get("shippingOptions") or []],
        "available": avail.get("estimatedAvailableQuantity"),
        "sold": avail.get("estimatedSoldQuantity"),
        "availability": avail.get("estimatedAvailabilityStatus"),
        "photoKey": fe.photo_key(img),
        "photoCount": 1 + len(r.get("additionalImages") or []) if img else len(r.get("additionalImages") or []),
        "buyingOptions": r.get("buyingOptions"),
        "returns": (r.get("returnTerms") or {}).get("returnsAccepted"),
        "created": r.get("itemCreationDate"),
        "url": f"https://www.ebay.co.uk/itm/{iid}",
    }


def item(headers, iid):
    """Full details for one listing; listings with options (variations) are read through their item group."""
    r = get(f"{BASE}/item/get_item_by_legacy_id?{urllib.parse.urlencode({'legacy_item_id': iid})}", headers)
    if r and "_error" in r and "11006" in r.get("_body", ""):
        g = get(f"{BASE}/item/get_items_by_item_group?{urllib.parse.urlencode({'item_group_id': iid})}", headers)
        items = (g or {}).get("items") or []
        if not items:
            return None
        rec = record(items[0], iid)
        rec["variations"] = [{"price": float((v.get("price") or {}).get("value") or 0),
                              "specifics": {a["name"]: a["value"] for a in v.get("localizedAspects") or [] if a.get("name")}}
                             for v in items]
        rec["price"] = min(v["price"] for v in rec["variations"])
        rec["description"] = items[0].get("description") or (g.get("commonDescriptions") or [{}])[0].get("description", "")
        return rec
    if not r or "_error" in r:
        return None
    rec = record(r, iid)
    rec["description"] = r.get("description") or ""
    return rec


def save_photo(iid, key):
    if not key:
        return
    pdir = SNAP / "shop/photos"
    pdir.mkdir(parents=True, exist_ok=True)
    keyfile = pdir / f"{iid}.key"
    if keyfile.exists() and keyfile.read_text().strip() == key and (pdir / f"{iid}.jpg").exists():
        return
    try:
        with urllib.request.urlopen(f"https://i.ebayimg.com/images/g/{key}/s-l300.jpg", timeout=30) as r:
            (pdir / f"{iid}.jpg").write_bytes(r.read())
        keyfile.write_text(key)
    except Exception as e:
        print(f"photo for {iid} not saved: {e}")


def shop(headers):
    ids = set(fe.parse(fe.api_pages(headers)))
    ids |= set(fe.previous())                      # anything live at the last website update
    items, gone = {}, []
    for n, iid in enumerate(sorted(ids, reverse=True)):
        rec = item(headers, iid)
        if rec is None or rec.get("availability") == "OUT_OF_STOCK":
            gone.append(iid)
        else:
            items[iid] = rec
        time.sleep(PAUSE)
    if len(items) < fe.MIN_LISTINGS:
        fe.fail(f"only {len(items)} listings could be read")
    ddir = SNAP / "shop/descriptions"
    ddir.mkdir(parents=True, exist_ok=True)
    for iid, rec in items.items():
        (ddir / f"{iid}.html").write_text(rec.pop("description") or "", encoding="utf-8")
        save_photo(iid, rec["photoKey"])
    for f in ddir.glob("*.html"):                  # tidy files of listings that have ended
        if f.stem not in items:
            f.unlink()
    for f in (SNAP / "shop/photos").glob("*.*"):
        if f.stem not in items:
            f.unlink()
    (SNAP / "shop/items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    today = datetime.date.today().isoformat()
    hist = SNAP / "shop/history.tsv"
    lines = [] if hist.exists() else ["date\tid\tprice\tsold\tavailable"]
    lines += [f"{today}\t{i}\t{r['price']:.2f}\t{r['sold'] if r['sold'] is not None else ''}\t{r['available'] if r['available'] is not None else ''}"
              for i, r in sorted(items.items())]
    with open(hist, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"shop: {len(items)} live listings saved; not live / unreadable: {len(gone)} {gone[:20]}")
    return len(items)


def market(headers):
    mdir = SNAP / "market"
    mdir.mkdir(parents=True, exist_ok=True)
    for term in MARKET_TERMS:
        r = get(f"{BASE}/item_summary/search?{urllib.parse.urlencode({'q': term, 'limit': MARKET_RESULTS})}", headers)
        if not r or "_error" in r:
            print(f"market search failed: {term}")
            continue
        res = []
        for it in r.get("itemSummaries") or []:
            iid = it.get("legacyItemId") or (it.get("itemId", "").split("|") + ["", ""])[1]
            res.append({
                "id": iid, "title": it.get("title"), "price": (it.get("price") or {}).get("value"),
                "seller": (it.get("seller") or {}).get("username"),
                "sellerFeedback": (it.get("seller") or {}).get("feedbackPercentage"),
                "postage": [(s.get("shippingCost") or {}).get("value") for s in it.get("shippingOptions") or []],
                "buyingOptions": it.get("buyingOptions"), "photos": 1 + len(it.get("additionalImages") or []),
                "topRated": it.get("topRatedBuyingExperience"), "url": it.get("itemWebUrl", "").split("?")[0],
            })
        for x in [x for x in res if (x["seller"] or "").lower() != fe.SELLER][:MARKET_DETAIL]:
            d = get(f"{BASE}/item/get_item_by_legacy_id?{urllib.parse.urlencode({'legacy_item_id': x['id']})}", headers)
            if d and "_error" not in d:
                a = (d.get("estimatedAvailabilities") or [{}])[0]
                x["sold"] = a.get("estimatedSoldQuantity")
                x["available"] = a.get("estimatedAvailableQuantity")
                x["specifics"] = aspects(d)
            time.sleep(PAUSE)
        slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
        (mdir / f"{slug}.json").write_text(json.dumps({"search": term, "total": r.get("total"), "results": res},
                                                      indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(PAUSE)
    print(f"market: {len(MARKET_TERMS)} searches saved")


def main():
    SNAP.mkdir(parents=True, exist_ok=True)
    headers = fe.api_headers()
    n = shop(headers)
    try:
        market(headers)
    except SystemExit:
        print("market research part failed; shop snapshot still saved")
    (SNAP / "snapshot.json").write_text(json.dumps({
        "taken": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "listings": n, "seller": fe.SELLER}, indent=1), encoding="utf-8")
    readme = SNAP / "README.md"
    if not readme.exists():
        readme.write_text("# Shop data for the weekly checks\n\nWritten automatically every day by "
                          "`scripts/snapshot_ebay.py` on the main branch (read-only eBay data). Don't edit by hand.\n")


if __name__ == "__main__":
    main()
