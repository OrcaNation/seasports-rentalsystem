from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv
import os

load_dotenv()

# MONGO_URI = os.getenv("MONGO_URI")
# client = MongoClient(MONGO_URI)
# db = client["rental_system"]

# Guests
guests = [
    {
        "name": "Alice Waters",
        "room_number": "102A",
        "departure_date": datetime(2025, 5, 28),
        "liability_waiver_signed": True,
        "waiver_pdf_url": "https://example.com/waivers/alice.pdf",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "name": "Bob Marley",
        "room_number": "305C",
        "departure_date": datetime(2025, 5, 30),
        "liability_waiver_signed": False,
        "waiver_pdf_url": "",
        "created_at": datetime.now(timezone.utc)
    }
]
db.guests.insert_many(guests)

# Equipments
equipments = [
    {
        "type": "snorkel set",
        "unique_id": "EQ001",
        "condition": "good",
        "rental_price": 10.0,
        "replacement_cost": 50.0,
        "issues_log": []
    },
    {
        "type": "fins",
        "unique_id": "EQ002",
        "condition": "fair",
        "rental_price": 5.0,
        "replacement_cost": 30.0,
        "issues_log": ["strap loose"]
    }
]
db.equipments.insert_many(equipments)

# Rentals
rentals = [
    {
        "guest_id": guests[0]["_id"],
        "equipment_ids": [equipments[0]["unique_id"]],
        "rental_date": datetime.now(timezone.utc),
        "returned": False
    }
]
db.rentals.insert_many(rentals)

print("Fake data inserted ✅")