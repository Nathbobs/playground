import requests
import json
import csv

BASE_URL = ""

# Get collection names
response = requests.get(BASE_URL)
data = response.json()

# Extract collection names (they are the dictionary keys)
collections = list(data.keys())

# Save to JSON
with open("collection_names.json", "w") as f:
    json.dump(collections, f, indent=2)

# Save to CSV
with open("collection_names_new.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["collection_name"])
    for name in collections:
        writer.writerow([name])

print(f"✅ Saved {len(collections)} collection names")
print(f"📄 Files: collection_names.json, collection_names.csv")