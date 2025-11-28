#!/usr/bin/env python3
from gov_ca_transportation.api_client import TransportationAPIClient
import json

client = TransportationAPIClient()

# Test query_bridges - Multiple provinces
print("=== Testing query_bridges (No filter - All Canada) ===")
result = client.query_bridges(limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")
if result['bridges']:
    b = result['bridges'][0]
    print(f"First Bridge: {b.get('name')} ({b.get('location', {}).get('province')})")

print("\n=== Testing query_bridges (Ontario only) ===")
result = client.query_bridges(province="Ontario", limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")
if result['bridges']:
    b = result['bridges'][0]
    print(f"Bridge: {b.get('name')}, BCI: {b.get('condition_index')}, Year: {b.get('year_built')}")
    print(f"Location: {b.get('location', {}).get('county')}, {b.get('location', {}).get('province')}")

print("\n=== Testing query_bridges (Montreal) ===")
result = client.query_bridges(city="Montreal", limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")
if result['bridges']:
    b = result['bridges'][0]
    print(f"Bridge: {b.get('name')}, Type: {b.get('structure_type')}")

# Test cycling - Multiple cities
print("\n=== Testing query_cycling_networks (All - no filter) ===")
result = client.query_cycling_networks(limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")

print("\n=== Testing query_cycling_networks (Toronto) ===")
result = client.query_cycling_networks(municipality="Toronto", limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")
if result['cycling_paths']:
    p = result['cycling_paths'][0]
    print(f"Path: {p.get('name')}, Type: {p.get('path_type')}")

print("\n=== Testing query_cycling_networks (Quebec province) ===")
result = client.query_cycling_networks(province="Quebec", limit=3)
print(f"Count: {result['count']}")
print(f"Sources: {result['sources']}")
if result['cycling_paths']:
    p = result['cycling_paths'][0]
    print(f"Path ID: {p.get('id')}, Type: {p.get('path_type')}")
