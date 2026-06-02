"""
generate_question_bank.py
═══════════════════════════════════════════════════════════
Generates 5,000+ MCQs from the 3 official Rescue 1122 books.

Run ONCE — cost ~$1.80 — takes ~30 minutes.
Every future test served from DB at zero API cost.

Usage:
    cd backend
    python scripts/generate_question_bank.py

    # Resume if interrupted:
    python scripts/generate_question_bank.py --start-from=fire_suppression

    # Double the bank to 5000+:
    python scripts/generate_question_bank.py --double
═══════════════════════════════════════════════════════════
"""
import asyncio, json, re, sys, os, time
from sqlalchemy.ext.asyncio import AsyncSessionLocal
from sqlalchemy import text as sql_text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.user import QuestionBank


# ─────────────────────────────────────────────────────────
# 1.  LOAD THE REAL BOOKS
# ─────────────────────────────────────────────────────────

def _pdf_text(path: str) -> str:
    import subprocess
    r = subprocess.run(['pdftotext', path, '-'],
                       capture_output=True, text=True, errors='replace')
    return r.stdout if r.returncode == 0 else ''


def _doc_text(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ''


def _clean(text: str) -> str:
    text = re.sub(r'\f', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    noise = {'Rescue 1122', 'Notes', 'Emergency Services Academy',
             'Basic Rescue Course', 'Firefighting & Prevention Course'}
    lines = []
    for l in text.split('\n'):
        s = l.strip()
        if s in noise:                     continue
        if re.match(r'^PWB \d+\s*-\s*\d+$', s): continue
        if re.match(r'^_{4,}$', s):        continue
        lines.append(s)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines))


def load_books():
    """
    Returns (rescue_text, fire_text, building_text) — full cleaned content
    from the three uploaded source books.
    """
    RESCUE  = '/mnt/user-data/uploads/Rescue_disaster_Book.pdf'
    FIRE    = '/mnt/user-data/uploads/Printable_EDITED_FireF_Book_24_Dec_2019_PDF_Final_All.pdf'
    BLDG    = '/mnt/user-data/uploads/BuildingRegulations.doc'

    print('  Loading Basic Rescue Course PDF...', end='', flush=True)
    rescue = _clean(_pdf_text(RESCUE))
    print(f' {len(rescue):,} chars')

    print('  Loading Firefighting & Prevention Course PDF...', end='', flush=True)
    fire = _clean(_pdf_text(FIRE))
    print(f' {len(fire):,} chars')

    print('  Loading Punjab Building Regulations DOC...', end='', flush=True)
    bldg = _doc_text(BLDG)
    print(f' {len(bldg):,} chars')

    return rescue, fire, bldg


# ─────────────────────────────────────────────────────────
# 2.  SLICE BOOKS INTO TOPIC SECTIONS
# ─────────────────────────────────────────────────────────

def _slice(text: str, start_kw: str, end_kws: list, limit: int = 18000) -> str:
    idx = text.find(start_kw)
    if idx == -1:
        return ''
    chunk = text[idx:]
    for ew in end_kws:
        if not ew:
            continue
        pos = chunk.find(ew, len(start_kw) + 50)
        if pos != -1:
            chunk = chunk[:pos]
            break
    return chunk[:limit].strip()


