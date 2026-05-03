import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


def load_json_file(filename: str) -> dict:
    """Load JSON file from data directory safely.

    Args:
        filename: Name of JSON file in data/

    Returns:
        Parsed dict or empty dict on error
    """
    filepath = DATA_DIR / filename
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Data file not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {filepath}: {e}")
        return {}


def get_all_stages() -> list:
    """Return all 8 election stages sorted by id.

    Returns:
        List of stage dicts
    """
    data = load_json_file("election_stages.json")
    return sorted(data.get("stages", []), key=lambda x: x["id"])


def get_stage_by_id(stage_id: int) -> dict | None:
    """Return a single election stage by its id.

    Args:
        stage_id: Integer id between 1 and 8

    Returns:
        Stage dict or None if not found
    """
    stages = get_all_stages()
    return next((s for s in stages if s["id"] == stage_id), None)


def get_timeline() -> dict:
    """Return full election timeline data.

    Returns:
        Timeline dict with phases list
    """
    return load_json_file("timeline.json")


def get_all_roles() -> list:
    """Return all election role definitions.

    Returns:
        List of role dicts
    """
    data = load_json_file("roles.json")
    return data.get("roles", [])


def get_glossary_sorted() -> list:
    """Return all glossary terms sorted alphabetically.

    Returns:
        List of term dicts sorted by term field
    """
    data = load_json_file("glossary.json")
    terms = data.get("terms", [])
    return sorted(terms, key=lambda x: x["term"].lower())


def search_glossary(query: str) -> list:
    """Search glossary terms by partial case-insensitive match.

    Args:
        query: Search string

    Returns:
        List of matching term dicts
    """
    query_lower = query.lower()
    terms = get_glossary_sorted()
    return [
        t for t in terms
        if query_lower in t["term"].lower()
        or query_lower in t["definition"].lower()
    ]


def get_quiz_questions_safe() -> list:
    """Return quiz questions with correct answer field removed for client safety.

    Returns:
        List of question dicts without correct field
    """
    data = load_json_file("quiz.json")
    questions = data.get("questions", [])
    safe = []
    for q in questions:
        safe_q = {k: v for k, v in q.items() if k != "correct"}
        safe.append(safe_q)
    return safe


def check_quiz_answer(question_id: int, answer: int) -> dict:
    """Validate a quiz answer server-side.

    Args:
        question_id: The question id (1-10)
        answer: The selected answer index (0-3)

    Returns:
        dict with correct (bool) and explanation (str)
    """
    data = load_json_file("quiz.json")
    questions = data.get("questions", [])
    question = next(
        (q for q in questions if q["id"] == question_id),
        None
    )
    if not question:
        return {"error": "Question not found", "correct": False, "explanation": ""}

    is_correct = answer == question["correct"]
    return {
        "correct": is_correct,
        "explanation": question["explanation"],
        "correct_answer": question["correct"]
    }
