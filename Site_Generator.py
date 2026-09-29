"""
Woolworths Deals Filterer - Restricted Content & Full Categories v5
-------------------------------------------------------------------
Implements strict content filtering to drop alcohol, tobacco, and 
restricted personal care items, while mapping all final Woolworths categories.
"""

import csv
import json
import os
from datetime import datetime

INPUT_CSV = "woolworths_deals.csv"
OUTPUT_HTML = "index.html"

def load_rows():
    if not os.path.exists(INPUT_CSV):
        print(f"No {INPUT_CSV} found — run your scraper first.")
        raise SystemExit(1)

    rows = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            old_price = row.get("Old Price") or ""
            sale_price = row.get("Discounted Price") or ""
            discount_pct = row.get("Discount %") or ""

            try:
                old_price = float(old_price) if old_price != "" else None
            except ValueError:
                old_price = None
            try:
                sale_price = float(sale_price) if sale_price != "" else None
            except ValueError:
                sale_price = None
            try:
                discount_pct = float(discount_pct) if discount_pct != "" else None
            except ValueError:
                discount_pct = None

            rows.append({
                "title": row.get("Title", "").strip(),
                "old_price": old_price,
                "sale_price": sale_price,
                "discount_pct": discount_pct,
                "link": row.get("Link", "").strip(),
                "promo": row.get("Promo Note", "").strip(),
                "rewards": (row.get("Everyday Rewards") or "").strip().lower() == "yes",
                "dept": (row.get("Department") or "").strip(),
                "aisle": (row.get("Aisle") or "").strip(),
            })
    return rows

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Woolies Premium Deals</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+CiAgPGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJnIiB4MT0iMCIgeTE9IjAiIHgyPSIxIiB5Mj0iMSI+PHN0b3Agb2Zmc2V0PSIwIiBzdG9wLWNvbG9yPSIjMTZjMjhhIi8+PHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjMGU5ZjZlIi8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+CiAgPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTUiIGZpbGw9InVybCgjZykiLz4KICA8cGF0aCBkPSJNMzMuNSAxMUg1MGEzIDMgMCAwIDEgMyAzdjE2LjVhMyAzIDAgMCAxLS45IDIuMUwzMi42IDUyLjFhMyAzIDAgMCAxLTQuMiAwTDExLjkgMzUuNmEzIDMgMCAwIDEgMC00LjJMMzEuNCAxMS45QTMgMyAwIDAgMSAzMy41IDExeiIgZmlsbD0iI2ZmZiIvPgogIDxjaXJjbGUgY3g9IjQ0LjUiIGN5PSIxOS41IiByPSIzLjYiIGZpbGw9IiMwZTlmNmUiLz4KICA8ZyBmaWxsPSIjMGU5ZjZlIiB0cmFuc2Zvcm09InJvdGF0ZSgtNDUgMzIgMzQpIj4KICAgIDxjaXJjbGUgY3g9IjI2LjUiIGN5PSIyOS41IiByPSIzLjEiLz48Y2lyY2xlIGN4PSIzNy41IiBjeT0iMzguNSIgcj0iMy4xIi8+CiAgICA8cmVjdCB4PSIzMC45IiB5PSIyNCIgd2lkdGg9IjIuNiIgaGVpZ2h0PSIyMCIgcng9IjEuMyIgdHJhbnNmb3JtPSJyb3RhdGUoMzUgMzIuMiAzNCkiLz4KICA8L2c+Cjwvc3ZnPgo=">
<link rel="icon" type="image/png" sizes="32x32" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAEvElEQVR4nJxXa2wUVRT+7uy2a6umWWgLWAhgoI1IeSSlTYwJJkjSRMAqxthaHpKYYEKiiYl/wKSoxBoT4g8lGhsjsWD6g1IjhIbVNlWUlsVHgm0tSCNp2tp22wW2UtruzuXMzM7rzsw+ev+cuXPm3HO+891z7h0/hFHU+eF+EtWcYz0DyjjnfpIgCVXKJJk2hz7X9aTgskxzZuo5j9NsgOQ10rdP7njvpNUf0x+W/PJxsTyXaCKTneDJl+YihhNNp0vtG1Pv1In2JNvi0vyBOzsao0YASzo+2iaDnyYAxdzdyEROEsw+1xA7kNvtrSCAIZ7gddEXj12SlJnM5NfBuOEc7kZw6GWk1nvbr2ASDqkZKOxsfIWi+DYt8sw5T4Xcvh5HLW0wfpBbOPOMnJubRtf7OMPuko1YmRfUF7AJ/SE8NYSO8Rvq1LY+cNBPk1U6Ak/kTEes6xkClMPWyr2oDK5AJqP+yilcGO0np8k9Q5mjhVdJEtjSbDkPMF9WzpWxoWCZWhSMW9aHvFSSOQ9ARJ5U6+/BzQxozvd4Oh++dxs1F0+gtOVdNP19yXjPhfRrdLCAlJJzwSiA9MhbbobROTKAsZm7aPyzHfNyQn0vbkQ9KsmB3JZ+buE8NXJ9lC9abjyXFhQjR/IBAnKYVQB/5pzvyYjz7SVPIPTcW+idGkXN6k02nRW57ldaKOeXxwZRcfaYaxCVRavxWtlTCObm2xVMWJ9eSVan2XCe58/BjTvj+Hd6EhkPl2qTFsr5uuBj6nd90RFkNJIAxX4j2SJLcp5DTeaMB/LBuxOqzKXNtaagCL3RUXX+Rf9PWNtyBMevhVz9T8xOu1abJHKuyNqSTahycf5S6HNsbv0AB7pOqvMnKQt9UyOYTcRxONyG8ZkYjv52DtPxWZtd9+QtNA+GhT6gBSGJ7VcZ4egQEsYBoY3o7D10UH0r48fhftxPzKs09BIFAZ8fu1ZuVHVKFTziD9ic7+5qwpwcd6k26H2A2eq0LzaGV6+eRlzhJDmCgXy8sW6r+vxm+TY85MuhDCzDddqIc9RsPnu6DueqD+GrZ/YbNj3k/IWuLzFDwYrI9T3HCi8c5V43mWeL1qJ5Sy01CwluYzAWweYz7+PnXe9gw6ISm05xXkPOFXqs/QW2IGB2QuMktUT4w/h1OsXsmbCOxx8tRL4/11EJonMncrc+kPxIrNOQGsQpzyDq11Rh+cNBT+f29eG8rCw+38ABpL3JbC8mOqrqPenwQu5+UzLvkJIXcgiZCY1RJrqbPTORGrl5a3bvAy7IIRydXA/i8jeOILLhXNxz1Ad4jzdyJ2cX/xtA/a9mENlyLmSmx5dXt7WClBVukdtvv5pUFr35/ySuRG7hHyrDt38/64nczrkmjWpT1+PnWeF3DRUyS3TTO59bnTLOkz9Dlj4B7jhYrHY2e/WAM20MBecJxqUtUuT5hqv0WZMb5w7OXM7zbDk318ent/cd/0OtgnkmHSER8eRM9u4Tdk7Tcq4FI/PhQN6c4lMrw9jOhkjCFy+lz9rMe/tCkHOBcxfk4N8zGesnXj4xDVj+jvWxuPXwPvpRraYVymlaRhZ+t40Fi/M0nFPB8AF6/xfVTXts7ydfW/09AAAA//8x1Z6eAAAABklEQVQDAOPssJtRSEgIAAAAAElFTkSuQmCC">
<link rel="apple-touch-icon" sizes="180x180" href="data:image/png;base64,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">
<meta name="theme-color" content="#10b981">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: #10b981;
    --primary-dark: #059669;
    --primary-glow: rgba(16, 185, 129, 0.2);
    --bg-color: #0c1017;
    --bg-gradient: linear-gradient(135deg, #0c1017 0%, #111823 100%);
    --card-bg: #141b26;
    --card-border: rgba(255, 255, 255, 0.1);
    --card-border-hover: rgba(16, 185, 129, 0.4);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --danger: #ef4444;
    --rewards: #fb923c;
    --rewards-bg: rgba(251, 146, 60, 0.14);
    --rewards-border: rgba(251, 146, 60, 0.4);
    --rewards-switch: #f97316;
    --danger-glow: rgba(239, 68, 68, 0.15);
    --accent-light: rgba(16, 185, 129, 0.1);
    --header-bg: rgba(12, 16, 23, 0.85);
    --shadow-md: 0 4px 20px 0 rgba(0, 0, 0, 0.5);
    --input-bg: rgba(255, 255, 255, 0.08);
    --input-border: rgba(255, 255, 255, 0.2);
  }

  [data-theme="light"] {
    --primary: #178841;
    --primary-dark: #126b33;
    --primary-glow: rgba(23, 136, 65, 0.2);
    --bg-color: #f4f6f8;
    --bg-gradient: linear-gradient(135deg, #f4f6f8 0%, #e2e8f0 100%);
    --card-bg: #ffffff;
    --card-border: rgba(0, 0, 0, 0.1);
    --card-border-hover: rgba(23, 136, 65, 0.4);
    --text-main: #0f172a;
    --text-muted: #64748b;
    --danger: #dc2626;
    --rewards: #c2410c;
    --rewards-bg: rgba(234, 88, 12, 0.1);
    --rewards-border: rgba(234, 88, 12, 0.35);
    --rewards-switch: #ea580c;
    --danger-glow: rgba(220, 38, 38, 0.1);
    --accent-light: #eaf7ec;
    --header-bg: rgba(255, 255, 255, 0.85);
    --shadow-md: 0 4px 20px 0 rgba(31, 38, 135, 0.05);
    --input-bg: rgba(0, 0, 0, 0.05);
    --input-border: rgba(0, 0, 0, 0.15);
  }

  * { box-sizing: border-box; font-family: 'Poppins', sans-serif; -webkit-tap-highlight-color: transparent; }
  body { 
    margin: 0; background: var(--bg-gradient); color: var(--text-main); 
    display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden;
    transition: background 0.4s ease;
  }

  header {
    background: var(--header-bg); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--card-border); padding: 1rem 2rem;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 50; gap: 1rem;
    transition: background 0.4s ease;
  }
  #brandReset { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; border-radius: 8px; transition: opacity 0.2s, transform 0.2s; }
  #brandReset:hover { opacity: 0.8; }
  #brandReset:active { transform: scale(0.97); }
  .header-brand { font-size: 1.3rem; font-weight: 800; display: flex; align-items: center; gap: 8px; color: var(--primary); letter-spacing: 0.5px; }
  
  .header-search { flex: 1; max-width: 500px; position: relative; }
  .header-search input {
    width: 100%; padding: 0.7rem 1.2rem 0.7rem 2.6rem; border: 1px solid var(--input-border); 
    border-radius: 99px; font-size: 0.95rem; outline: none; background: var(--input-bg); 
    color: var(--text-main); transition: all 0.3s;
  }
  .header-search input:focus { border-color: var(--primary); box-shadow: 0 0 12px var(--primary-glow); background: var(--card-bg); }
  [data-theme="dark"] .header-search input { background: rgba(0,0,0,0.3); }
  [data-theme="dark"] .header-search input:focus { background: rgba(0,0,0,0.5); }
  .header-search i { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--text-muted); font-size: 0.95rem; }

  .header-controls { display: flex; align-items: center; gap: 1rem; }
  .timestamp-badge { background: var(--accent-light); border: 1px solid var(--primary-glow); padding: 5px 12px; border-radius: 99px; font-size: 0.75rem; color: var(--primary); display: flex; align-items: center; gap: 6px; font-weight: 600; white-space: nowrap; }
  .theme-toggle { background: var(--card-bg); border: 1px solid var(--card-border); color: var(--text-main); width: 38px; height: 38px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; transition: all 0.3s ease; }
  .theme-toggle:hover { background: var(--primary); color: white; border-color: var(--primary); box-shadow: 0 0 10px var(--primary-glow); }
  .mobile-menu-btn { display: none; background: transparent; border: none; color: var(--text-main); font-size: 1.4rem; cursor: pointer; padding: 5px; }

  .container { display: flex; max-width: 1500px; margin: 1.5rem auto; padding: 0 1.5rem; gap: 2rem; flex: 1; width: 100%; position: relative; }

  .sidebar { width: 280px; flex-shrink: 0; background: var(--card-bg); border-radius: 12px; padding: 1.5rem; box-shadow: var(--shadow-md); border: 1px solid var(--card-border); align-self: flex-start; position: sticky; top: 90px; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.4s ease;
    /* Fits the screen and scrolls on its own, so every category is reachable
       while the sidebar is stuck in place. Scrolling past its end carries on
       scrolling the page. */
    max-height: calc(100vh - 110px); overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--input-border) transparent; }
  .sidebar::-webkit-scrollbar { width: 6px; }
  .sidebar::-webkit-scrollbar-thumb { background: var(--input-border); border-radius: 99px; }
  .sidebar::-webkit-scrollbar-track { background: transparent; }
  .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.8rem; }
  .sidebar-header h2 { margin: 0; font-size: 1.1rem; font-weight: 600; }
  
  .filter-group { margin-bottom: 1.5rem; }
  .filter-group label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.6rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
  .then-by { margin-top: 0.8rem; padding-left: 0.8rem; border-left: 2px solid var(--primary-glow); animation: thenByIn 0.25s ease; }
  .then-by[hidden] { display: none; }
  .then-by label i { font-size: 0.7rem; margin-right: 4px; color: var(--primary); }
  @keyframes thenByIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
  .filter-group select { width: 100%; padding: 0.7rem; border: 1px solid var(--input-border); border-radius: 8px; font-size: 0.9rem; background: var(--input-bg); color: var(--text-main); outline: none; }
  [data-theme="dark"] .filter-group select { background: rgba(0,0,0,0.3); }

  .toggle-container { display: flex; align-items: center; justify-content: space-between; background: var(--input-bg); padding: 10px 14px; border-radius: 10px; border: 1px solid var(--input-border); }
  [data-theme="dark"] .toggle-container { background: rgba(0,0,0,0.3); }
  .toggle-container span { font-size: 0.85rem; font-weight: 600; color: var(--text-main); }
  .switch { position: relative; display: inline-block; width: 42px; height: 24px; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--input-border); transition: .4s; border-radius: 34px; }
  .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
  input:checked + .slider { background-color: var(--primary); }
  input:checked + .slider:before { transform: translateX(20px); background-color: white; }

  input[type=range] { -webkit-appearance: none; width: 100%; background: transparent; margin-top: 5px; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 18px; width: 18px; border-radius: 50%; background: var(--primary); cursor: pointer; margin-top: -6px; box-shadow: 0 0 10px var(--primary-glow); }
  input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 6px; cursor: pointer; background: var(--input-border); border-radius: 3px; }

  .category-nav details { margin-bottom: 0.4rem; }
  .category-nav summary, .category-nav li { font-weight: 600; padding: 0.7rem 0.9rem; cursor: pointer; border-radius: 8px; transition: all 0.2s; list-style: none; display: flex; align-items: center; gap: 10px; color: var(--text-main); font-size: 0.9rem; }
  .category-nav summary::-webkit-details-marker { display: none; }
  .category-nav summary i.cat-icon { font-size: 1rem; color: var(--primary); width: 20px; text-align: center; }
  .category-nav summary .arrow { margin-left: auto; font-size: 0.75rem; color: var(--text-muted); transition: transform 0.3s; }
  .category-nav details[open] summary .arrow { transform: rotate(180deg); }
  
  .category-nav summary:hover, .category-nav li:hover { background: var(--input-bg); }
  .category-nav summary.active, .category-nav li.active { background: var(--accent-light); border: 1px solid var(--primary-glow); color: var(--primary); }
  .category-nav ul { list-style: none; padding: 0; margin: 0.3rem 0 0.3rem 1.2rem; border-left: 2px solid var(--input-border); }
  .category-nav li { padding: 0.5rem 0.9rem; font-size: 0.85rem; color: var(--text-muted); }
  .category-nav .cat-name { flex: 1; min-width: 0; }
  .category-nav .cat-count { font-size: 0.7rem; font-weight: 600; color: var(--text-muted); background: var(--input-bg); border: 1px solid var(--input-border); padding: 1px 7px; border-radius: 99px; flex-shrink: 0; }
  .category-nav summary .arrow { margin-left: 0; }
  .card-cat { font-size: 0.72rem; color: var(--text-muted); margin-top: -0.4rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .results-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 0.5rem; padding-bottom: 0.8rem; border-bottom: 1px solid var(--card-border); flex-wrap: wrap; gap: 1rem; }
  .results-title-group h2 { margin: 0 0 4px 0; font-size: 1.4rem; font-weight: 700; color: var(--primary); }
  .results-title-group span { color: var(--text-muted); font-size: 0.85rem; font-weight: 600; }
  .results-controls { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
  .per-page-selector { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: var(--text-muted); font-weight: 600; }
  .per-page-selector select { padding: 4px 8px; border-radius: 6px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-main); font-weight: 600; outline: none; cursor: pointer; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem; }
  
  .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: 0.8rem; opacity: 0; transform: translateY(15px); transition: opacity 0.4s ease, transform 0.4s ease, border-color 0.3s ease, background 0.4s ease; }
  .card.show { opacity: 1; transform: translateY(0); }
  .card:hover { border-color: var(--card-border-hover); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
  .card-top { display: flex; gap: 0.8rem; align-items: flex-start; }
  .card-icon-wrapper { width: 50px; height: 50px; flex-shrink: 0; background: var(--input-bg); border: 1px solid var(--input-border); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: var(--primary); font-size: 1.4rem; }
  .card-badges { display: flex; flex-direction: column; gap: 0.4rem; flex: 1; align-items: flex-start; }
  .badge-promo { background: var(--accent-light); color: var(--primary-dark); padding: 3px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: 700; border: 1px solid var(--primary-glow); display: inline-flex; align-items: center; gap: 4px; }
  [data-theme="dark"] .badge-promo { color: var(--primary); }
  .badge-rewards { background: var(--rewards-bg); color: var(--rewards); padding: 3px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: 700; border: 1px solid var(--rewards-border); display: inline-flex; align-items: center; gap: 4px; }
  .price-note { font-size: 0.7rem; font-weight: 600; color: var(--rewards); margin-top: 2px; }
  #showRewards:checked + .slider { background-color: var(--rewards-switch); }
  .badge-discount { background: var(--danger-glow); color: var(--danger); padding: 3px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: 700; border: 1px solid rgba(239, 68, 68, 0.3); display: inline-flex; align-items: center; gap: 4px; }
  .card h3 { font-size: 0.95rem; margin: 0; line-height: 1.3; color: var(--text-main); font-weight: 700; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .price-box { margin-top: auto; padding-top: 0.6rem; border-top: 1px dashed var(--input-border); display: flex; flex-direction: column; }
  .price-sale { font-size: 1.6rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; line-height: 1; }
  .price-old { font-size: 0.8rem; color: var(--text-muted); text-decoration: line-through; margin-top: 2px; }
  .btn-view { text-align: center; text-decoration: none; background: var(--input-bg); color: var(--text-main); border: 1px solid var(--card-border); padding: 0.6rem; border-radius: 6px; font-weight: 600; transition: all 0.2s; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 0.2rem; text-transform: uppercase; }
  .btn-view:hover { background: var(--card-border-hover); border-color: var(--primary); color: white; }
  [data-theme="light"] .btn-view:hover { color: white; }

  .pagination-container { display: flex; justify-content: center; margin: 1rem 0; }
  .pagination { display: flex; justify-content: center; gap: 0.4rem; flex-wrap: wrap; }
  .page-btn { background: var(--card-bg); border: 1px solid var(--card-border); padding: 0.5rem 0.9rem; border-radius: 6px; cursor: pointer; color: var(--text-main); font-weight: 600; font-size: 0.85rem; transition: all 0.2s; }
  .page-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
  .page-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
  .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .mobile-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 80; backdrop-filter: blur(4px); opacity: 0; transition: opacity 0.3s; }
  .mobile-overlay.show { display: block; opacity: 1; }
  #emptyState { text-align: center; padding: 4rem 1rem; color: var(--text-muted); display: none; background: var(--input-bg); border-radius: 12px; border: 1px dashed var(--card-border); margin-top: 1rem; }
  #emptyState i { font-size: 3rem; color: var(--input-border); margin-bottom: 1rem; }

  @media (max-width: 900px) {
    header { padding: 1rem; flex-wrap: wrap; }
    .header-controls { order: 2; }
    .header-search { order: 3; width: 100%; max-width: 100%; margin: 0.5rem 0 0 0; }
    .mobile-menu-btn { display: block; }
    .timestamp-badge { display: none; }
    .container { margin: 1rem auto; padding: 0 1rem; }
    .sidebar { position: fixed; top: 0; left: 0; height: 100vh; z-index: 100; width: 85%; max-width: 300px; border-radius: 0; margin: 0; overflow-y: auto; padding: 2rem 1.5rem; transform: translateX(-105%); max-height: none; overscroll-behavior: contain; }
    .sidebar.open { transform: translateX(0); }
    .sidebar-close-btn { display: block !important; background: none; border: none; color: var(--text-main); font-size: 1.5rem; cursor: pointer; }
    .grid { grid-template-columns: 1fr; } 
  }
  .sidebar-close-btn { display: none; }
</style>
</head>
<body>

<header>
  <div class="header-brand">
    <button class="mobile-menu-btn" id="mobileMenuBtn"><i class="fa-solid fa-bars-staggered"></i></button>
    <span id="brandReset" title="Back to all deals">
      <i class="fa-solid fa-apple-whole"></i> Woolies
    </span>
  </div>
  
  <div class="header-search">
    <i class="fa-solid fa-search"></i>
    <input type="text" id="searchInput" placeholder="Search products, brands, cuts...">
  </div>

  <div class="header-controls">
    <div class="timestamp-badge">
      <i class="fa-solid fa-clock-rotate-left"></i> __TIMESTAMP__
    </div>
    <button id="themeToggle" class="theme-toggle" aria-label="Toggle Dark/Light Mode">
      <i class="fa-solid fa-sun"></i>
    </button>
  </div>
</header>

<div class="mobile-overlay" id="mobileOverlay"></div>

<div class="container">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <h2><i class="fa-solid fa-sliders"></i> Filters</h2>
      <button class="sidebar-close-btn" id="closeSidebarBtn"><i class="fa-solid fa-xmark"></i></button>
    </div>

    <div class="filter-group toggle-group">
      <div class="toggle-container">
        <span>Hide No-Discount</span>
        <label class="switch">
          <input type="checkbox" id="hideNoDiscount" checked>
          <span class="slider"></span>
        </label>
      </div>
    </div>

    <div class="filter-group toggle-group">
      <div class="toggle-container">
        <span>Everyday Rewards Prices</span>
        <label class="switch">
          <input type="checkbox" id="showRewards" checked>
          <span class="slider"></span>
        </label>
      </div>
    </div>

    <div class="filter-group">
      <label>Sort By</label>
      <select id="sortSelect">
        <option value="discount_desc" selected>Biggest Discount (%)</option>
        <option value="price_asc">Lowest Price</option>
        <option value="price_desc">Highest Price</option>
        <option value="title_asc">Name (A-Z)</option>
      </select>
      <div class="then-by" id="thenByWrap">
        <label for="thenBySelect"><i class="fa-solid fa-arrow-turn-up fa-rotate-90"></i> Then By</label>
        <select id="thenBySelect"></select>
      </div>
    </div>

    <div class="filter-group">
      <label>Min Discount: <span id="minVal" style="color:var(--primary); font-size:1rem;">0%</span></label>
      <input type="range" id="minDiscount" min="0" max="80" step="5" value="0">
    </div>

    <div class="filter-group">
      <label>Categories</label>
      <div class="category-nav" id="categoryNav">
        <!-- JS Injected -->
      </div>
    </div>
  </aside>

  <main>
    <div class="results-header">
      <div class="results-title-group">
        <h2 id="resultsHeading">All Deals</h2>
        <span id="resultCount">0 items</span>
      </div>
      <div class="results-controls">
        <div class="per-page-selector">
          <label for="perPageSelect">Per page:</label>
          <select id="perPageSelect">
            <option value="10">10</option>
            <option value="25" selected>25</option>
            <option value="50">50</option>
            <option value="75">75</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </div>
        <div class="pagination" id="paginationTop"></div>
      </div>
    </div>
    
    <div class="grid" id="grid"></div>
    
    <div id="emptyState">
      <i class="fa-solid fa-box-open"></i>
      <h3 style="font-size: 1.2rem; margin:0 0 8px 0;">No matching deals</h3>
      <p style="font-size: 0.85rem;">Adjust your filters, toggle off 'Hide No-Discount', or search something else.</p>
    </div>

    <div class="pagination-container">
      <div class="pagination" id="paginationBottom"></div>
    </div>
  </main>
</div>

<script>
  // ----------------------------------------------------
  // RESTRICTED CONTENT FILTER
  // Automatically drops items matching these keywords
  // ----------------------------------------------------
  // Whole-word matching, so "La Gina", "Extra Virgin", "Original", "Crumpets"
  // and "Drumsticks" aren't caught by "gin"/"rum".
  const RESTRICTED_RE = /\\b(wines?|beers?|vodka|whiske?y|rum|gin|ciders?|bourbon|liquor|tequila|cigarettes?|tobacco|vapes?|smoking|condoms?|lubricants?|pregnancy|period|tampons?|pads?)\\b/i;

  // Only load deals that DO NOT contain restricted words in their title
  const RAW_DEALS = __DEALS_JSON__;
  const RESTRICTED_DEPT_RE = /beer|wine|liquor|spirits|tobacco/i;
  const DEALS = RAW_DEALS.filter(d => !RESTRICTED_RE.test(d.title) && !RESTRICTED_DEPT_RE.test(d.dept || ""));

  // Theme Toggle
  let isDark = true;
  const themeToggle = document.getElementById('themeToggle');
  themeToggle.addEventListener('click', () => {
    isDark = !isDark;
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    themeToggle.innerHTML = isDark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
  });

  // Mobile Sidebar
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mobileOverlay');
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const closeBtn = document.getElementById('closeSidebarBtn');

  function openSidebar() { sidebar.classList.add('open'); overlay.classList.add('show'); document.body.style.overflow = 'hidden'; }
  function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('show'); document.body.style.overflow = ''; }
  mobileBtn.addEventListener('click', openSidebar);
  closeBtn.addEventListener('click', closeSidebar);
  overlay.addEventListener('click', closeSidebar);

  // Animations
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('show');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: "0px 0px 50px 0px" });

  const grid = document.getElementById('grid');
  const emptyState = document.getElementById('emptyState');
  const searchInput = document.getElementById('searchInput');
  const sortSelect = document.getElementById('sortSelect');
  const minDiscount = document.getElementById('minDiscount');
  const hideNoDiscount = document.getElementById('hideNoDiscount');
  const minVal = document.getElementById('minVal');
  const resultCount = document.getElementById('resultCount');
  const resultsHeading = document.getElementById('resultsHeading');
  const paginationTop = document.getElementById('paginationTop');
  const paginationBottom = document.getElementById('paginationBottom');
  const categoryNav = document.getElementById('categoryNav');
  const perPageSelect = document.getElementById('perPageSelect');

  let filteredData = [];
  let currentPage = 1;
  let itemsPerPage = parseInt(perPageSelect.value);
  let activeCategoryKeywords = [];
  let activeCategoryName = "All Deals";
  // Real Woolworths categories (from the scraper). Falls back to keyword
  // categories below if the CSV has no Department column.
  const HAS_REAL_CATS = DEALS.some(d => d.dept);
  let activeDept = null;
  let activeAisle = null;

  perPageSelect.addEventListener('change', (e) => {
    itemsPerPage = parseInt(e.target.value);
    currentPage = 1; 
    renderGrid();
  });

  // Fully Mapped Woolworths Categories
  const categories = [
    { name: 'Dinner', icon: 'fa-utensils', keys: ['meal', 'dinner', 'heat', 'salad'],
      sub: [
        { name: 'Ready Meals', keys: ['ready meal', 'prepared'] },
        { name: 'Heat & Eat', keys: ['heat', 'pie', 'quiche'] },
        { name: 'Sides & Salads', keys: ['side', 'salad', 'slaw'] },
        { name: 'Desserts', keys: ['dessert', 'pudding'] }
      ]
    },
    { name: 'Fruit & Veg', icon: 'fa-carrot', keys: ['fruit', 'veg', 'apple', 'banana', 'carrot', 'tomato', 'potato', 'onion', 'berries', 'floral', 'herb'],
      sub: [
        { name: 'Fruit', keys: ['fruit', 'apple', 'banana', 'berry', 'citrus'] },
        { name: 'Vegetables', keys: ['veg', 'carrot', 'potato', 'onion', 'broccoli'] },
        { name: 'Prepared Fruit & Veg', keys: ['prepared', 'cut'] },
        { name: 'Fresh Salad & Herbs', keys: ['salad', 'herb', 'parsley', 'basil'] },
        { name: 'Organic', keys: ['organic'] },
        { name: 'The Odd Bunch', keys: ['odd bunch'] },
        { name: 'Floral', keys: ['flower', 'floral', 'bouquet'] }
      ]
    },
    { name: 'Meat & Poultry', icon: 'fa-drumstick-bite', keys: ['beef', 'chicken', 'lamb', 'pork', 'venison', 'mince', 'sausage', 'meat', 'poultry'],
      sub: [
        { name: 'Beef', keys: ['beef', 'steak'] },
        { name: 'Chicken & Poultry', keys: ['chicken', 'poultry', 'turkey'] },
        { name: 'Lamb', keys: ['lamb'] },
        { name: 'Pork', keys: ['pork', 'bacon'] },
        { name: 'Venison & Game', keys: ['venison', 'game'] },
        { name: 'Mince & Patties', keys: ['mince', 'pattie', 'burger'] },
        { name: 'Sausages', keys: ['sausage', 'saveloy'] },
        { name: 'BBQ & Roast', keys: ['bbq', 'roast'] },
        { name: 'Offal & Bones', keys: ['offal', 'bone', 'liver'] },
        { name: 'Plant Based', keys: ['plant based', 'vegan', 'vegetarian'] }
      ]
    },
    { name: 'Fish & Seafood', icon: 'fa-fish-fins', keys: ['fish', 'seafood', 'salmon', 'prawn', 'tuna'],
      sub: [
        { name: 'Fish', keys: ['fish'] },
        { name: 'Salmon', keys: ['salmon'] },
        { name: 'Prawns & Seafood', keys: ['prawn', 'seafood', 'mussel', 'squid'] }
      ]
    },
    { name: 'Fridge & Deli', icon: 'fa-cheese', keys: ['cheese', 'milk', 'yoghurt', 'butter', 'deli', 'salami', 'egg', 'cream', 'juice'],
      sub: [
        { name: 'Eggs, Butter & Spreads', keys: ['egg', 'butter', 'margarine', 'spread'] },
        { name: 'Milk', keys: ['milk'] },
        { name: 'Cheese', keys: ['cheese', 'brie', 'cheddar'] },
        { name: 'Yoghurt & Desserts', keys: ['yoghurt', 'dessert'] },
        { name: 'Cream & Custard', keys: ['cream', 'custard'] },
        { name: 'Juice & Drinks', keys: ['juice', 'drink'] },
        { name: 'Deli Meats & Seafood', keys: ['deli', 'salami', 'ham'] },
        { name: 'Pasta, Pizza & Pastry', keys: ['pasta', 'pizza', 'pastry'] },
        { name: 'Dips, Hummus & Nibbles', keys: ['dip', 'hummus', 'nibble', 'pate'] }
      ]
    },
    { name: 'Bakery', icon: 'fa-bread-slice', keys: ['bread', 'wrap', 'roll', 'croissant', 'bagel', 'muffin', 'cake', 'pastry'],
      sub: [
        { name: 'Sliced & Packaged Bread', keys: ['bread', 'loaf', 'sliced'] },
        { name: 'Buns, Rolls & Sticks', keys: ['bun', 'roll', 'stick'] },
        { name: 'Wraps, Pita & Pizza Bases', keys: ['wrap', 'pita', 'pizza base'] },
        { name: 'Pastries, Croissants', keys: ['pastry', 'croissant', 'danish'] },
        { name: 'Cakes, Muffins & Desserts', keys: ['cake', 'muffin', 'dessert', 'tart'] },
        { name: 'Bagels, Crumpets', keys: ['bagel', 'crumpet', 'pancake'] }
      ]
    },
    { name: 'Frozen', icon: 'fa-snowflake', keys: ['frozen', 'ice cream', 'pizza', 'chips', 'sorbet'],
      sub: [
        { name: 'Frozen Vegetables', keys: ['frozen veg', 'pea', 'corn'] },
        { name: 'Frozen Meat & Seafood', keys: ['frozen meat', 'frozen fish', 'frozen prawn'] },
        { name: 'Frozen Meals & Snacks', keys: ['frozen meal', 'chip', 'wedge', 'snack'] },
        { name: 'Ice Cream & Sorbet', keys: ['ice cream', 'sorbet', 'gelato'] },
        { name: 'Pizza, Pastry & Bread', keys: ['frozen pizza', 'frozen pastry'] }
      ]
    },
    { name: 'Pantry', icon: 'fa-jar', keys: ['sauce', 'cereal', 'pasta', 'rice', 'spread', 'can', 'snack', 'sweet', 'biscuit'],
      sub: [
        { name: 'Snacks & Sweets', keys: ['snack', 'sweet', 'chip', 'nut'] },
        { name: 'Biscuits & Crackers', keys: ['biscuit', 'cracker', 'cookie'] },
        { name: 'Tinned Foods & Packets', keys: ['tin', 'can', 'packet'] },
        { name: 'Baking', keys: ['baking', 'flour', 'sugar', 'mix'] },
        { name: 'Cereals & Spreads', keys: ['cereal', 'oat', 'spread', 'jam', 'peanut butter'] },
        { name: 'Sauces & Pastes', keys: ['sauce', 'paste', 'mayo', 'ketchup'] },
        { name: 'Pasta, Noodles & Grains', keys: ['pasta', 'noodle', 'rice', 'grain'] },
        { name: 'Herbs, Spices & Stock', keys: ['herb', 'spice', 'stock', 'salt', 'pepper'] },
        { name: 'Oil, Vinegar & Condiments', keys: ['oil', 'vinegar', 'condiment', 'dressing'] },
        { name: 'International Foods', keys: ['international', 'asian', 'indian', 'mexican'] },
        { name: 'Meal Kits', keys: ['meal kit'] }
      ]
    },
    { name: 'Drinks', icon: 'fa-bottle-water', keys: ['drink', 'water', 'juice', 'coke', 'soda', 'coffee', 'tea'],
      sub: [
        { name: 'Coffee', keys: ['coffee', 'bean', 'capsule', 'instant'] },
        { name: 'Tea & Milk Drinks', keys: ['tea', 'milk drink', 'milo'] },
        { name: 'Soft Drinks', keys: ['soft drink', 'coke', 'lemonade', 'soda'] },
        { name: 'Sports & Energy', keys: ['sport', 'energy', 'red bull', 'powerade'] },
        { name: 'Juice, Cordial & Water', keys: ['juice', 'cordial', 'water', 'sparkling'] }
      ]
    },
    { name: 'Health & Body', icon: 'fa-pump-soap', keys: ['shampoo', 'soap', 'clean', 'spray', 'wash', 'toothpaste', 'deodorant', 'skin'],
      sub: [
        { name: 'Bath, Shower & Soap', keys: ['bath', 'shower', 'soap', 'body wash'] },
        { name: 'Hair Care', keys: ['hair', 'shampoo', 'conditioner'] },
        { name: 'Dental & Oral Care', keys: ['dental', 'tooth', 'mouthwash'] },
        { name: 'Deodorant & Body Sprays', keys: ['deodorant', 'spray', 'antiperspirant'] },
        { name: 'Skin Care & Sun Care', keys: ['skin', 'sun', 'lotion', 'cream'] },
        { name: 'Shaving & Hair Removal', keys: ['shave', 'razor'] },
        { name: 'Medical, Vitamins & First Aid', keys: ['medical', 'vitamin', 'supplement', 'first aid', 'plaster'] }
      ]
    },
    { name: 'Household', icon: 'fa-broom', keys: ['clean', 'spray', 'wash', 'toilet', 'laundry', 'kitchen', 'bathroom'],
      sub: [
        { name: 'Bathroom & Toilet', keys: ['bathroom', 'toilet', 'tissue'] },
        { name: 'Kitchen', keys: ['kitchen', 'foil', 'wrap', 'bin liner'] },
        { name: 'Laundry', keys: ['laundry', 'powder', 'liquid', 'softener'] },
        { name: 'Cleaning', keys: ['cleaning', 'spray', 'wipe', 'sponge'] },
        { name: 'Pest Control', keys: ['pest', 'insect', 'fly'] },
        { name: 'Hardware & Auto', keys: ['hardware', 'auto', 'battery', 'lightbulb'] }
      ]
    },
    { name: 'Baby & Child', icon: 'fa-baby-carriage', keys: ['baby', 'child', 'nappy', 'diaper', 'wipe', 'formula'],
      sub: [
        { name: 'Nappies & Wipes', keys: ['nappy', 'diaper', 'wipe'] },
        { name: 'Baby Food & Formula', keys: ['baby food', 'formula', 'pouch'] },
        { name: 'Bottles, Toys & Accessories', keys: ['bottle', 'toy', 'dummy', 'pacifier'] }
      ]
    }
  ];

  function getIconForTitle(title) {
    const t = title.toLowerCase();
    if (t.includes('beef') || t.includes('steak') || t.includes('mince')) return 'fa-cow';
    if (t.includes('chicken') || t.includes('poultry')) return 'fa-drumstick-bite';
    if (t.includes('lamb') || t.includes('pork') || t.includes('sausage') || t.includes('bacon')) return 'fa-bacon';
    if (t.includes('fish') || t.includes('salmon') || t.includes('tuna') || t.includes('seafood')) return 'fa-fish';
    if (t.includes('milk') || t.includes('cheese') || t.includes('butter') || t.includes('yoghurt')) return 'fa-cheese';
    if (t.includes('chocolate') || t.includes('candy') || t.includes('sweet') || t.includes('lolly')) return 'fa-candy-cane';
    if (t.includes('bread') || t.includes('wrap') || t.includes('roll')) return 'fa-bread-slice';
    if (t.includes('apple') || t.includes('banana') || t.includes('fruit')) return 'fa-apple-whole';
    if (t.includes('veg') || t.includes('carrot') || t.includes('potato') || t.includes('onion') || t.includes('lentil')) return 'fa-carrot';
    if (t.includes('water') || t.includes('drink') || t.includes('juice') || t.includes('coke') || t.includes('soda')) return 'fa-bottle-water';
    if (t.includes('ice cream') || t.includes('frozen')) return 'fa-ice-cream';
    if (t.includes('coffee') || t.includes('tea')) return 'fa-mug-hot';
    if (t.includes('pizza')) return 'fa-pizza-slice';
    if (t.includes('can') || t.includes('sauce') || t.includes('spread') || t.includes('pasta')) return 'fa-jar';
    if (t.includes('nappy') || t.includes('diaper') || t.includes('baby')) return 'fa-baby-carriage';
    if (t.includes('clean') || t.includes('spray') || t.includes('laundry')) return 'fa-broom';
    return 'fa-basket-shopping';
  }

  function deptIcon(name) {
    const n = name.toLowerCase();
    const rules = [['frozen','fa-snowflake'],['fruit','fa-apple-whole'],['veg','fa-carrot'],['meat','fa-drumstick-bite'],
      ['seafood','fa-fish'],['fridge','fa-cheese'],['deli','fa-cheese'],['dairy','fa-cheese'],['egg','fa-egg'],['bakery','fa-bread-slice'],
      ['pantry','fa-jar'],['snack','fa-cookie-bite'],['drink','fa-bottle-water'],['health','fa-pump-soap'],['beauty','fa-pump-soap'],
      ['household','fa-broom'],['cleaning','fa-broom'],['baby','fa-baby-carriage'],['pet','fa-paw'],['kitchen','fa-kitchen-set']];
    for (const [k, icon] of rules) if (n.includes(k)) return icon;
    return 'fa-basket-shopping';
  }

  function initRealCategories() {
    const tree = new Map();
    DEALS.forEach(d => {
      if (!d.dept) return;
      if (!tree.has(d.dept)) tree.set(d.dept, { count: 0, aisles: new Map() });
      const node = tree.get(d.dept);
      node.count++;
      if (d.aisle) node.aisles.set(d.aisle, (node.aisles.get(d.aisle) || 0) + 1);
    });
    let html = '';
    [...tree.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([dept, node]) => {
      const aisles = [...node.aisles.entries()].sort((a, b) => a[0].localeCompare(b[0]));
      html += `<details>
                 <summary data-dept="${escapeHtml(dept)}" class="${aisles.length ? '' : 'no-sub'}">
                   <i class="fa-solid ${deptIcon(dept)} cat-icon"></i>
                   <span class="cat-name">${escapeHtml(dept)}</span>
                   <span class="cat-count">${node.count}</span>
                   ${aisles.length ? '<i class="fa-solid fa-chevron-down arrow"></i>' : ''}
                 </summary>`;
      if (aisles.length) {
        html += '<ul>' + aisles.map(([aisle, n]) =>
          `<li data-dept="${escapeHtml(dept)}" data-aisle="${escapeHtml(aisle)}"><span class="cat-name">${escapeHtml(aisle)}</span><span class="cat-count">${n}</span></li>`
        ).join('') + '</ul>';
      }
      html += '</details>';
    });
    categoryNav.innerHTML = html;
  }

  categoryNav.addEventListener('click', (event) => {
    const el = event.target.closest('[data-dept]');
    if (!el || !HAS_REAL_CATS) return;
    event.preventDefault();
    event.stopPropagation();
    const dept = el.dataset.dept;
    const aisle = el.dataset.aisle || null;
    const detailsEl = el.closest('details');
    const same = activeDept === dept && activeAisle === aisle;

    document.querySelectorAll('.category-nav li, .category-nav summary').forEach(x => x.classList.remove('active'));
    if (same) {
      activeDept = null; activeAisle = null; activeCategoryName = "All Deals";
      if (!aisle && detailsEl) detailsEl.removeAttribute('open');
    } else {
      activeDept = dept; activeAisle = aisle;
      activeCategoryName = aisle ? `${dept} › ${aisle}` : dept;
      el.classList.add('active');
      searchInput.value = '';
      document.querySelectorAll('.category-nav details').forEach(d => { if (d !== detailsEl) d.removeAttribute('open'); });
      if (detailsEl) detailsEl.setAttribute('open', '');
    }
    if (window.innerWidth <= 900 && (aisle || same)) closeSidebar();
    applyFilters();
  });

  function initCategories() {
    if (HAS_REAL_CATS) { initRealCategories(); return; }
    let html = '';
    categories.forEach((cat) => {
      const keys = cat.keys.join(',');
      if (cat.sub) {
        html += `<details>
                   <summary onclick="toggleCategory('${cat.name}', '${keys}', this, event)">
                     <i class="fa-solid ${cat.icon} cat-icon"></i> ${cat.name} <i class="fa-solid fa-chevron-down arrow"></i>
                   </summary>
                   <ul>`;
        cat.sub.forEach(sub => {
          html += `<li onclick="toggleCategory('${sub.name}', '${sub.keys.join(',')}', this, event)">${sub.name}</li>`;
        });
        html += `</ul></details>`;
      } else {
        html += `<details>
                   <summary onclick="toggleCategory('${cat.name}', '${keys}', this, event)" class="no-sub">
                     <i class="fa-solid ${cat.icon} cat-icon"></i> ${cat.name}
                   </summary>
                 </details>`;
      }
    });
    categoryNav.innerHTML = html;
  }

  window.toggleCategory = function(name, keysString, element, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const isSummary = element.tagName.toLowerCase() === 'summary';
    const detailsEl = isSummary ? element.parentElement : element.closest('details');

    if (activeCategoryName === name) {
        element.classList.remove('active');
        activeCategoryName = "All Deals";
        activeCategoryKeywords = [];
        if (detailsEl) detailsEl.removeAttribute('open');
    } else {
        document.querySelectorAll('.category-nav li, .category-nav summary').forEach(el => el.classList.remove('active'));
        element.classList.add('active');
        activeCategoryName = name;
        activeCategoryKeywords = keysString.split(',');
        searchInput.value = ''; 

        document.querySelectorAll('.category-nav details').forEach(d => {
            if (d !== detailsEl) d.removeAttribute('open');
        });
        if (detailsEl) detailsEl.setAttribute('open', '');
    }

    if (window.innerWidth <= 900) closeSidebar();
    applyFilters();
  };

  function formatPrice(p) { return p ? '$' + p.toFixed(2) : ''; }
  function escapeHtml(str) { return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  // ---- Sorting: primary + "Then By" (only options that make sense) ----
  const byNum = (v, missing) => (typeof v === 'number' && !isNaN(v)) ? v : missing;
  const SORTS = {
    discount_desc: { label: 'Biggest Discount (%)', cmp: (a, b) => byNum(b.discount_pct, 0) - byNum(a.discount_pct, 0) },
    price_asc:     { label: 'Lowest Price',         cmp: (a, b) => byNum(a.sale_price, Infinity) - byNum(b.sale_price, Infinity) || 0 },
    price_desc:    { label: 'Highest Price',        cmp: (a, b) => byNum(b.sale_price, -Infinity) - byNum(a.sale_price, -Infinity) || 0 },
    title_asc:     { label: 'Name (A-Z)',           cmp: (a, b) => a.title.localeCompare(b.title) },
  };
  // Name ties almost never happen, so it gets no second sort. A price sort
  // doesn't offer the other price direction (it would do nothing).
  const THEN_BY = {
    discount_desc: ['price_asc', 'price_desc', 'title_asc'],
    price_asc:     ['discount_desc', 'title_asc'],
    price_desc:    ['discount_desc', 'title_asc'],
    title_asc:     [],
  };
  const THEN_BY_DEFAULT = { discount_desc: 'price_asc', price_asc: 'discount_desc', price_desc: 'discount_desc' };
  const thenBySelect = document.getElementById('thenBySelect');
  const thenByWrap = document.getElementById('thenByWrap');

  function updateThenBy(forceDefault) {
    const options = THEN_BY[sortSelect.value] || [];
    if (!options.length) { thenByWrap.hidden = true; thenBySelect.innerHTML = ''; return; }
    const keep = !forceDefault && options.includes(thenBySelect.value) ? thenBySelect.value : THEN_BY_DEFAULT[sortSelect.value];
    thenBySelect.innerHTML = options.map(o => `<option value="${o}">${SORTS[o].label}</option>`).join('');
    thenBySelect.value = keep;
    thenByWrap.hidden = false;
  }

  function applyFilters() {
    const q = searchInput.value.trim().toLowerCase();
    const minPct = Number(minDiscount.value);
    const hideNoDisc = hideNoDiscount.checked;
    
    minVal.textContent = minPct + '%';
    if (q) resultsHeading.innerHTML = `Search: "${q}"`;
    else resultsHeading.innerHTML = activeCategoryName;

    filteredData = DEALS.filter(d => {
      if (d.rewards && !showRewards.checked) return false;
      const pct = d.discount_pct || 0;
      if (hideNoDisc && pct <= 0) return false;
      if (pct < minPct) return false;
      
      const title = d.title.toLowerCase();
      if (q && !title.includes(q)) return false;
      if (!q && activeDept) {
        if (d.dept !== activeDept) return false;
        if (activeAisle && d.aisle !== activeAisle) return false;
      }
      if (!q && activeCategoryKeywords.length > 0) {
        if (!activeCategoryKeywords.some(kw => title.includes(kw))) return false;
      }
      return true;
    });

    const primary = SORTS[sortSelect.value] || SORTS.discount_desc;
    const secondary = thenBySelect.value ? SORTS[thenBySelect.value] : null;
    filteredData.sort((a, b) =>
      primary.cmp(a, b) || (secondary ? secondary.cmp(a, b) : 0) || a.title.localeCompare(b.title));

    currentPage = 1;
    renderGrid();
  }

  function renderGrid() {
    resultCount.textContent = `${filteredData.length} items`;
    grid.innerHTML = '';
    
    if (filteredData.length === 0) {
      emptyState.style.display = 'block';
      paginationTop.innerHTML = '';
      paginationBottom.innerHTML = '';
      return;
    }
    emptyState.style.display = 'none';

    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedItems = filteredData.slice(startIndex, startIndex + itemsPerPage);
    const frag = document.createDocumentFragment();

    paginatedItems.forEach(d => {
      const card = document.createElement('div');
      card.className = 'card';

      let badges = '';
      let promoText = d.promo || "";
      const promoLower = promoText.toLowerCase();
      
      if (promoLower.includes("half price") || promoLower.startsWith("save ") || promoLower.startsWith("save\\n")) {
          promoText = "";
      }

      if (d.rewards && /rewards|club|member/i.test(promoText)) promoText = "";

      if (d.discount_pct || promoText || d.rewards) {
        badges += `<div class="card-badges">`;
        if (d.rewards) badges += `<span class="badge-rewards"><i class="fa-solid fa-id-card"></i> Everyday Rewards</span>`;
        if (promoText) badges += `<span class="badge-promo"><i class="fa-solid fa-star"></i> ${escapeHtml(promoText)}</span>`;
        if (d.discount_pct) badges += `<span class="badge-discount"><i class="fa-solid fa-tag"></i> ${d.discount_pct}% OFF</span>`;
        badges += `</div>`;
      }
      
      const iconClass = getIconForTitle(d.title);

      card.innerHTML = `
        <div class="card-top">
          <div class="card-icon-wrapper">
            <i class="fa-solid ${iconClass}"></i>
          </div>
          ${badges}
        </div>
        <h3>${escapeHtml(d.title)}</h3>
        ${d.aisle || d.dept ? `<div class="card-cat">${escapeHtml(d.aisle || d.dept)}</div>` : ''}
        <div class="price-box">
          <span class="price-sale">${formatPrice(d.sale_price)}</span>
          ${d.rewards ? `<span class="price-note">With Everyday Rewards card</span>` : ''}
          ${d.old_price ? `<span class="price-old">${formatPrice(d.old_price)}</span>` : ''}
        </div>
        <a class="btn-view" href="${escapeHtml(d.link)}" target="_blank">
          <i class="fa-solid fa-cart-shopping"></i> VIEW DEAL
        </a>
      `;
      frag.appendChild(card);
      observer.observe(card);
    });
    
    grid.appendChild(frag);
    renderPagination();
  }

  function generatePaginationButtons(totalPages) {
    let html = '';
    
    const prevDisabled = currentPage === 1 ? 'disabled' : '';
    html += `<button class="page-btn" ${prevDisabled} onclick="changePage(${currentPage - 1})"><i class="fa-solid fa-chevron-left"></i></button>`;

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 3);
    if (endPage - startPage < 3) startPage = Math.max(1, endPage - 3);

    for (let i = startPage; i <= endPage; i++) {
      const activeClass = i === currentPage ? 'active' : '';
      html += `<button class="page-btn ${activeClass}" onclick="changePage(${i})">${i}</button>`;
    }

    const nextDisabled = currentPage === totalPages ? 'disabled' : '';
    html += `<button class="page-btn" ${nextDisabled} onclick="changePage(${currentPage + 1})"><i class="fa-solid fa-chevron-right"></i></button>`;
    
    return html;
  }

  function renderPagination() {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    if (totalPages <= 1) {
        paginationTop.innerHTML = '';
        paginationBottom.innerHTML = '';
        return;
    }
    const html = generatePaginationButtons(totalPages);
    paginationTop.innerHTML = html;
    paginationBottom.innerHTML = html;
  }

  window.changePage = function(page) {
      currentPage = page;
      renderGrid();
      window.scrollTo({top: 0, behavior: 'smooth'});
  };

  searchInput.addEventListener('input', () => { 
    if(activeCategoryKeywords.length > 0 || activeDept) {
       activeCategoryKeywords = [];
       activeDept = null; activeAisle = null;
       activeCategoryName = "Search Results";
       document.querySelectorAll('.category-nav li, .category-nav summary').forEach(el => el.classList.remove('active'));
    }
    applyFilters(); 
  });
  sortSelect.addEventListener('change', () => { updateThenBy(false); applyFilters(); });
  thenBySelect.addEventListener('change', applyFilters);
  minDiscount.addEventListener('input', applyFilters);
  hideNoDiscount.addEventListener('change', applyFilters);
  const showRewards = document.getElementById('showRewards');
  showRewards.addEventListener('change', applyFilters);

  // Clicking the logo puts everything back to how the site first loads.
  function resetAll() {
    searchInput.value = '';
    activeDept = null; activeAisle = null;
    activeCategoryKeywords = []; activeCategoryName = "All Deals";
    hideNoDiscount.checked = true;
    showRewards.checked = true;
    minDiscount.value = 0;
    sortSelect.value = 'discount_desc';
    updateThenBy(true);
    perPageSelect.value = '25'; itemsPerPage = 25;
    document.querySelectorAll('.category-nav li, .category-nav summary').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.category-nav details').forEach(d => d.removeAttribute('open'));
    sidebar.scrollTop = 0;
    if (window.innerWidth <= 900) closeSidebar();
    applyFilters();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  document.getElementById('brandReset').addEventListener('click', resetAll);

  updateThenBy(true);
  initCategories();
  applyFilters();
</script>

</body>
</html>
"""

def main():
    rows = load_rows()
    deals_json = json.dumps(rows)
    
    timestamp = datetime.now().strftime("Latest catalogue scraped at %I:%M %p, %b %d")
    
    html = HTML_TEMPLATE.replace("__DEALS_JSON__", deals_json).replace("__TIMESTAMP__", timestamp)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Done. {len(rows)} deals written to {OUTPUT_HTML}")
    print("Open that file directly in a browser to view it.")

if __name__ == "__main__":
    main()