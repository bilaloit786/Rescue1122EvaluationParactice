import argparse
import asyncio
import html
import json
import random
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, inspect, select, text  # noqa: E402

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.core.question_topics import BUILDING_TOPICS, FIRE_CHAPTERS, RESCUE_CHAPTERS  # noqa: E402
from app.models.user import QuestionBank, active_test_questions, staff_seen_questions  # noqa: E402
from app.services.ai_service import BUILDING_CONTENT  # noqa: E402
from app.services.question_quality import is_valid_question  # noqa: E402


FIRE_BOOK = Path("/home/muhammad-ilal/Desktop/Evaluation/Fire_Book.pdf")
RESCUE_BOOK = Path("/home/muhammad-ilal/Desktop/Evaluation/Rescue disaster Book.pdf")
BUILDING_DOC = Path("/home/muhammad-ilal/Desktop/Evaluation/Notification (The Punjab Community Safety Building_260505_213527.pdf")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OPTION_LETTERS = ["A", "B", "C", "D"]

BAD_STARTS = ("others", "also", "and", "this", "these", "above", "list", "name", "state", "you")
BAD_TEXT_PATTERN = re.compile(
    r"\b(?:participant|workbook|course overview|course methodology|unit test|post[- ]?test|"
    r"evaluation chart|practical evaluations?|preface|edition|feedback|objective|written course|scanned with|"
    r"main safety point|initial scene size-up|practical drill evaluation|training assessment|"
    r"what should a responder do during|which action best shows correct basic practice)\b",
    flags=re.I,
)
STOPWORDS = {
    "about", "above", "after", "again", "against", "also", "because", "before", "being",
    "between", "both", "cannot", "could", "during", "each", "from", "have", "into",
    "more", "must", "only", "other", "shall", "should", "such", "than", "that",
    "their", "there", "these", "they", "this", "through", "under", "used", "when",
    "where", "which", "with", "within", "would", "notes", "course", "academy",
    "service", "services", "emergency", "participant", "participants", "training",
    "the", "and", "for", "are", "will", "your", "able", "chapter", "lesson",
}


@dataclass(frozen=True)
class SourceFact:
    subject: str
    answer: str
    relation: str
    source_text: str
    topic_hint: str = ""


def distribute_total(chapters: list[tuple[str, str]], total: int) -> list[tuple[str, str, int]]:
    base, extra = divmod(total, len(chapters))
    return [
        (topic_id, label, base + (1 if index < extra else 0))
        for index, (topic_id, label) in enumerate(chapters)
    ]


def distribute_difficulties(
    chapters: list[tuple[str, str]],
    easy: int,
    medium: int,
    hard: int,
) -> dict[str, dict[str, int]]:
    return {
        topic_id: {
            "easy": target_easy,
            "medium": target_medium,
            "hard": target_hard,
        }
        for (topic_id, _, target_easy), (_, _, target_medium), (_, _, target_hard) in zip(
            distribute_total(chapters, easy),
            distribute_total(chapters, medium),
            distribute_total(chapters, hard),
        )
    }


BOOK_TARGETS = {
    "FireFighting": {
        "prefix": "FIRE",
        "source": FIRE_BOOK,
        "output": "fire_questions_2500.json",
        "chapters": FIRE_CHAPTERS,
        "difficulty_targets": distribute_difficulties(FIRE_CHAPTERS, easy=1000, medium=1000, hard=500),
    },
    "Rescue": {
        "prefix": "RESCUE",
        "source": RESCUE_BOOK,
        "output": "rescue_disaster_questions_2500.json",
        "chapters": RESCUE_CHAPTERS,
        "difficulty_targets": distribute_difficulties(RESCUE_CHAPTERS, easy=1000, medium=1000, hard=500),
    },
    "BuildingRegulations": {
        "prefix": "BUILDING",
        "source": BUILDING_DOC,
        "output": "building_regulation_questions_500.json",
        "chapters": BUILDING_TOPICS,
        "difficulty_targets": distribute_difficulties(BUILDING_TOPICS, easy=200, medium=200, hard=100),
    },
}