def build_topics(rescue: str, fire: str, bldg: str) -> dict:
    """
    Slice each book by its actual chapter headings.
    Returns {topic_id: {label, book, source}} where source is the raw
    chapter text from the official Rescue 1122 training materials.
    """
    def r(s, ends, lim=18000): return _slice(rescue, s, ends, lim)
    def f(s, ends, lim=18000): return _slice(fire,   s, ends, lim)

    return {

        # ══ BASIC RESCUE COURSE ══════════════════════════════════════

        "ropes_knots": {
            "label": "Ropes & Rescue Knots",
            "book":  "Basic Rescue Course — Workbook 2 (Ropes) & Workbook 3 (Knots)",
            "source": (
                r("1. Ropes",
                  ["1. Knot", "2. Basic rescue Knots", "PARTICIPANT'S"])
                + "\n\n" +
                r("2. Basic rescue Knots",
                  ["1. Personal Protective Equipment", "PARTICIPANT'S"])
                + "\n\n" +
                r("1. 2. Clove Hitch",
                  ["1. Personal Protective Equipment", "PARTICIPANT'S"])
                + "\n\n" +
                r("7. Round turn with two half hitches",
                  ["1. Personal Protective Equipment", "PARTICIPANT'S"])
            ),
        },

        "rope_rescue": {
            "label": "Rope Rescue Techniques",
            "book":  "Basic Rescue Course — Workbook 5 (Rope Rescue Techniques)",
            "source": (
                r("1. Rope Rescue Techniques",
                  ["1. Definition", "PARTICIPANT'S"])
                + "\n\n" +
                r("2.4 Well Rescue with Ladder",
                  ["1. Definition", "PARTICIPANT'S"])
                + "\n\n" +
                r("5. Safety Measures for Rope Rescue",
                  ["1. Definition", "PARTICIPANT'S"])
                + "\n\n" +
                r("Basket Stretcher",
                  ["1. Definition", "PARTICIPANT'S"])
                + "\n\n" +
                r("Descender",
                  ["1. Definition", "PARTICIPANT'S"])
            ),
        },

        "ppe": {
            "label": "Personal Protective Equipment",
            "book":  "Basic Rescue Course Workbook 4 + Firefighting Course",
            "source": (
                r("1. Personal Protective Equipment (PPE)",
                  ["1. Rope Rescue Techniques", "PARTICIPANT'S"])
                + "\n\n" +
                f("Personal Protective Equipment (PPE)",
                  ["Causes of Fire", "Fire History"])
            ),
        },

        "disaster_response": {
            "label": "Disaster Response, ICS & CSSR Operations",
            "book":  "Basic Rescue Course — Workbook 6 (Disaster Management & CSSR)",
            "source": (
                r("1. Definition",
                  ["PARTICIPANT'S WORK BOOK"])
                + "\n\n" +
                r("2. 3. Phases of a CSSR Operation",
                  ["PARTICIPANT'S WORK BOOK"])
                + "\n\n" +
                r("Tools and equipment. Very important to maintain",
                  ["PARTICIPANT'S WORK BOOK"])
            ),
        },

        # ══ FIREFIGHTING & PREVENTION COURSE ═════════════════════════

        "fire_basics": {
            "label": "Fire Chemistry & Causes of Fire",
            "book":  "Firefighting & Prevention Course — Fire Chemistry Lessons",
            "source": (
                f("Causes of Fire",
                  ["Fire Chemistry-2", "Solid and Liquid Fuel"])
                + "\n\n" +
                f("Fire Chemistry",
                  ["Solid and Liquid Fuel Fire Behavior"])
                + "\n\n" +
                f("Solid and Liquid Fuel Fire Behavior",
                  ["Firefighting Tools, Equipment"])
            ),
        },

        "fire_suppression": {
            "label": "Fire Suppression & Foam Tactics",
            "book":  "Firefighting & Prevention Course — Fire Suppression & Foam Lessons",
            "source": (
                f("Fire Suppression",
                  ["Foam and Foam Making Equipment"])
                + "\n\n" +
                f("Foam and Foam Making Equipment",
                  ["Chemical Fire"])
            ),
        },

        "fire_vehicles": {
            "label": "Firefighting Tools, Equipment & Vehicles (Fire-TEA)",
            "book":  "Firefighting & Prevention Course — Fire-TEA & Vehicles Lessons",
            "source": (
                f("Firefighting Tools, Equipment and Accessories",
                  ["Fire Suppression"])
                + "\n\n" +
                f("Introduction to Fire Vehicles",
                  ["Specialized Fire Vehicles"])
                + "\n\n" +
                f("Specialized Fire Vehicles",
                  ["Confined Space Entry"])
            ),
        },

        "fire_hose_water": {
            "label": "Fire Hoses, Pump Tactics & Water Supply",
            "book":  "Firefighting & Prevention Course — Hoses, Pump & Hydrant Lessons",
            "source": (
                f("Fire Hoses",
                  ["Fire Risk Assessment"])
                + "\n\n" +
                f("Fire Pump and Hose Line Tactics",
                  ["Water Supply and Fire Hydrant"])
                + "\n\n" +
                f("Water Supply and Fire Hydrant",
                  ["Fire Ladders"])
            ),
        },

        "scba_respiratory": {
            "label": "Respiratory Protection & SCBA",
            "book":  "Firefighting & Prevention Course — Respiratory Protection Lesson",
            "source": f("Respiratory Protection",
                        ["Building Protection System"]),
        },

        "portable_extinguishers": {
            "label": "Portable Fire Appliances & Extinguishers",
            "book":  "Firefighting & Prevention Course — Portable Appliances Lesson",
            "source": f("Portable Fire Appliances",
                        ["Fire Hoses"]),
        },

        "fire_ladders": {
            "label": "Fire Ladders & Climbing",
            "book":  "Firefighting & Prevention Course — Fire Ladders Lesson",
            "source": f("Fire Ladders",
                        ["Respiratory Protection"]),
        },

        "building_protection_systems": {
            "label": "Building Protection Systems (Sprinklers, Alarms, Detectors)",
            "book":  "Firefighting & Prevention Course — Building Protection Systems Lesson",
            "source": f("Building Protection System",
                        ["Introduction to Fire Vehicles"]),
        },

        "ics": {
            "label": "Incident Command System & Emergency Response Levels",
            "book":  "Firefighting & Prevention Course — ICS Lesson + Basic Rescue Course Workbook 6",
            "source": (
                f("Incident Command System and Emergency Response Level",
                  ["Repair & Maintenance", "Course Review"])
                + "\n\n" +
                r("1. Definition",
                  ["2. 3. Phases of a CSSR"])
            ),
        },

        "fire_risk": {
            "label": "Fire Risk Assessment",
            "book":  "Firefighting & Prevention Course — Fire Risk Assessment Lesson",
            "source": f("Fire Risk Assessment",
                        ["Fire Pump and Hose Line Tactics"]),
        },

        "rescue_fire_buildings": {
            "label": "Rescue from Fire Buildings, Forcible Entry & Ventilation",
            "book":  "Firefighting & Prevention Course — Rescue, Forcible Entry & Ventilation Lessons",
            "source": (
                f("Rescue from Fire Involved Buildings",
                  ["Introduction to Building Code"])
                + "\n\n" +
                f("Forcible Entry",
                  ["Ventilation at Fire"])
                + "\n\n" +
                f("Ventilation at Fire",
                  ["Rescue from Fire Involved Buildings"])
            ),
        },

        "fire_strategies": {
            "label": "Fire Operation Strategies & Tactics",
            "book":  "Firefighting & Prevention Course — Strategies & Tactics Lesson",
            "source": f("Fire Operation Strategies and Tactics",
                        ["Incident Command System"]),
        },

        # ══ PUNJAB BUILDING REGULATIONS ══════════════════════════════

        "building_safety": {
            "label": "Punjab Community Safety Buildings Regulations 2022",
            "book":  "Punjab Community Safety Buildings Regulations 2022 (Official Government Document)",
            "source": bldg,
        },
    }


