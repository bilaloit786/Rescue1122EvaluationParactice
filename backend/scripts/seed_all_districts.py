import asyncio
import os
import httpx

DISTRICTS = [
    "Gujrat", "Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala", "Sialkot",
    "Sargodha", "Bahawalpur", "Jhang", "Sheikhupura", "Rahim Yar Khan", "Kasur",
    "Okara", "Sahiwal", "Narowal", "Mandi Bahauddin", "Jhelum", "Chakwal", "Attock",
    "Khushab", "Mianwali", "Bhakkar", "Layyah", "Muzaffargarh", "Dera Ghazi Khan",
    "Rajanpur", "Lodhran", "Vehari", "Pakpattan", "Khanewal", "Hafizabad",
    "Nankana Sahib", "Chiniot", "Toba Tek Singh", "Bahawalnagar"
]

DESIGNATIONS = [
    "Firefighter", "Rescue Officer", "Station Officer", "Safety Manager", "Paramedic"
]

async def seed():
    count = 0
    password = os.getenv("SEED_STAFF_PASSWORD")
    if not password:
        raise RuntimeError("Set SEED_STAFF_PASSWORD before running this script.")

    # Increase limits properly, giving time to sqlite inserts
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        for district in DISTRICTS:
            for designation in DESIGNATIONS:
                first_name = designation.split()[0].lower() # e.g. "firefighter", "rescue", "station"...
                
                # Username format: firstname_district (lowercase, no spaces)
                clean_district = district.lower().replace(' ', '')
                username = f"{first_name}_{clean_district}"
                # Email format: firstname.district@rescue1122.pk
                email = f"{first_name}.{clean_district}@rescue1122.pk"
                
                payload = {
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": f"{designation} {district}",
                    "father_name": f"Mr. {district}",
                    "designation": designation,
                    "district": district
                }
                
                resp = await client.post("/api/auth/register", json=payload)
                if resp.status_code in (200, 201):
                    # Print progress: "Created: {name} | {district}" for each.
                    print(f"Created: {payload['full_name']} | {district}")
                    count += 1
                else:
                    print(f"Failed {username}: {resp.text}")

    # At the end print: "Total created: {count}"
    print(f"Total created: {count}")

if __name__ == "__main__":
    asyncio.run(seed())
