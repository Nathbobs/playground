import json
import os
from pymongo import MongoClient
from datetime import datetime

# -----------------------------
# Configuration
# -----------------------------
MONGO_URL = "..."  # Add your MongoDB URL here
DB_NAME = "SPACEMAP-CDM"
DOWNLOAD_PATH = "..."

# Date range configuration
YEAR = "2025"
MONTH = "AUG"
START_DAY = 22
END_DAY = 31
TIMES = ["0000", "0800", "1600"]

# Filter configuration
FILTER_QUERY = {"TYPE": "MAJOR"}

# -----------------------------
# Helper Functions
# -----------------------------
def get_collection_name(day, time):
    """Generate collection name based on day and time"""
    day_str = str(day).zfill(2)  # Pad with zero (7 -> 07)
    return f"SPACEMAP_CA_{YEAR}{MONTH}{day_str}T{time}_S1"

def download_collection(db, collection_name, output_path):
    """Download a single collection with filter and save to JSON"""
    try:
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            print(f"⚠️  Collection '{collection_name}' not found - skipping")
            return False
        
        # Query with filter
        collection = db[collection_name]
        data = list(collection.find(FILTER_QUERY))
        
        # Check if data exists
        if len(data) == 0:
            print(f"⚠️  No MAJOR type data found in '{collection_name}' - skipping")
            return False
        
        # Save to JSON file
        filename = f"SPACEMAP-CDM.{collection_name}.json"
        filepath = os.path.join(output_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Downloaded: {filename} ({len(data)} records)")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading '{collection_name}': {e}")
        return False

# -----------------------------
# Main Execution
# -----------------------------
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🛰️  SPACEMAP CDM Data Downloader (Filtered: TYPE=MAJOR)")
    print("=" * 70)
    print(f"📅 Downloading: Day {START_DAY} to Day {END_DAY} ({YEAR} {MONTH})")
    print(f"⏰ Times: {', '.join(TIMES)}")
    print(f"📂 Destination: {DOWNLOAD_PATH}")
    print(f"🔍 Filter: {FILTER_QUERY}")
    print("=" * 70 + "\n")
    
    # Create download directory if it doesn't exist
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)
        print(f"📁 Created directory: {DOWNLOAD_PATH}\n")
    
    # Connect to MongoDB
    try:
        print("🔌 Connecting to MongoDB...")
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Test connection
        db.list_collection_names()
        print("✅ Connected successfully!\n")
        
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        exit(1)
    
    # Download data for each day and time
    print("=" * 70)
    print("📥 Starting Downloads")
    print("=" * 70 + "\n")
    
    successful_downloads = 0
    failed_downloads = 0
    total_files = (END_DAY - START_DAY + 1) * len(TIMES)
    
    for day in range(START_DAY, END_DAY + 1):
        print(f"📆 Day {day:02d}")
        print("-" * 70)
        
        for time in TIMES:
            collection_name = get_collection_name(day, time)
            
            if download_collection(db, collection_name, DOWNLOAD_PATH):
                successful_downloads += 1
            else:
                failed_downloads += 1
        
        print()  # Empty line between days
    
    # Summary
    print("=" * 70)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"Total files attempted: {total_files}")
    print(f"✅ Successful: {successful_downloads}")
    print(f"❌ Failed/Skipped: {failed_downloads}")
    print(f"📂 Files saved to: {DOWNLOAD_PATH}")
    print("=" * 70 + "\n")
    
    # Close MongoDB connection
    client.close()
    print("✅ Done! MongoDB connection closed.")