TOPIC_TARGETS = {
    topic_id: {
        "book": book,
        "prefix": config["prefix"],
        "topic_label": topic_label,
        "source": config["source"],
        "difficulty_targets": config["difficulty_targets"][topic_id],
        "total": sum(config["difficulty_targets"][topic_id].values()),
    }
    for book, config in BOOK_TARGETS.items()
    for topic_id, topic_label in config["chapters"]
}


DEFAULT_DISTRACTORS = {
    "fire": [
        "cool the fuel", "protect responders", "control smoke", "stop fire spread",
        "identify hazards", "support evacuation", "supply water", "reduce heat",
        "isolate fuel", "protect breathing", "warn occupants", "inspect equipment",
    ],
    "rescue": [
        "secure the casualty", "protect rescuers", "stabilize hazards", "control lifting",
        "support evacuation", "protect rope edges", "mark unsafe structures", "brief the team",
        "inspect ropes", "maintain communication", "control access", "remove damaged gear",
    ],
    "building": [
        "keep exits clear", "guide evacuation", "provide water supply", "detect fire early",
        "control smoke spread", "support fire crews", "protect occupants", "maintain alarms",
        "inspect extinguishers", "mark escape routes", "reduce ignition hazards", "manage drills",
    ],
}


MANUAL_BUILDING_FACTS = [
    ("Exit staircases", "at least two in each building", "requirement"),
    ("Additional exit staircase", "after every 6000 square feet", "requirement"),
    ("Maximum travel distance", "100 feet", "measurement"),
    ("Exit doors", "open outward on hinges", "requirement"),
    ("Exit door fire rating", "one hour", "measurement"),
    ("Exit door headroom", "80 inches", "measurement"),
    ("Exit door width", "3 feet", "measurement"),
    ("Refuge areas", "required above 100 feet", "requirement"),
    ("Stair illumination backup", "90 minutes", "measurement"),
    ("Stair tread", "11 inches", "measurement"),
    ("Stair riser", "7 inches", "measurement"),
    ("Exit signs", "show EXIT in capital letters", "requirement"),
    ("EXIT letter height", "6 inches", "measurement"),
    ("Fire hydrants", "provide water to fire crews", "use"),
    ("External pillar hydrants", "painted red", "requirement"),
    ("Hydrant outlets", "two 2.5 inch outlets", "measurement"),
    ("Hydrant access distance", "not more than 12 feet from fire road", "measurement"),
    ("Hydrant clear space", "5 feet", "measurement"),
    ("Fire alarm systems", "warn occupants early", "use"),
    ("Emergency evacuation plan", "guides safe escape", "use"),
    ("Safety manager", "monitors building fire safety", "use"),
    ("First aid arrangements", "support injured occupants", "use"),
    ("Fire extinguishers", "control small fires early", "use"),
    ("Sprinkler systems", "control fire automatically", "use"),
    ("Fire safety certificate", "confirms required safety measures", "definition"),
]


MANUAL_TOPIC_FACTS = {
    "fire": [
        ("Fire fighting history", "learn from past incidents", "use"),
        ("Past fire incidents", "improve field practice", "use"),
        ("Fire service history", "guide safer response decisions", "use"),
        ("Personal protective equipment", "protect firefighters from injury", "use"),
        ("SCBA", "protect breathing in smoke", "use"),
        ("Fire helmet", "protect the head", "use"),
        ("Fire gloves", "protect hands from heat", "use"),
        ("Fire triangle", "heat, fuel, and oxygen", "definition"),
        ("Cooling", "removes heat from fire", "definition"),
        ("Smothering", "removes oxygen from fire", "definition"),
        ("Starvation", "removes fuel from fire", "definition"),
        ("Foam", "separates fuel from oxygen", "use"),
        ("Fire hose", "carries water to the nozzle", "use"),
        ("Nozzle", "controls the water stream", "use"),
        ("Fire hydrant", "supplies water for firefighting", "use"),
        ("Ladder", "provides access to height", "use"),
        ("Ventilation", "removes heat and smoke", "use"),
        ("Forcible entry tools", "open locked or blocked doors", "use"),
        ("Incident command", "coordinates emergency operations", "use"),
        ("Confined space entry", "requires atmospheric monitoring", "requirement"),
        ("Fire risk assessment", "identifies hazards before fire", "use"),
    ],
    "rescue": [
        ("Life safety rope", "support rescuers and casualties", "use"),
        ("Utility rope", "secure equipment and tools", "use"),
        ("Stopper knot", "prevents rope ends slipping", "use"),
        ("Anchor point", "holds the rescue rope system", "use"),
        ("Belay system", "protects against falling", "use"),
        ("Basket stretcher", "carries casualties safely", "use"),
        ("Tripod", "supports vertical rescue from depth", "use"),
        ("Shoring", "supports unstable structures", "use"),
        ("Structural triage", "prioritizes damaged buildings", "use"),
        ("INSARAG marking", "shows search and rescue information", "use"),
        ("Operational safety", "protects rescuers and victims", "use"),
        ("Search techniques", "locate trapped victims", "use"),
        ("Confined space rescue", "requires air monitoring", "requirement"),
        ("Casualty evacuation", "moves victims to safety", "use"),
        ("Electrical winch", "pulls or lifts heavy loads", "use"),
        ("Generator", "provides portable power", "use"),
        ("Damaged rescue ropes", "removed from service immediately", "requirement"),
        ("Rope inspection", "finds damage before use", "use"),
        ("Edge protection", "prevents rope damage", "use"),
        ("Vehicle extrication", "removes trapped road victims", "use"),
    ],
}


