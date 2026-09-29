"""
Woolworths API Deals Scraper - The "All Specials" Edition
---------------------------------------------------------
Uses the backend's native 'SPECIALS' filter to capture discounted items.

Woolworths caps any single search at 1,000 results. When there are more
specials than that, this scraper splits the search into smaller groups
(departments if possible, otherwise brands - each under the cap), then
merges and de-duplicates by SKU. It works out the filter format itself by
testing it against a known brand count, and falls back to one capped
search (printing Woolworths' own error message) if nothing works.

Runs two passes - SPECIALS and MEMBER_PRICE - so Everyday Rewards member
prices are included too. The member price comes from the product's
"MemberPrice" tag (decisionInputs.promotionalPrice, in cents); the regular
sellingPrice is the non-member price.

Also records each product's real Woolworths category path (Department >
Aisle > Shelf, from categoryHierarchyNames) so the site can organise
products exactly the way woolworths.co.nz does.
"""

import csv
import json
import time
import requests

# --- CONFIGURATION ---
OUTPUT_CSV = "woolworths_deals.csv"
PAGE_SIZE = 400        # Max batch size permitted by the server
MAX_PAGES = 20         # safety cap per search
RESULT_CAP = 1000      # Woolworths returns at most this many results per search
REQUEST_PAUSE_S = 0.2  # small pause between requests, easier on their servers
MIN_COVERAGE = 0.9     # a split must cover 90%+ of all specials to be used
ONLY_DISCOUNTED = True
STATIC_FILTERS = ["SPECIALS", "MEMBER_PRICE"]   # passes to run, in order

GRAPHQL_URL = "https://www.woolworths.co.nz/api/graphql?op-name=ProductSearch"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "wnzx-operation-name": "ProductSearch"
}

QUERY = """
query ProductSearch($searchInput: CompositeSearchInput!) {
  My {
    products(searchInput: $searchInput) {
      results {
        ... on ProductSummary {
          sku
          productName
          slug
          brand
          __CATEGORY_FIELDS__
          variants {
            variantPrice {
              sellingPrice
              wasPrice
              savedPercentage
              isSpecial
              isClubPrice
            }
          }
          tags {
            kind
            type
            userSegmentId
            decisionInputs
            content {
              strap { label }
              roundel { alt }
            }
          }
        }
      }
      totalCount
      totalPages
      currentPage
      filterOptions {
        title
        options {
          key value title count
          children {
            key value title count
            children { key value title count }
          }
        }
      }
    }
  }
}
"""


CATEGORY_FIELDS = "categoryHierarchyNames { lvl0 lvl1 lvl2 lvl3 }"
USE_CATEGORIES = True   # switched off automatically if the API ever rejects the field
LAST_ERROR = ""


def fetch_page(page_index, facet_filters=None, quiet=False, static_filter="SPECIALS"):
    global LAST_ERROR, USE_CATEGORIES
    payload = {
        "operationName": "ProductSearch",
        "variables": {
            "searchInput": {
                "byKeyword": {
                    "pageIndex": page_index,
                    "pageSize": PAGE_SIZE,
                    "value": "",
                    "sortBy": "RELEVANCE",
                    "facetFilters": facet_filters or [],
                    "staticFilters": [static_filter]
                }
            }
        },
        "query": QUERY.replace("__CATEGORY_FIELDS__", CATEGORY_FIELDS if USE_CATEGORIES else "")
    }

    time.sleep(REQUEST_PAUSE_S)
    try:
        response = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=60)
    except requests.RequestException as e:
        LAST_ERROR = f"Network error: {e}"
        if not quiet:
            print(f"  {LAST_ERROR}")
        return None

    if response.status_code != 200 and USE_CATEGORIES and "categoryHierarchyNames" in response.text:
        print("  (Woolworths rejected the category field - continuing without categories)")
        USE_CATEGORIES = False
        return fetch_page(page_index, facet_filters, quiet, static_filter)
    if response.status_code != 200:
        LAST_ERROR = f"Status {response.status_code}: {response.text[:400]}"
        if not quiet:
            print(f"  Server rejected the request ({LAST_ERROR})")
        return None

    data = response.json()
    if "errors" in data and USE_CATEGORIES and "categoryHierarchyNames" in json.dumps(data["errors"]):
        # Category field not accepted - carry on without categories rather than fail.
        print("  (Woolworths rejected the category field - continuing without categories)")
        USE_CATEGORIES = False
        return fetch_page(page_index, facet_filters, quiet, static_filter)
    if "errors" in data:
        LAST_ERROR = "GraphQL Error: " + json.dumps(data["errors"])[:400]
        if not quiet:
            print(f"  {LAST_ERROR}")
        return None

    return (data.get("data") or {}).get("My", {}).get("products", {})