# ─────────────────────────────────────────────────────────
# 3.  HOW MANY QUESTIONS PER TOPIC × DIFFICULTY
# ─────────────────────────────────────────────────────────

PLAN = {                               # easy  medium  hard   total
    "ropes_knots":              {"easy": 60, "medium": 70, "hard": 30},  # 160
    "rope_rescue":              {"easy": 50, "medium": 60, "hard": 25},  # 135
    "ppe":                      {"easy": 60, "medium": 65, "hard": 25},  # 150
    "disaster_response":        {"easy": 60, "medium": 70, "hard": 30},  # 160
    "fire_basics":              {"easy": 70, "medium": 75, "hard": 35},  # 180
    "fire_suppression":         {"easy": 55, "medium": 65, "hard": 25},  # 145
    "fire_vehicles":            {"easy": 60, "medium": 65, "hard": 25},  # 150
    "fire_hose_water":          {"easy": 60, "medium": 65, "hard": 25},  # 150
    "scba_respiratory":         {"easy": 50, "medium": 55, "hard": 20},  # 125
    "portable_extinguishers":   {"easy": 45, "medium": 50, "hard": 20},  # 115
    "fire_ladders":             {"easy": 40, "medium": 40, "hard": 15},  #  95
    "building_protection_systems": {"easy": 55, "medium": 60, "hard": 25},# 140
    "ics":                      {"easy": 60, "medium": 70, "hard": 30},  # 160
    "fire_risk":                {"easy": 55, "medium": 65, "hard": 25},  # 145
    "rescue_fire_buildings":    {"easy": 55, "medium": 65, "hard": 25},  # 145
    "fire_strategies":          {"easy": 45, "medium": 55, "hard": 20},  # 120
    "building_safety":          {"easy": 80, "medium": 90, "hard": 40},  # 210
}
# ─ Grand total: ~2,485  |  With --double flag: ~4,970 ─────────────