def normalize_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_phrase(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\b(?:Firefighting\s*&\s*Prevention Course|Basic Rescue Course|Emergency Services Academy|Rescue\s+1122)\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:PWB|PM|TM)\s*\d+\s*[-–]\s*\d+\b", " ", value, flags=re.I)
    value = re.sub(r"^\s*(?:[•*\-]+|\d+(?:\.\d+)*[.)])\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,.;:-()[]{}\"'")


def text_starts_bad(text: str) -> bool:
    return text.lower().startswith(BAD_STARTS)


def is_good_subject(subject: str) -> bool:
    subject = clean_phrase(subject)
    words = subject.split()
    if not 1 <= len(words) <= 7:
        return False
    if text_starts_bad(subject) or BAD_TEXT_PATTERN.search(subject):
        return False
    if re.search(r"\b(?:was|were|there|it|note|notes)\b", subject, flags=re.I):
        return False
    if subject.lower() in STOPWORDS:
        return False
    if re.search(r"_{2,}|@|www\.|[/\\]{2,}", subject):
        return False
    return bool(re.search(r"[A-Za-z]", subject))


def is_good_answer(answer: str) -> bool:
    answer = clean_phrase(answer)
    words = answer.split()
    if not 1 <= len(words) <= 10:
        return False
    if text_starts_bad(answer) or BAD_TEXT_PATTERN.search(answer):
        return False
    if answer.lower() in {"note", "notes", "pass", "fail"}:
        return False
    if re.match(r"^(?:for|to|by|of|and|or)\b", answer, flags=re.I):
        return False
    if re.search(r"\b(?:the|a|an|to|of|and|or|is|are|was|were)\s*$", answer, flags=re.I):
        return False
    if answer.count("(") != answer.count(")"):
        return False
    if re.search(r"_{2,}|@|www\.|copyright|page\s+\d+", answer, flags=re.I):
        return False
    if len(answer) > 72:
        return False
    return bool(re.search(r"[A-Za-z0-9]", answer))


def extract_pdf_text(path: Path) -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        subprocess.run(["pdftotext", "-layout", str(path), tmp.name], check=True)
        return Path(tmp.name).read_text(errors="ignore")


def extract_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        return path.read_text(errors="ignore")
    text = extract_pdf_text(path)
    if normalize_text(text):
        return text
    if path == BUILDING_DOC:
        return BUILDING_CONTENT
    return text


def split_source_units(text: str) -> list[str]:
    text = re.sub(r"\r", "\n", text)
    rough_units = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+", text)
    units = []
    seen = set()
    for unit in rough_units:
        unit = clean_phrase(unit)
        if not 25 <= len(unit) <= 260:
            continue
        if BAD_TEXT_PATTERN.search(unit):
            continue
        if len(re.findall(r"[A-Za-z]", unit)) < 18:
            continue
        key = unit.lower()
        if key in seen:
            continue
        seen.add(key)
        units.append(unit)
    return units


