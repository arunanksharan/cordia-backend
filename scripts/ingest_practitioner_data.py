
import asyncio
import json
import os
import sys
from sqlalchemy.future import select

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.db import SessionLocal
from app.modules.directory.models import Practitioner, Location
from app.modules.availability.models import PractitionerSchedule

async def create_schedule_for_practitioner(db, practitioner_id, location_id):
    """
    Creates the default weekly schedule for a given practitioner.
    """
    print(f"    - Creating default schedule for practitioner {practitioner_id}...")
    working_days = range(5)  # Monday to Friday
    time_blocks = [
        {"start": 9, "end": 13},   # 9:00 AM to 1:00 PM
        {"start": 13, "end": 15},  # 1:00 PM to 3:00 PM
    ]

    for day in working_days:
        for block in time_blocks:
            schedule_entry = PractitionerSchedule(
                practitioner_id=practitioner_id,
                location_id=location_id,
                day_of_week=day,
                start_minute=block["start"] * 60,
                end_minute=block["end"] * 60,
                slot_minutes=15,
                active=True
            )
            db.add(schedule_entry)
    print("      ...schedule created.")

async def main():
    """
    Main function to ingest practitioner data from JSON file.
    """
    print("Starting data ingestion...")
    
    # Load data from JSON file
    json_file_path = os.path.join(os.path.dirname(__file__), 'aster_doctors_full.json')
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with SessionLocal() as db:
        for doc_data in data:
            print(f"Processing doctor: {doc_data['name']} at {doc_data['hospital']}")

            # --- Find or Create Location (Hospital) ---
            loc_result = await db.execute(select(Location).where(Location.name == doc_data['hospital']))
            location = loc_result.scalars().first()

            if not location:
                print(f"  - Hospital '{doc_data['hospital']}' not found. Creating new one.")
                location = Location(name=doc_data['hospital'])
                db.add(location)
                await db.flush()
                await db.refresh(location)
                print(f"    ...created hospital with ID: {location.id}")
            else:
                print(f"  - Found existing hospital with ID: {location.id}")

            # --- Find or Create Practitioner (Doctor) ---
            prac_result = await db.execute(
                select(Practitioner).where(
                    Practitioner.name == doc_data['name'],
                    Practitioner.location_id == location.id
                )
            )
            practitioner = prac_result.scalars().first()

            if practitioner:
                print(f"  - Practitioner '{doc_data['name']}' already exists for this location. Skipping.")
                continue
            
            print(f"  - Creating new practitioner: {doc_data['name']}")
            practitioner = Practitioner(
                name=doc_data.get('name'),
                specialty=doc_data.get('department'),
                location_id=location.id,
                designation=doc_data.get('designation'),
                qualifications=doc_data.get('qualifications'),
                profile_url=doc_data.get('profile_url'),
                overview=doc_data.get('overview'),
                area_of_expertise=doc_data.get('area_of_expertise'),
                awards_recognition=doc_data.get('awards_recognition'),
                active=True
            )
            db.add(practitioner)
            await db.flush()
            await db.refresh(practitioner)
            print(f"    ...created practitioner with ID: {practitioner.id}")

            # --- Create Schedule for the new Practitioner ---
            await create_schedule_for_practitioner(db, practitioner.id, location.id)

        print("\nCommitting all changes to the database...")
        await db.commit()
        print("Data ingestion complete!")

if __name__ == "__main__":
    asyncio.run(main())