DIFFICULTY_GUIDE = {
    "easy": (
        "EASY — Direct recall. The correct answer appears word-for-word "
        "or near-verbatim in the source text. Test one specific fact. "
        "Example: 'What is the minimum staircase width?' → answer is a "
        "specific measurement stated explicitly in the source."
    ),
    "medium": (
        "MEDIUM — Application. The officer must apply a rule, procedure, "
        "or concept to a described situation. Correct answer requires "
        "understanding — not just memorisation. Example: 'A firefighter "
        "enters a smoke-filled room. What PPE is mandatory and why?'"
    ),
    "hard": (
        "HARD — Analysis or discrimination. Either (a) combine two or more "
        "facts from the source, OR (b) all four options are plausible but "
        "only one is precisely correct. Example: 'Which statement BEST "
        "distinguishes static rope from dynamic rope for rescue operations?'"
    ),
}


# ─────────────────────────────────────────────────────────
# 4.  GENERATE ONE BATCH VIA CLAUDE API
# ─────────────────────────────────────────────────────────

def generate_batch(topic_id, label, book, difficulty, count, source) -> list:
    source_chunk = source[:14000]

    prompt = f"""You are an official examiner for Punjab Emergency Service (Rescue 1122), Pakistan.

TASK: Generate exactly {count} MCQ questions for Rescue 1122 staff knowledge evaluation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE BOOK : {book}
TOPIC       : {label}
DIFFICULTY  : {difficulty.upper()}
{DIFFICULTY_GUIDE[difficulty]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OFFICIAL SOURCE MATERIAL
(All questions MUST come from this text only — no outside knowledge):

{source_chunk}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES (strictly enforced):
1. Exactly {count} questions.
2. Every question answerable ONLY from the source text above.
3. No invented facts. If it is not in the source, do not ask about it.
4. Exactly 4 options per question (A, B, C, D).
5. One correct answer per question.
6. Wrong options must use real Rescue 1122 terminology — not nonsense.
7. No duplicate questions — each tests a different specific fact or concept.
8. "subtopic" field: 3-6 words naming the specific sub-area tested.
9. Return ONLY a JSON array. No preamble, no markdown fences, nothing else.

JSON FORMAT:
[
  {{
    "q": "Complete question text ending with a question mark?",
    "opts": ["Option A", "Option B", "Option C", "Option D"],
    "ans": 0,
    "subtopic": "specific sub-topic name",
    "difficulty": "{difficulty}"
  }}
]

"ans" = 0-indexed correct answer position (0=A, 1=B, 2=C, 3=D).

Generate all {count} questions now:"""

    print("AI question generation is disabled. The app uses the database question bank.")
    return []


# ─────────────────────────────────────────────────────────
# 5.  SAVE BATCH TO POSTGRESQL
# ─────────────────────────────────────────────────────────

async def save_batch(qs: list, topic_id, label, book) -> int:
    saved = 0
    async with AsyncSessionLocal() as db:
        for q in qs:
            if (not isinstance(q, dict)
                    or 'q' not in q or not str(q['q']).strip()
                    or 'opts' not in q or len(q['opts']) != 4
                    or 'ans' not in q or int(q['ans']) not in (0, 1, 2, 3)):
                continue
            db.add(QuestionBank(
                topic_id    = topic_id,
                topic_label = label,
                subtopic    = str(q.get("subtopic", "general"))[:200],
                difficulty  = str(q.get("difficulty", "medium")),
                question    = str(q["q"]).strip(),
                option_a    = str(q["opts"][0]).strip(),
                option_b    = str(q["opts"][1]).strip(),
                option_c    = str(q["opts"][2]).strip(),
                option_d    = str(q["opts"][3]).strip(),
                correct_ans = int(q["ans"]),
                source_doc  = book[:200],
            ))
            saved += 1
        await db.commit()
    return saved