def _tag_text(tag):
    """Strap label or roundel alt text from one tag, if any."""
    content = tag.get("content") if isinstance(tag, dict) else None
    if not isinstance(content, dict):
        return ""
    strap = content.get("strap")
    roundel = content.get("roundel")
    if isinstance(strap, list) and strap:
        strap = strap[0]
    if isinstance(strap, dict) and strap.get("label"):
        return strap["label"].strip()
    if isinstance(roundel, list) and roundel:
        roundel = roundel[0]
    if isinstance(roundel, dict) and roundel.get("alt"):
        return roundel["alt"].strip()
    return ""


def _member_price(tags):
    """Member (Everyday Rewards) price in dollars from the MemberPrice tag, or None."""
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        is_member = tag.get("type") == "MemberPrice" or "rewards" in str(tag.get("userSegmentId") or "").lower()
        inputs = tag.get("decisionInputs")
        if is_member and isinstance(inputs, dict):
            cents = inputs.get("promotionalPrice")
            if isinstance(cents, (int, float)) and cents > 0:
                return round(cents / 100, 2)
    return None


SKIP_CATEGORY_NAMES = {"all departments", "specials", "all", ""}


def category_path(item):
    """Woolworths category path as [Department, Aisle, Shelf], from
    categoryHierarchyNames. Handles plain names, lists, and 'A > B > C' paths."""
    names = item.get("categoryHierarchyNames")
    if not isinstance(names, dict):
        return []
    levels = []
    for key in ("lvl0", "lvl1", "lvl2", "lvl3"):
        v = names.get(key)
        if isinstance(v, list):
            v = v[0] if v else None
        if isinstance(v, str) and v.strip():
            levels.append(v.strip())
    # Some systems store each level as the full path ("Pantry > Oil"): use the deepest.
    full = [lv for lv in levels if " > " in lv]
    parts = max(full, key=lambda x: x.count(" > ")).split(" > ") if full else levels
    return [p.strip() for p in parts if p.strip().lower() not in SKIP_CATEGORY_NAMES][:3]


def parse_item(item):
    """Turn one API product into a CSV row dict, or None to skip it."""
    if "productName" not in item:
        return None

    sku = item.get("sku", "UNKNOWN")
    title = item.get("productName", "").strip()
    slug = item.get("slug", "")
    link = f"https://www.woolworths.co.nz/shop/product-details/{sku}/{slug}" if slug else ""

    variants = item.get("variants")
    if not isinstance(variants, list) or len(variants) == 0:
        return None

    price_info = variants[0].get("variantPrice")
    if not isinstance(price_info, dict):
        price_info = {}

    sale_price = price_info.get("sellingPrice")
    old_price = price_info.get("wasPrice")

    tags = item.get("tags") if isinstance(item.get("tags"), list) else []

    # Promo label: first tag as before; if that's empty, the first price-promotion tag.
    promo_note = _tag_text(tags[0]) if tags else ""
    if not promo_note:
        for tag in tags:
            if isinstance(tag, dict) and tag.get("kind") == "PricePromotion" and _tag_text(tag):
                promo_note = _tag_text(tag)
                break

    # Everyday Rewards member price: member price is the deal, the regular
    # sellingPrice is what non-members pay.
    member_price = _member_price(tags)
    is_rewards = member_price is not None
    if is_rewards and (sale_price is None or member_price < sale_price):
        old_price = sale_price
        sale_price = member_price
        if not promo_note:
            promo_note = "Member Price"

    # Discount Math verification
    is_discounted = bool(old_price and sale_price and old_price > sale_price)
    if ONLY_DISCOUNTED and not is_discounted and not promo_note:
        return None

    discount_pct = ""
    if is_discounted:
        # Always calculate manually to avoid Woolworths API errors
        discount_pct = round(((old_price - sale_price) / old_price) * 100, 1)

    path = category_path(item) + ["", "", ""]

    return {
        "sku": sku,
        "Department": path[0],
        "Aisle": path[1],
        "Shelf": path[2],
        "Title": title,
        "Old Price": old_price if old_price else "",
        "Discounted Price": sale_price,
        "Discount %": discount_pct,
        "Link": link,
        "Promo Note": promo_note,
        "Everyday Rewards": "Yes" if is_rewards else "No",
    }