FACT_PATTERNS = [
    ("definition", re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9 /&(),.-]{2,70}?)\s+(?:is|are|means|refers to)\s+(?P<answer>[^.;:]{4,120})", re.I)),
    ("use", re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9 /&(),.-]{2,70}?)\s+(?:is|are)?\s*(?:used|provided|designed)\s+(?:to|for|as|in)\s+(?P<answer>[^.;:]{4,120})", re.I)),
    ("requirement", re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9 /&(),.-]{2,70}?)\s+(?:shall|should|must|required to|required)\s+(?P<answer>[^.;:]{4,120})", re.I)),
    ("definition", re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9 /&(),.-]{2,55}?):\s+(?P<answer>[^.;:]{4,120})")),
]


def fact_from_match(kind: str, match: re.Match, source_text: str) -> SourceFact | None:
    subject = clean_phrase(match.group("subject"))
    answer = clean_phrase(match.group("answer"))
    answer = re.sub(r"^(?:be|to)\s+", "", answer, flags=re.I).strip()
    if not is_good_subject(subject) or not is_good_answer(answer):
        return None
    return SourceFact(subject=subject, answer=answer, relation=kind, source_text=source_text)


def extract_facts_from_text(text: str) -> list[SourceFact]:
    facts = []
    seen = set()
    for unit in split_source_units(text):
        for kind, pattern in FACT_PATTERNS:
            match = pattern.search(unit)
            if not match:
                continue
            fact = fact_from_match(kind, match, unit)
            if fact:
                key = (fact.subject.lower(), fact.answer.lower())
                if key not in seen:
                    facts.append(fact)
                    seen.add(key)
            break
    return facts


def manual_facts(profile: str) -> list[SourceFact]:
    raw_facts = MANUAL_BUILDING_FACTS if profile == "building" else MANUAL_TOPIC_FACTS[profile]
    return [
        SourceFact(subject=subject, answer=answer, relation=relation, source_text=f"{subject}: {answer}")
        for subject, answer, relation in raw_facts
    ]


def topic_concept_facts(topic_label: str, profile: str) -> list[SourceFact]:
    subject = topic_subject(topic_label)
    if profile == "fire":
        raw = [
            (subject, "improve fire response safety", "use"),
            (f"{subject} knowledge", "guide correct emergency decisions", "use"),
            (f"{subject} training", "build practical field skill", "use"),
            (f"{subject} practice", "control hazards during operations", "use"),
            (f"{subject} review", "identify safer working methods", "use"),
            (f"Safety checks for {subject}", "protect responders and occupants", "use"),
            (f"Procedures for {subject}", "support coordinated fire operations", "use"),
            (f"{subject} safety", "reduce injury during response", "use"),
        ]
    elif profile == "rescue":
        raw = [
            (subject, "support safe rescue operations", "use"),
            (f"{subject} knowledge", "guide rescue team decisions", "use"),
            (f"{subject} training", "build practical rescue skill", "use"),
            (f"{subject} practice", "protect rescuers and casualties", "use"),
            (f"{subject} review", "identify safer rescue methods", "use"),
            (f"Safety checks for {subject}", "control hazards before action", "use"),
            (f"Procedures for {subject}", "support coordinated rescue work", "use"),
            (f"{subject} safety", "reduce injury during rescue", "use"),
        ]
    else:
        raw = [
            (subject, "protect building occupants", "use"),
            (f"Safety checks for {subject}", "keep fire systems ready", "use"),
            (f"Exit signs for {subject}", "guide safe evacuation", "use"),
            (f"Emergency exits for {subject}", "provide safe escape routes", "use"),
            (f"Inspection for {subject}", "confirm safety compliance", "use"),
            (f"Planning for {subject}", "prepare occupants for emergencies", "use"),
            (f"Safety systems for {subject}", "detect and control fire early", "use"),
            (f"Management of {subject}", "maintain safety arrangements", "use"),
        ]
    return [
        SourceFact(subject=item_subject, answer=answer, relation=relation, source_text=f"{item_subject}: {answer}")
        for item_subject, answer, relation in raw
        if is_good_subject(item_subject) and is_good_answer(answer)
    ]


def profile_for_book(book: str) -> str:
    if book == "BuildingRegulations":
        return "building"
    if book == "FireFighting":
        return "fire"
    return "rescue"


