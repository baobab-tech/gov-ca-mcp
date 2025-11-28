#!/usr/bin/env python3
import httpx
import json

# Search for transit stops datasets
search_url = "https://donnees.montreal.ca/api/3/action/package_show?id=stm-traces-des-lignes-de-bus-et-de-metro"
try:
    resp = httpx.get(search_url, timeout=30)
    data = resp.json()
    if data.get("success"):
        print("=== STM Bus and Metro Lines ===")
        for r in data.get("result", {}).get("resources", []):
            print(f"  {r.get('name')} ({r.get('format')}): {r.get('url', '')[:80]}")
except Exception as e:
    print(f"Error: {e}")

# Try to look at GTFS
print("\n=== GTFS Data ===")
gtfs_url = "https://donnees.montreal.ca/api/3/action/package_show?id=stm-horaires-planifies-et-trajets-des-bus-et-du-metro"
try:
    resp = httpx.get(gtfs_url, timeout=30)
    data = resp.json()
    if data.get("success"):
        for r in data.get("result", {}).get("resources", []):
            print(f"  {r.get('name')} ({r.get('format')}): {r.get('url', '')[:80]}")
except Exception as e:
    print(f"Error: {e}")

