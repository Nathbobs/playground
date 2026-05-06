import requests
import json
import csv
from time import sleep
import os
from dotenv import load_dotenv

# -----------------------------
# Settings
# -----------------------------

load_dotenv()

url = os.environ.get("CDM_API_URL")
collection_name = "SPACEMAP_CA_2025JUL08T0800_S1a"  

limit = 100   # number of records per request
offset = 0
batch_save = 1000  # save every 1000 entries
all_data = []

headers = {
    # "Authorization": "Bearer YOUR_TOKEN_HERE"
}

print(f"🚀 Starting CDM download for collection: {collection_name}")

while True:
    params = {"limit": limit, "offset": offset}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Connection error at offset {offset}: {e}. Retrying in 5s...")
        sleep(5)
        continue

    conjunctions = data.get("conjunctions", [])
    if not conjunctions:
        print("✅ No more conjunctions found. Done.")
        break

    all_data.extend(conjunctions)
    offset += len(conjunctions)

    # Progress
    total_count = data.get("totalCount", "unknown")
    print(f"Fetched {len(conjunctions)} entries, total so far: {len(all_data)}/{total_count}")

    # Periodic save
    if len(all_data) % batch_save < limit:
        with open(f"cdm_{collection_name}.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)

        keys = set()
        for entry in all_data:
            for section in entry.values():  # CONJUNCTION, OBJECT1, OBJECT2
                keys.update(section.keys())
        keys = sorted(keys)

        with open(f"cdm_{collection_name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for entry in all_data:
                row = {}
                for section in entry.values():
                    row.update(section)
                writer.writerow(row)

        print(f"💾 Saved checkpoint at offset {offset}")

    # avoid hammering API
    sleep(0.5)

# -----------------------------
# Final save
# -----------------------------
with open(f"cdm_{collection_name}.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, indent=4, ensure_ascii=False)

# flatten CSV
keys = set()
for entry in all_data:
    for section in entry.values():
        keys.update(section.keys())
keys = sorted(keys)

with open(f"cdm_{collection_name}.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for entry in all_data:
        row = {}
        for section in entry.values():
            row.update(section)
        writer.writerow(row)

print(f"✅ Finished! Total entries saved: {len(all_data)}")