def topic_subject(topic_label: str) -> str:
    label = re.sub(r"^(Fire|Rescue)\s+\d+\s*[-–]\s*", "", topic_label, flags=re.I)
    label = re.sub(r"\([^)]*\)", " ", label)
    label = re.sub(r"[_-]+", " ", label)
    label = re.sub(r"\s+", " ", label)
    return label.strip(" .") or topic_label


def keywords_for_topic(topic_label: str) -> list[str]:
    label = topic_subject(topic_label)
    words = re.findall(r"[A-Za-z][A-Za-z/-]{2,}", label.lower())
    blocked = STOPWORDS | {
        "fire", "rescue", "introduction", "review", "glossary", "methods", "techniques",
        "equipment", "accessories", "system", "level", "operations",
    }
    return [word for word in words if word not in blocked]


def facts_for_topic(topic_label: str, facts: list[SourceFact], profile: str) -> list[SourceFact]:
    selected = topic_concept_facts(topic_label, profile)
    selected.extend(manual_facts(profile))

    clean = []
    seen = set()
    for fact in selected:
        key = (fact.subject.lower(), fact.answer.lower(), fact.relation)
        if key not in seen:
            clean.append(fact)
            seen.add(key)
    return clean


def measurement_options(answer: str) -> list[str]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*([A-Za-z%]+(?:\s+[A-Za-z%]+)?|square feet|inch outlets)?", answer, flags=re.I)
    if not match:
        return []
    number = float(match.group(1))
    unit = (match.group(2) or "").strip()
    if number <= 10:
        values = [number, number + 1, max(1, number - 1), number + 2]
    elif number <= 100:
        step = 10 if number > 20 else 5
        values = [number, number + step, max(1, number - step), number + (step * 2)]
    else:
        step = 50 if number < 500 else 500
        values = [number, number + step, max(1, number - step), number + (step * 2)]
    options = []
    for value in values:
        value_text = str(int(value)) if float(value).is_integer() else str(value).rstrip("0").rstrip(".")
        options.append(f"{value_text} {unit}".strip())
    return list(dict.fromkeys(options))


def answer_kind(answer: str) -> str:
    if re.search(r"\d", answer):
        return "measurement"
    if re.search(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|ninety|hundred)\s+(?:hours?|minutes?|feet|foot|inches|inch|outlets?)\b", answer, flags=re.I):
        return "measurement"
    if re.fullmatch(r"[A-Z0-9]{2,10}", answer.strip()):
        return "acronym"
    return "phrase"


def build_options(answer: str, pool: list[str], profile: str, rng: random.Random) -> list[str]:
    answer = clean_phrase(answer)
    if answer_kind(answer) == "measurement":
        options = measurement_options(answer)
    else:
        options = [answer]

    candidates = [
        clean_phrase(item) for item in pool
        if clean_phrase(item).lower() != answer.lower()
        and is_good_answer(clean_phrase(item))
        and answer_kind(clean_phrase(item)) == answer_kind(answer)
    ]
    if answer_kind(answer) != "measurement" and len(candidates) < 6:
        candidates.extend(DEFAULT_DISTRACTORS[profile])
    if answer_kind(answer) == "measurement" and len(options) < 4:
        candidates.extend([item for item in pool if re.search(r"\d", item)])

    rng.shuffle(candidates)
    options.extend(candidates)

    clean_options = []
    seen = set()
    for option in options:
        option = clean_phrase(option)
        key = option.lower()
        if not key or key in seen or len(option) > 72:
            continue
        clean_options.append(option)
        seen.add(key)
        if len(clean_options) == 4:
            break

    fallback = DEFAULT_DISTRACTORS[profile]
    for option in fallback:
        if len(clean_options) == 4:
            break
        key = option.lower()
        if key != answer.lower() and key not in seen:
            clean_options.append(option)
            seen.add(key)

    rng.shuffle(clean_options)
    return clean_options[:4]


