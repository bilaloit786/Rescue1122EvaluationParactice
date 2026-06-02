import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.models.user import QuestionBank, User, StaffProfile
from app.core.security import get_password_hash

async def main():
    print("--- STEP 4: Test Uniqueness with 10 Staff ---")
    
    # 1. Register 10 Staff directly via DB
    staff_ids = []
    async with AsyncSessionLocal() as db:
        for i in range(1, 11):
            email = f"staff{i}_test@rescue1122.gov.pk"
            # clean up if exists
            existing = await db.execute(select(User).where(User.email == email))
            u = existing.scalar_one_or_none()
            if u:
                await db.delete(u)
                await db.commit()
            
            user = User(
                email=email,
                username=f"staff{i}_test",
                hashed_password=get_password_hash("password123"),
                role="staff"
            )
            db.add(user)
            await db.flush()
            profile = StaffProfile(
                user_id=user.id,
                full_name=f"Test Staff {i}",
                designation="Rescuer",
                district="Lahore"
            )
            db.add(profile)
            await db.commit()
            staff_ids.append(user.id)
            
    # 2. Login & Generate Test for each
    staff_tokens = []
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # We need the app running, or we can just use the functions directly.
        # Let's just use the functions directly to avoid needing the server running.
        pass

    # Wait, using the HTTP client requires the server to be running.
    # I'll just invoke the functions directly since I have the DB.
    from app.api.test import generate, submit_test
    from app.schemas.schemas import GenerateQuestionsRequest, SubmitTestRequest, AnswerItem
    
    seen_sets = []
    staff_users = []
    
    async with AsyncSessionLocal() as db:
        for i, user_id in enumerate(staff_ids):
            user = await db.get(User, user_id)
            staff_users.append(user)
            
            payload = GenerateQuestionsRequest(topic_id="fire_basics", designation="Rescuer")
            res = await generate(payload, current_user=user, db=db)
            q_ids = set([q["id"] for q in res["questions"]])
            seen_sets.append(q_ids)
            print(f"Staff #{i+1} received {len(q_ids)} questions: {sorted(list(q_ids))}")

    # Check overlaps
    has_overlap = False
    for i in range(len(seen_sets)):
        for j in range(i + 1, len(seen_sets)):
            overlap = seen_sets[i].intersection(seen_sets[j])
            if overlap:
                print(f"WARNING: Staff #{i+1} and #{j+1} have overlap: {overlap}")
                has_overlap = True
    
    if not has_overlap:
        print("SUCCESS: No two staff got the same set of 25 questions!\n")
        
    print("--- STEP 5: Take a Second Test as Staff #1 ---")
    async with AsyncSessionLocal() as db:
        user1 = staff_users[0]
        # Generate second test
        payload = GenerateQuestionsRequest(topic_id="fire_basics", designation="Rescuer")
        res2 = await generate(payload, current_user=user1, db=db)
        q_ids_2 = set([q["id"] for q in res2["questions"]])
        
        print(f"Staff #1 Round 1: {sorted(list(seen_sets[0]))}")
        print(f"Staff #1 Round 2: {sorted(list(q_ids_2))}")
        
        overlap2 = seen_sets[0].intersection(q_ids_2)
        if overlap2:
            print(f"WARNING: Staff #1 got repeat questions: {overlap2}")
        else:
            print("SUCCESS: Staff #1 received completely different 25 questions in Round 2!\n")
            
        # Let's submit the first test for Staff #1 to log some analytics
        print("Submitting Test for Staff #1 (All Wrong Answers) to generate analytics...")
        submit_payload = SubmitTestRequest(
            topic_id="fire_basics",
            topic_label="Fire Chemistry & Causes",
            questions=res2["questions"],
            answers=[AnswerItem(q_index=idx, selected=-1) for idx in range(len(res2["questions"]))],
            started_at="2026-04-21T12:00:00Z"
        )
        await submit_test(submit_payload, current_user=user1, db=db)
        print("Submitted successfully.\n")
        
    print("--- STEP 6: Check the Hardest Questions ---")
    async with AsyncSessionLocal() as db:
        query = text("""
            SELECT id, times_served, times_wrong,
                   ROUND(times_wrong * 100.0 / NULLIF(times_served,0), 1) AS fail_rate
            FROM question_bank
            WHERE times_served > 0
            ORDER BY fail_rate DESC LIMIT 10;
        """)
        rows = await db.execute(query)
        print("ID | Served | Wrong | Fail Rate %")
        print("-" * 40)
        for r in rows:
            print(f"{r[0]:<2} | {r[1]:<6} | {r[2]:<5} | {r[3]}")

if __name__ == "__main__":
    asyncio.run(main())
