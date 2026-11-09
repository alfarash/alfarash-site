# Al Farash Home Decor website

The website at www.alfarash.co.uk, built from the shop's live eBay listings.

## How it updates

Every morning GitHub runs **Update website from eBay** (`.github/workflows/update-site.yml`):

1. `scripts/fetch_ebay.py` reads the shop's live listings through eBay's official API and saves them to `data/live.tsv`.
2. `build.py` turns them into the website (`designs/noir.html` + `shared.js`).
3. The result is published to GitHub Pages.

New eBay listings appear on the site and ended ones disappear on their own, usually by the next morning.
To update straight away: **Actions** tab > **Update website from eBay** > **Run workflow**.

If eBay can't be read, the run fails, GitHub emails you, and the website stays as it was.

## Files

| File | What it is |
|---|---|
| `data/live.tsv` | The live listings (written automatically, don't edit) |
| `data/categories.txt` | Which website section each listing sits in, checked by eye. New listings are sorted by their title until added here. |
| `data/colours.txt` | Main and detail colour of each listing, checked by eye. Same fallback. |
| `data/sizes.txt` | Cushion size in inches. Same fallback. |
| `data/titles_ebay.txt` | Old search words kept so visitors can still find a cushion by its old name |
| `data/all.txt` | The original listing list, kept for its old titles |
| `build.py`, `shared.js`, `designs/noir.html` | The website itself |

## eBay keys

Stored as repository secrets `EBAY_CLIENT_ID` (App ID) and `EBAY_CLIENT_SECRET` (Cert ID) under
Settings > Secrets and variables > Actions. Never put them in a file here: this repository is public.
