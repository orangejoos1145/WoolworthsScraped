"""
Woolworths API Deals Scraper - The "All Specials" Edition
---------------------------------------------------------
Uses the backend's native 'SPECIALS' filter to capture every single 
discounted item. Includes Webshare static proxy integration to bypass anti-bot blocks.
"""

import csv
import requests
import urllib3
import random

# Suppress SSL warnings in GitHub Actions logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_CSV = "woolworths_deals.csv"
PAGE_SIZE = 400  # Max batch size permitted by the server
MAX_PAGES = 20   # 20 pages * 400 items = 8,000 max capacity
ONLY_DISCOUNTED = True

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
    }
  }
}
"""

def fetch_page(page_index):
    payload = {
        "operationName": "ProductSearch",
        "variables": {
            "searchInput": {
                "byKeyword": {
                    "pageIndex": page_index,
                    "pageSize": PAGE_SIZE,
                    "value": "",
                    "sortBy": "RELEVANCE",
                    "facetFilters": [],
                    "staticFilters": ["SPECIALS"] 
                }
            }
        },
        "query": QUERY
    }

    # Your 10 dedicated Webshare proxies
    proxy_list = [
        "http://ouswikyu:4luytcyxhn0o@31.59.20.176:6754",
        "http://ouswikyu:4luytcyxhn0o@45.38.107.97:6014",
        "http://ouswikyu:4luytcyxhn0o@198.105.121.200:6462",
        "http://ouswikyu:4luytcyxhn0o@64.137.96.74:6641",
        "http://ouswikyu:4luytcyxhn0o@198.23.243.226:6361",
        "http://ouswikyu:4luytcyxhn0o@38.154.185.97:6370",
        "http://ouswikyu:4luytcyxhn0o@84.247.60.125:6095",
        "http://ouswikyu:4luytcyxhn0o@142.111.67.146:5611",
        "http://ouswikyu:4luytcyxhn0o@191.96.254.138:6185",
        "http://ouswikyu:4luytcyxhn0o@31.58.9.4:6077"
    ]

    # Randomly select a proxy for this specific request
    proxy_url = random.choice(proxy_list)
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    print(f"Requesting page {page_index} (batch of {PAGE_SIZE}) using proxy {proxy_url.split('@')[1]}...")
    
    try:
        response = requests.post(
            GRAPHQL_URL, 
            headers=HEADERS, 
            json=payload, 
            proxies=proxies, 
            verify=False, 
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"Server rejected the request (Status {response.status_code}).")
            return None

        data = response.json()
        if "errors" in data:
            print("GraphQL Error:", data["errors"])
            return None
            
        return data.get("data", {}).get("My", {}).get("products", {})

    except requests.exceptions.Timeout:
        print("Error: Webshare proxy connection timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None

def main():
    all_deals = []
    seen_skus = set()
    
    for page in range(0, MAX_PAGES):
        product_data = fetch_page(page)
        if not product_data:
            break
            
        results = product_data.get("results", [])
        if not results:
            print("No more results found.")
            break
            
        for item in results:
            if "productName" not in item:
                continue
                
            sku = item.get("sku", "UNKNOWN")
            if sku in seen_skus:
                continue
            seen_skus.add(sku)
            
            title = item.get("productName", "").strip()
            slug = item.get("slug", "")
            link = f"https://www.woolworths.co.nz/shop/product-details/{slug}" if slug else ""
            
            variants = item.get("variants")
            if not isinstance(variants, list) or len(variants) == 0:
                continue
                
            price_info = variants[0].get("variantPrice")
            if not isinstance(price_info, dict):
                price_info = {}
                
            sale_price = price_info.get("sellingPrice")
            old_price = price_info.get("wasPrice")
            
            promo_note = ""
            tags = item.get("tags")
            
            if isinstance(tags, list) and len(tags) > 0:
                tag_item = tags[0]
                if isinstance(tag_item, dict):
                    content = tag_item.get("content")
                    if isinstance(content, dict):
                        strap = content.get("strap")
                        roundel = content.get("roundel")
                        
                        if isinstance(strap, list) and len(strap) > 0:
                            strap = strap[0]
                        if isinstance(strap, dict) and strap.get("label"):
                            promo_note = strap.get("label").strip()
                            
                        if not promo_note:
                            if isinstance(roundel, list) and len(roundel) > 0:
                                roundel = roundel[0]
                            if isinstance(roundel, dict) and roundel.get("alt"):
                                promo_note = roundel.get("alt").strip()
            
            is_discounted = bool(old_price and sale_price and old_price > sale_price)
            if ONLY_DISCOUNTED and not is_discounted and not promo_note:
                continue
                
            discount_pct = ""
            if is_discounted:
                saved_pct = price_info.get("savedPercentage")
                if saved_pct:
                    discount_pct = round(saved_pct, 1)
                else:
                    discount_pct = round((old_price - sale_price) / old_price * 100, 1)
            
            all_deals.append({
                "Title": title,
                "Old Price": old_price if old_price else "",
                "Discounted Price": sale_price,
                "Discount %": discount_pct,
                "Link": link,
                "Promo Note": promo_note
            })

        print(f" -> Processed {len(results)} items. Kept {len(all_deals)} unique deals total.")
        
        total_pages = product_data.get("totalPages", 1)
        if page + 1 >= total_pages:
            print("Reached the final page of specials.")
            break

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Title", "Old Price", "Discounted Price", "Discount %", "Link", "Promo Note"]
        )
        writer.writeheader()
        writer.writerows(all_deals)

    print(f"\nDone! Saved {len(all_deals)} unique specials to {OUTPUT_CSV}.")

if __name__ == "__main__":
    main()
