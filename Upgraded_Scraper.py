"""
Woolworths API Deals Scraper - The "All Specials" Edition
---------------------------------------------------------
Uses the backend's native 'SPECIALS' filter to capture every single 
discounted item. Automatically fetches live Webshare proxies via API 
and rotates through them to bypass blocks.
"""

import csv
import requests
import urllib3
import random

# Suppress SSL warnings in GitHub Actions logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_CSV = "woolworths_deals.csv"
PAGE_SIZE = 400  
MAX_PAGES = 20   
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

    # Fetch live proxies automatically using your Webshare API Token
    api_token = "o1bcyv81lheoev6cpdszzk8bn7a0cioeho2xpso5"
    api_url = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=20"
    
    proxy_list = []
    try:
        ws_response = requests.get(api_url, headers={"Authorization": f"Token {api_token}"}, timeout=10)
        if ws_response.status_code == 200:
            for p in ws_response.json().get("results", []):
                if p.get("valid"):
                    proxy_list.append(f"http://{p['username']}:{p['password']}@{p['proxy_address']}:{p['port']}")
    except Exception as e:
        print(f"Could not fetch proxies from Webshare API: {e}")

    # Fallback just in case the API fails
    if not proxy_list:
        print("Error: Proxy list is empty. Check your Webshare API token.")
        return None

    # Shuffle the list so it tries them in a random order
    random.shuffle(proxy_list)

    # Retry loop: try all fetched proxies before giving up on this page
    for attempt, proxy_url in enumerate(proxy_list, start=1):
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        ip_port = proxy_url.split('@')[1]
        print(f"Requesting page {page_index} (Attempt {attempt}/{len(proxy_list)}) using proxy {ip_port}...")
        
        try:
            response = requests.post(
                GRAPHQL_URL, 
                headers=HEADERS, 
                json=payload, 
                proxies=proxies, 
                verify=False, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    print("GraphQL Error:", data["errors"])
                    return None
                return data.get("data", {}).get("My", {}).get("products", {})
            else:
                print(f" -> Failed with Status {response.status_code}. Trying next proxy...")

        except requests.exceptions.Timeout:
            print(" -> Proxy timed out. Trying next proxy...")
        except requests.exceptions.RequestException as e:
            print(" -> Connection error. Trying next proxy...")

    print("All proxies failed for this page.")
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
