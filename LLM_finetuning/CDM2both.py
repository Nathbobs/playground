import requests
import json
import csv
from time import sleep
from tqdm import tqdm  # progress bar, install with pip install tqdm

# API endpoint (replace with the correct one if needed)
url = "https://cdm.spacemap42.com/cdm"

# Parameters
limit = 100  # number of records per request
offset = 0
all_data = []

# Optional: headers for authentication if needed
headers = {
    # "Authorization": "Bearer YOUR_TOKEN_HERE"
}

print("🚀 Starting CDM data download...")

while True:
    params = {"limit": limit, "offset": offset}
    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        print("❌ Error:", response.status_code, response.text)
        break

    data = response.json()
    if not data:
        print("✅ All data fetched.")
        break

    all_data.extend(data)
    offset += limit

    # Progress indicator
    print(f"Fetched {len(data)} entries, total so far: {len(all_data)}")

    # Optional: sleep to avoid API rate limits
    sleep(0.5)

# -------------------------------
# Save as JSON
with open("cdm_all.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, indent=4, ensure_ascii=False)
print("✅ Saved JSON: cdm_all.json")

# -------------------------------
# Save as CSV
if all_data:
    keys = all_data[0].keys()
    with open("cdm_all.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_data)
    print("✅ Saved CSV: cdm_all.csv")
else:
    print("⚠️ No data to save in CSV")