def scrape_search(label, facet_filters, all_deals, seen_skus, first_page=None, warn_cap=True, static_filter="SPECIALS"):
    """Page through one search (all specials, or one department)."""
    print(f"\n{label}")
    fetched = 0
    for page in range(0, MAX_PAGES):
        product_data = first_page if (page == 0 and first_page is not None) else fetch_page(page, facet_filters, static_filter=static_filter)
        if not product_data:
            break

        results = product_data.get("results") or []
        if not results:
            break
        fetched += len(results)

        for item in results:
            row = parse_item(item)
            if row and row["sku"] not in seen_skus:
                seen_skus.add(row["sku"])
                all_deals.append(row)

        print(f"  page {page}: {len(results)} items | {len(all_deals)} unique deals so far")

        if page + 1 >= (product_data.get("totalPages") or 1):
            break

    if warn_cap and fetched >= RESULT_CAP - 5:
        print(f"  !! Got ~{RESULT_CAP} results - this search probably hit Woolworths' cap and is missing items.")
    return fetched


def facet_filters(option):
    # Woolworths wants a nested list: [[{key, value}]] - each inner list is an
    # OR-group, the outer list ANDs them. Confirmed from its own error messages.
    return [[{"key": option["key"], "value": option["value"]}]]


def facet_works(option, overall_total, static_filter="SPECIALS"):
    """Check a filter really narrows the search, using an option with a known count."""
    data = fetch_page(0, facet_filters(option), quiet=True, static_filter=static_filter)
    if data is None:
        print(f"  Test on '{option.get('value')}' rejected - {LAST_ERROR[:200]}")
        return False
    count = data.get("totalCount")
    print(f"  Test on '{option.get('value')}': {count} results (expected ~{option.get('count')})")
    return isinstance(count, int) and 0 < count < overall_total


def leaf_options(options):
    """Walk the category tree down until each group is under the cap."""
    out = []
    for o in options or []:
        kids = o.get("children") or []
        if (o.get("count") or 0) > RESULT_CAP and kids:
            out.extend(leaf_options(kids))
        else:
            out.append(o)
    return out


def candidate_splits(filter_options, overall_total):
    """Ways to split the search, best first: departments, then brands.
    Only splits whose groups cover (almost) all specials are returned."""
    groups = [((g.get("title") or "").lower(), g.get("options") or []) for g in filter_options or []]
    candidates = []
    for title, opts in groups:
        if any(w in title for w in ("categor", "department", "aisle")):
            candidates.append((f"department ({title})", leaf_options(opts)))
    for title, opts in groups:
        if "brand" in title:
            candidates.append(("brand", opts))

    usable_splits = []
    for label, opts in candidates:
        usable = [o for o in opts if o.get("key") and o.get("value")]
        covered = sum(min(o.get("count") or 0, RESULT_CAP) for o in usable)
        ok = usable and covered >= MIN_COVERAGE * overall_total
        print(f"  Split by {label}: {len(usable)} groups covering ~{covered} of {overall_total}"
              + ("" if ok else " - not enough, skipping"))
        if ok:
            usable_splits.append((label, usable))
    return usable_splits