async def existing_counts():
    async with AsyncSessionLocal() as db:
        rows = await db.execute(sql_text(
            "SELECT topic_id, difficulty, COUNT(*) AS n "
            "FROM question_bank GROUP BY topic_id, difficulty"
        ))
        out = {}
        for r in rows:
            out.setdefault(r.topic_id, {})[r.difficulty] = r.n
    return out


# ─────────────────────────────────────────────────────────
# 6.  MAIN LOOP
# ─────────────────────────────────────────────────────────

async def main():
    start_from  = next((a.split('=',1)[1] for a in sys.argv[1:] if a.startswith('--start-from=')), None)
    double_mode = '--double' in sys.argv

    print("=" * 65)
    print("  Rescue 1122  —  Question Bank Generator")
    print("  Source: 3 official books (real full-text content)")
    if double_mode: print("  Mode: DOUBLE (targeting 5,000 questions)")
    print("=" * 65)

    print("\n  Loading source books...")
    rescue, fire, bldg = load_books()
    topics = build_topics(rescue, fire, bldg)

    total_chars = sum(len(t['source']) for t in topics.values())
    print(f"  Source loaded: {total_chars:,} chars across {len(topics)} topics\n")

    have = await existing_counts()
    BATCH_SIZE = 25
    grand_saved = 0
    grand_target = sum(
        sum(d.values()) * (2 if double_mode else 1)
        for d in PLAN.values()
    )

    skipping = bool(start_from)
    for topic_id, diff_plan in PLAN.items():
        if skipping:
            if topic_id == start_from: skipping = False
            else:
                print(f"  ↷  Skipping {topic_id}")
                continue

        if topic_id not in topics:
            print(f"  ⚠   No source text for '{topic_id}' — skipping")
            continue

        td = topics[topic_id]
        src_size = len(td['source'])
        print(f"\n{'─'*65}")
        print(f"  ▶  {td['label']}")
        print(f"     {td['book']}")
        print(f"     Source: {src_size:,} chars  |  {src_size//5:,} words approx")
        print(f"{'─'*65}")

        for diff, target in diff_plan.items():
            if double_mode:
                target *= 2
            already = have.get(topic_id, {}).get(diff, 0)
            need    = max(0, target - already)
            if need == 0:
                print(f"    [{diff:6s}] ✓ already have {already}/{target}")
                continue

            print(f"    [{diff:6s}] need {need} more  (have {already}/{target})")
            batches = [BATCH_SIZE] * (need // BATCH_SIZE)
            if need % BATCH_SIZE:
                batches.append(need % BATCH_SIZE)

            for bi, bsz in enumerate(batches):
                label = f"      batch {bi+1}/{len(batches)} ({bsz} Qs)"
                print(f"{label}...", end='', flush=True)
                for attempt in range(1, 4):
                    try:
                        qs = generate_batch(
                            topic_id, td['label'], td['book'],
                            diff, bsz, td['source']
                        )
                        n = await save_batch(qs, topic_id, td['label'], td['book'])
                        grand_saved += n
                        pct = grand_saved / grand_target * 100
                        print(f" ✓  {n} saved  [{grand_saved}/{grand_target}  {pct:.1f}%]")
                        time.sleep(3)   # ~20 req / min to stay within rate limit
                        break
                    except json.JSONDecodeError as e:
                        print(f" ✗  JSON error (try {attempt}/3): {e}")
                        time.sleep(5)
                    except Exception as e:
                        print(f" ✗  Error (try {attempt}/3): {e}")
                        time.sleep(10)
                else:
                    print(f"      ⚠  Skipping batch after 3 failures")

    print(f"\n{'='*65}")
    print(f"  DONE  —  {grand_saved} questions saved this run")
    print(f"  Estimated cost  : ~${grand_saved * 0.00036:.2f}")
    print(f"  Cost per test   : $0.00  (DB lookup)")
    print()
    print("  Verify with:")
    print("    SELECT topic_id, difficulty, COUNT(*)")
    print("    FROM question_bank")
    print("    GROUP BY topic_id, difficulty")
    print("    ORDER BY topic_id, difficulty;")
    print(f"{'='*65}")


if __name__ == "__main__":
    asyncio.run(main())