def stem_templates(relation: str, difficulty: str) -> list[str]:
    templates = {
        "definition": {
            "easy": ["The meaning of {subject} is:", "{subject} refers to:"],
            "medium": ["{subject} is best described as:", "The correct meaning of {subject} is:"],
            "hard": ["The correct statement about {subject} is:", "{subject} should be understood as:"],
        },
        "use": {
            "easy": ["{subject} is mainly used to:", "The main purpose of {subject} is to:"],
            "medium": ["{subject} helps responders to:", "In field work, {subject} is used to:"],
            "hard": ["The best operational use of {subject} is to:", "A responder uses {subject} mainly to:"],
        },
        "requirement": {
            "easy": ["{subject} should be:", "{subject} requires:"],
            "medium": ["The correct safety rule for {subject} is:", "{subject} must be:"],
            "hard": ["The required standard for {subject} is:", "A proper check of {subject} requires:"],
        },
        "measurement": {
            "easy": ["The {subject} requirement is:", "The required value for {subject} is:"],
            "medium": ["The correct measurement for {subject} is:", "{subject} should measure:"],
            "hard": ["The standard value for {subject} is:", "The regulation value for {subject} is:"],
        },
    }
    return templates.get(relation, templates["definition"])[difficulty]


def make_question_text(fact: SourceFact, topic_label: str, difficulty: str, variant: int) -> str:
    subject = clean_phrase(fact.subject)
    relation = "measurement" if answer_kind(fact.answer) == "measurement" else fact.relation
    templates = stem_templates(relation, difficulty)
    text = templates[variant % len(templates)].format(subject=subject)

    if variant >= len(templates):
        topic = topic_subject(topic_label)
        scoped_templates = [
            f"{topic} check: {text}",
            f"{topic} review: {text}",
            f"{topic} drill: {text}",
            f"Safety rule: {text}",
            f"Field check: {text}",
            f"Training check: {text}",
            f"Inspection item: {text}",
            f"Emergency planning check: {text}",
            f"Responder review: {text}",
            f"Operational check: {text}",
            f"Punjab standard check: {text}",
            f"Readiness check: {text}",
        ]
        text = scoped_templates[(variant // len(templates)) % len(scoped_templates)]

    text = normalize_text(text).strip(" .")
    last_word = subject.split()[-1].lower() if subject.split() else ""
    plural_subject = (
        (last_word.endswith("s") or subject.lower().startswith(("safety checks", "procedures", "exit signs", "emergency exits", "safety systems")))
        and last_word not in {"was", "is"}
        and not subject.lower().startswith("introduction of")
        and not subject.lower().startswith(("inspection for", "planning for", "management of"))
    )
    if plural_subject and text.startswith(subject):
        text = text.replace(f"{subject} is ", f"{subject} are ", 1)
        text = text.replace(f"{subject} requires:", f"{subject} require:", 1)
        text = text.replace(f"{subject} helps ", f"{subject} help ", 1)
    elif plural_subject:
        text = re.sub(
            rf"^((?:In|For) [^,]+, )({re.escape(subject)}) is ",
            rf"\1\2 are ",
            text,
            count=1,
        )
        text = re.sub(rf"(^|: )({re.escape(subject)}) is ", rf"\1\2 are ", text, count=1)
        text = re.sub(rf"(^|: )({re.escape(subject)}) requires:", rf"\1\2 require:", text, count=1)
        text = re.sub(rf"(^|: )({re.escape(subject)}) helps ", rf"\1\2 help ", text, count=1)
        text = re.sub(
            rf"(^|: )(In field work, )({re.escape(subject)}) is ",
            rf"\1\2\3 are ",
            text,
            count=1,
        )
    if not text.endswith(":") and not text.endswith("?"):
        text += ":"
    return text


def explanation_for(fact: SourceFact, topic_label: str) -> str:
    source = clean_phrase(fact.source_text)
    if len(source) > 180:
        source = source[:177].rstrip() + "..."
    return f"{fact.answer} is correct for {topic_label}. Source note: {source}"


def build_source_question(
    *,
    fact: SourceFact,
    book: str,
    topic_label: str,
    difficulty: str,
    options: list[str],
    variant: int,
) -> dict | None:
    question_text = make_question_text(fact, topic_label, difficulty, variant)
    if fact.answer not in options:
        return None
    correct_index = options.index(fact.answer)
    option_map = dict(zip(OPTION_LETTERS, options))
    question = {
        "id": "",
        "book": book,
        "question": question_text,
        "options": option_map,
        "correct": OPTION_LETTERS[correct_index],
        "explanation": explanation_for(fact, topic_label),
        "source_chapter": topic_label,
        "q": question_text,
        "opts": options,
        "ans": correct_index,
        "topic": topic_label,
        "source": fact.source_text,
        "difficulty": difficulty,
    }
    return question


def apply_required_metadata(question: dict, *, mcq_id: str, book: str, topic_label: str, difficulty: str) -> dict:
    question["id"] = mcq_id
    question["book"] = book
    question["topic"] = topic_label
    question["difficulty"] = difficulty
    question["source_chapter"] = topic_label
    question["q"] = question["question"]
    question["opts"] = [question["options"][letter] for letter in OPTION_LETTERS]
    question["ans"] = OPTION_LETTERS.index(question["correct"])
    return question


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w/&.-]+\b", text or ""))


def validate_mcq(question: dict, difficulty: str) -> bool:
    required = {
        "id", "book", "question", "options", "correct", "explanation", "source_chapter",
        "q", "opts", "ans", "topic", "source", "difficulty",
    }
    if not required.issubset(question):
        return False
    if question["difficulty"] != difficulty:
        return False
    if question["book"] not in {"FireFighting", "Rescue", "Disaster", "RescueDisaster", "BuildingRegulations"}:
        return False
    if question["question"] != question["q"]:
        return False
    if question["correct"] not in OPTION_LETTERS:
        return False
    if not isinstance(question["options"], dict) or set(question["options"]) != set(OPTION_LETTERS):
        return False
    if question["opts"] != [question["options"][letter] for letter in OPTION_LETTERS]:
        return False
    if question["ans"] != OPTION_LETTERS.index(question["correct"]):
        return False
    if len(set(str(item).lower() for item in question["opts"])) != 4:
        return False
    if word_count(question["question"]) > 22:
        return False
    if BAD_TEXT_PATTERN.search(question["question"]):
        return False
    if any(BAD_TEXT_PATTERN.search(str(option)) for option in question["opts"]):
        return False
    return is_valid_question(question)


def generate_for_topic(
    *,
    book: str,
    prefix: str,
    topic_label: str,
    facts: list[SourceFact],
    all_answers: list[str],
    difficulty_targets: dict[str, int],
    id_start: int,
    seen_questions: set[str],
) -> list[tuple[str, dict]]:
    questions = []
    next_id = id_start
    profile = profile_for_book(book)
    topic_facts = facts_for_topic(topic_label, facts, profile)
    if not topic_facts:
        topic_facts = manual_facts(profile)

    for difficulty in ("easy", "medium", "hard"):
        target = difficulty_targets[difficulty]
        made = 0
        attempts = 0
        while made < target and attempts < target * 120:
            rng = random.Random(f"{book}|{topic_label}|{difficulty}|{attempts}")
            fact = topic_facts[attempts % len(topic_facts)]
            clean_pool = [item for item in all_answers if item in [manual.answer for manual in manual_facts(profile)]]
            options = build_options(fact.answer, clean_pool, profile, rng)
            question = build_source_question(
                fact=fact,
                book=book,
                topic_label=topic_label,
                difficulty=difficulty,
                options=options,
                variant=attempts // len(topic_facts),
            )
            attempts += 1
            if not question:
                continue
            key = question["question"].lower()
            if key in seen_questions:
                continue
            mcq_id = f"{prefix}_{next_id:03d}"
            question = apply_required_metadata(
                question,
                mcq_id=mcq_id,
                book=book,
                topic_label=topic_label,
                difficulty=difficulty,
            )
            if validate_mcq(question, difficulty):
                questions.append((difficulty, question))
                seen_questions.add(key)
                next_id += 1
                made += 1

        if made < target:
            raise RuntimeError(f"Generated only {made}/{target} {difficulty} questions for {topic_label}")
    return questions


def load_book_facts() -> dict[str, list[SourceFact]]:
    facts_by_book = {}
    for book, config in BOOK_TARGETS.items():
        profile = profile_for_book(book)
        text = extract_text(config["source"])
        facts = extract_facts_from_text(text)
        facts.extend(manual_facts(profile))

        clean_facts = []
        seen = set()
        for fact in facts:
            key = (fact.subject.lower(), fact.answer.lower(), fact.relation)
            if key in seen:
                continue
            if is_good_subject(fact.subject) and is_good_answer(fact.answer):
                clean_facts.append(fact)
                seen.add(key)
        facts_by_book[book] = clean_facts
        print(f"- {config['source'].name}: {len(clean_facts)} usable source facts")
    return facts_by_book


def generate_question_bank() -> list[tuple[str, str, dict]]:
    print("Extracting source documents and building short MCQs...")
    facts_by_book = load_book_facts()
    book_counters = {book: 1 for book in BOOK_TARGETS}
    seen_questions: set[str] = set()
    rows = []

    for topic_id, config in TOPIC_TARGETS.items():
        book = config["book"]
        facts = facts_by_book[book]
        profile = profile_for_book(book)
        all_answers = [fact.answer for fact in manual_facts(profile)] + DEFAULT_DISTRACTORS[profile]
        generated = generate_for_topic(
            book=book,
            prefix=config["prefix"],
            topic_label=config["topic_label"],
            facts=facts,
            all_answers=all_answers,
            difficulty_targets=config["difficulty_targets"],
            id_start=book_counters[book],
            seen_questions=seen_questions,
        )
        book_counters[book] += len(generated)
        rows.extend((topic_id, difficulty, question) for difficulty, question in generated)
        print(f"{topic_id}: prepared {len(generated)} questions")

    return rows


def write_json_files(rows: list[tuple[str, str, dict]], data_dir: Path = DATA_DIR) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    by_book = {book: [] for book in BOOK_TARGETS}
    for _, _, question in rows:
        by_book[question["book"]].append(question)

    for book, config in BOOK_TARGETS.items():
        path = data_dir / config["output"]
        path.write_text(json.dumps(by_book[book], indent=2), encoding="utf-8")
        print(f"Wrote {len(by_book[book])} questions to {path}")

    combined = [question for _, _, question in rows]
    combined_path = data_dir / "question_bank_5500.json"
    combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"Wrote {len(combined)} questions to {combined_path}")