def scrape_filter(static_filter, all_deals, seen_skus):
    """Scrape everything for one static filter (SPECIALS or MEMBER_PRICE),
    splitting past the 1,000 cap. Returns Woolworths' reported total, or None."""
    print(f"\n========== {static_filter} ==========")
    first = fetch_page(0, static_filter=static_filter)
    if not first:
        print(f"Couldn't fetch {static_filter}.")
        return None

    overall_total = first.get("totalCount") or 0
    print(f"Woolworths reports {overall_total} products for {static_filter}.")

    if overall_total <= RESULT_CAP:
        scrape_search("All (under the cap, one search is enough)", [], all_deals, seen_skus,
                      first_page=first, static_filter=static_filter)
        return overall_total

    filter_options = first.get("filterOptions") or []
    print(f"More than {RESULT_CAP} - looking for a way to split the search...")

    split_label, groups, build = None, None, None
    for label, opts in candidate_splits(filter_options, overall_total):
        test = max(opts, key=lambda o: o.get("count") or 0)
        print(f"Trying split by {label}:")
        if facet_works(test, overall_total, static_filter=static_filter):
            split_label, groups, build = label, opts, facet_filters
            print(f"Split by {label} works. Scraping {len(groups)} groups...")
            break

    if build:
        # One unfiltered pass first, to catch products that belong to no group.
        scrape_search("All (first 1,000)", [], all_deals, seen_skus, first_page=first,
                      warn_cap=False, static_filter=static_filter)
        for i, opt in enumerate(groups, 1):
            name = opt.get('value') if split_label == "brand" else (opt.get('title') or opt.get('value'))
            label = f"[{i}/{len(groups)}] {name} ({opt.get('count', '?')} items)"
            scrape_search(label, build(opt), all_deals, seen_skus, static_filter=static_filter)
    else:
        print("\n!! Couldn't split the search - falling back to one capped search.")
        print("   Send everything below this line to Claude so it can be fixed:")
        print("   LAST_ERROR = " + LAST_ERROR[:600])
        cats = [g for g in filter_options if "brand" not in (g.get("title") or "").lower()]
        print("   OTHER_FILTERS = " + json.dumps(cats)[:3000])
        scrape_search("All (capped at 1,000)", [], all_deals, seen_skus, first_page=first,
                      static_filter=static_filter)
    return overall_total


def main():
    all_deals = []
    seen_skus = set()
    started = time.time()
    totals = {}

    for static_filter in STATIC_FILTERS:
        totals[static_filter] = scrape_filter(static_filter, all_deals, seen_skus)

    if totals.get("SPECIALS") is None:
        print("\nCouldn't reach Woolworths for specials - no CSV written, previous file kept.")
        return

    # Write to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Title", "Old Price", "Discounted Price", "Discount %", "Link", "Promo Note",
                           "Everyday Rewards", "Department", "Aisle", "Shelf"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(all_deals)

    rewards = sum(1 for d in all_deals if d["Everyday Rewards"] == "Yes")
    with_dept = [d for d in all_deals if d["Department"]]
    if with_dept:
        ex = with_dept[0]
        print(f"\nCategories: {len(with_dept)} of {len(all_deals)} deals have a department "
              f"(e.g. {' > '.join(x for x in (ex['Department'], ex['Aisle'], ex['Shelf']) if x)}).")
    else:
        print("\nCategories: none found - the site will fall back to keyword categories.")
    mins = round((time.time() - started) / 60, 1)
    reported = ", ".join(f"{k}: {v}" for k, v in totals.items())
    print(f"\nDone in {mins} min! Saved {len(all_deals)} unique deals to {OUTPUT_CSV} "
          f"({rewards} with Everyday Rewards member prices). Woolworths reported {reported}.")


if __name__ == "__main__":
    main()
