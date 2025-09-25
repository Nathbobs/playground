import requests
import json

url = "https://cdm.spacemap42.com/api/v1/cdm"
all_data = []
limit = 100
offset = 0

while True:
    params = {"limit": limit, "offset": offset}
    response = requests.get(url, params=params)
    data = response.json()

    if not data:  # empty list → no more data
        break

    all_data.extend(data)
    offset += limit

# Save to JSON
with open("cdm_all.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, indent=4, ensure_ascii=False)

print(f"✅ Downloaded {len(all_data)} CDM entries")