def _question_bank_has_valid_column(sync_conn) -> bool:
    inspector = inspect(sync_conn)
    if "question_bank" not in inspector.get_table_names():
        return True
    return any(column["name"] == "is_valid" for column in inspector.get_columns("question_bank"))


async def ensure_question_bank_quality_column() -> None:
    async with engine.begin() as conn:
        has_column = await conn.run_sync(_question_bank_has_valid_column)
        if has_column:
            return
        default_value = "1" if conn.dialect.name == "sqlite" else "TRUE"
        await conn.execute(text(f"ALTER TABLE question_bank ADD COLUMN is_valid BOOLEAN NOT NULL DEFAULT {default_value}"))


async def seed_database(reset: bool = True, write_json: bool = True) -> None:
    rows = generate_question_bank()
    if write_json:
        write_json_files(rows)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_question_bank_quality_column()

    async with AsyncSessionLocal() as db:
        if reset:
            print("Clearing old question bank rows, active reservations, and seen-question links...")
            await db.execute(delete(active_test_questions))
            await db.execute(delete(staff_seen_questions))
            await db.execute(delete(QuestionBank))
            await db.commit()

        inserted = 0
        for topic_id, difficulty, question in rows:
            db.add(QuestionBank(topic_id=topic_id, difficulty=difficulty, question=question, is_valid=True))
            inserted += 1
            if inserted % 250 == 0:
                await db.commit()
        await db.commit()

        total = await db.scalar(select(func.count(QuestionBank.id)))
        difficulty_rows = await db.execute(
            select(QuestionBank.difficulty, func.count(QuestionBank.id)).group_by(QuestionBank.difficulty)
        )
        print(f"Done. Inserted {inserted}; question_bank now has {total} rows.")
        print("Difficulty totals:", dict(difficulty_rows.all()))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and seed the source-based Rescue1122 MCQ bank.")
    parser.add_argument("--no-reset", action="store_true", help="Append instead of replacing question_bank rows.")
    parser.add_argument("--no-json", action="store_true", help="Do not write generated JSON files.")
    args = parser.parse_args()
    await seed_database(reset=not args.no_reset, write_json=not args.no_json)


if __name__ == "__main__":
    asyncio.run(main())
