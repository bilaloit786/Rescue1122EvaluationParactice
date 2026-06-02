import asyncio
import httpx
from datetime import datetime, timezone
import json
import os

GROUP_A = {"Gujrat", "Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala", "Sialkot", "Sargodha", "Bahawalpur", "Jhang", "Sheikhupura", "Rahim Yar Khan"}
GROUP_B = {"Kasur", "Okara", "Sahiwal", "Narowal", "Mandi Bahauddin", "Jhelum", "Chakwal", "Attock", "Khushab", "Mianwali", "Bhakkar", "Layyah"}
GROUP_C = {"Muzaffargarh", "Dera Ghazi Khan", "Rajanpur", "Lodhran", "Vehari", "Pakpattan", "Khanewal", "Hafizabad", "Nankana Sahib", "Chiniot", "Toba Tek Singh", "Bahawalnagar"}

TOPIC_MAP = {
    "Firefighter": "fire_basics",
    "Rescue Officer": "ropes_knots",
    "Station Officer": "ics",
    "Safety Manager": "building_safety",
    "Paramedic": "first_aid_rescue"
}

DISTRICTS = list(GROUP_A | GROUP_B | GROUP_C)
DESIGNATIONS = ["Firefighter", "Rescue Officer", "Station Officer", "Safety Manager", "Paramedic"]

async def run_tests():
    results = []
    staff_password = os.getenv("SEED_STAFF_PASSWORD")
    if not staff_password:
        raise RuntimeError("Set SEED_STAFF_PASSWORD before running this script.")
    
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Loop over all accounts exactly like the seeder
        for district in DISTRICTS:
            for designation in DESIGNATIONS:
                first_name = designation.split()[0].lower()
                clean_district = district.lower().replace(' ', '')
                username = f"{first_name}_{clean_district}"
                
                # 1. Login
                login_resp = await client.post("/api/auth/login", data={"username": username, "password": staff_password})
                if login_resp.status_code != 200:
                    print(f"Login failed for {username}: HTTP {login_resp.status_code}")
                    continue
                token = login_resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # 2. Generate questions
                topic_id = TOPIC_MAP[designation]
                gen_resp = await client.post("/api/test/generate", json={"topic_id": topic_id, "designation": designation}, headers=headers)
                if gen_resp.status_code != 200:
                    print(f"Gen failed for {username}: {gen_resp.text}")
                    continue
                questions = gen_resp.json()["questions"]
                
                # 3. Simulate correct/wrong based on groups
                answers = []
                if district in GROUP_A:
                    correct_limit = 20 # 20/25 = 80%
                elif district in GROUP_B:
                    correct_limit = 15 # 15/25 = 60%
                else:
                    correct_limit = 11 # 11/25 = 44% (fails)
                    
                for i, q in enumerate(questions):
                    ans_correct = q["ans"]
                    if i < correct_limit:
                        selected = ans_correct
                    else:
                        selected = (ans_correct + 1) % 4
                    answers.append({"q_index": i, "selected": selected})
                
                # 4. Submit
                submit_payload = {
                    "topic_id": topic_id,
                    "topic_label": topic_id.replace("_", " ").title(),
                    "questions": questions,
                    "answers": answers,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "time_taken_seconds": 1200
                }
                
                submit_resp = await client.post("/api/test/submit", json=submit_payload, headers=headers)
                if submit_resp.status_code == 200:
                    data = submit_resp.json()
                    score = data["score_percent"]
                    passed = data["passed"]
                    status_str = "PASS" if passed else "FAIL"
                    print(f"{first_name} ({username}) | {district} | {score}% | {status_str}")
                    results.append({
                        "name": username, 
                        "district": district, 
                        "designation": designation, 
                        "score": score, 
                        "passed": passed,
                        "group": "A" if district in GROUP_A else "B" if district in GROUP_B else "C"
                    })
                else:
                    print(f"Submit failed for {username}: {submit_resp.text}")
                    
    # Generate Analytics
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    district_scores = {}
    district_pass = {}
    designation_scores = {}
    
    for r in results:
        dist = r["district"]
        desig = r["designation"]
        district_scores.setdefault(dist, []).append(r["score"])
        district_pass.setdefault(dist, []).append(1 if r["passed"] else 0)
        designation_scores.setdefault(desig, []).append(r["score"])
        
    dist_avg = {d: sum(scores)/len(scores) for d, scores in district_scores.items()}
    dist_pass_rate = {d: (sum(p)/len(p))*100 for d, p in district_pass.items()}
    desig_avg = {d: sum(scores)/len(scores) for d, scores in designation_scores.items()}
    
    sorted_dists = sorted(dist_avg.items(), key=lambda x: x[1], reverse=True)
    sorted_pass_rate = sorted(dist_pass_rate.items(), key=lambda x: x[1], reverse=True)
    
    print("\n--- RESULTS SUMMARY ---")
    print(f"Total Passed: {passed_count} / Total Failed: {failed_count}")
    print("\nTop 5 Districts (Pass Rate):")
    for d, s in sorted_pass_rate[:5]: print(f"{d}: {s:.0f}% pass rate / {dist_avg[d]}% avg")
    print("\nBottom 5 Districts (Pass Rate):")
    for d, s in sorted_pass_rate[-5:]: print(f"{d}: {s:.0f}% pass rate / {dist_avg[d]}% avg")
    print("\nDesignation Averages:")
    for d, s in desig_avg.items(): print(f"{d}: {s}%")
    print("\nMost Failed Topic Overall: Since this was deterministic, all topics fail equally for Group C.")
    
    # Write to local file to build the report later
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports'), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), '..', 'reports', 'raw_data.json'), "w") as f:
        json.dump(results, f)


if __name__ == "__main__":
    asyncio.run(run_tests())
