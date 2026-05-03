"""firebase_service.py — Firebase Admin SDK wrapper for VoteGuide.

Handles:
  - Firestore leaderboard (quiz scores)
  - Async translation via Google Cloud Translate SDK
  - Graceful fallback when Firebase credentials are not configured
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firebase Admin SDK initialisation
# ---------------------------------------------------------------------------

_db = None
_firebase_available = False

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    _cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    _project_id = os.getenv("FIREBASE_PROJECT_ID", "voteguide-df047")

    if _cred_path and os.path.exists(_cred_path):
        # Service account JSON provided (production / Cloud Run with mounted secret)
        cred = credentials.Certificate(_cred_path)
        firebase_admin.initialize_app(cred, {"projectId": _project_id})
    else:
        # Application Default Credentials (Cloud Run's attached service account
        # or local `gcloud auth application-default login`)
        firebase_admin.initialize_app(options={"projectId": _project_id})

    _db = firestore.client()
    _firebase_available = True
    logger.info("Firebase Admin SDK initialised (project=%s)", _project_id)

except Exception as exc:
    logger.warning(
        "Firebase Admin SDK not available — leaderboard and server-side "
        "Firestore features disabled. Reason: %s", exc
    )


# ---------------------------------------------------------------------------
# Google Cloud Translate (async-compatible via httpx)
# ---------------------------------------------------------------------------

async def translate_text(text: str, target_lang: str) -> Optional[str]:
    """Translate text to target_lang using Google Translate REST API.

    Uses the GOOGLE_TRANSLATE_API_KEY env var. Falls back gracefully.
    """
    translate_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not translate_key:
        return None
    try:
        import httpx
        url = (
            "https://translation.googleapis.com"
            "/language/translate/v2"
            f"?key={translate_key}"
        )
        payload = {"q": text, "target": target_lang, "format": "text"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
        if r.status_code == 200:
            return r.json()["data"]["translations"][0]["translatedText"]
    except Exception as e:
        logger.error("Translation error: %s", e)
    return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Return True if Firestore is reachable."""
    return _firebase_available


async def save_quiz_score(player_name: str, score: int, total: int) -> Optional[str]:
    """Write a quiz score document to Firestore.

    Returns the new document ID, or None if Firestore is unavailable.
    """
    if not _firebase_available or _db is None:
        logger.warning("save_quiz_score called but Firebase unavailable")
        return None
    try:
        doc_ref = _db.collection("quiz_scores").document()
        doc_ref.set({
            "player_name": player_name,
            "score": score,
            "total": total,
            "percentage": round((score / total) * 100) if total > 0 else 0,
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("Quiz score saved: %s => %d/%d", player_name, score, total)
        return doc_ref.id
    except Exception as e:
        logger.error("Error saving quiz score: %s", e)
        return None


async def get_leaderboard(limit: int = 10) -> list:
    """Fetch top quiz scores ordered by score descending.

    Returns list of dicts with player_name, score, total, created_at.
    Falls back to empty list if Firestore unavailable.
    """
    if not _firebase_available or _db is None:
        return []
    try:
        query = (
            _db.collection("quiz_scores")
            .order_by("score", direction=firestore.Query.DESCENDING)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = query.stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            results.append({
                "player_name": d.get("player_name", "Anonymous"),
                "score": d.get("score", 0),
                "total": d.get("total", 10),
                "percentage": d.get("percentage", 0),
                "created_at": d.get("created_at", datetime.now(timezone.utc)).isoformat()
                if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at", "")),
            })
        return results
    except Exception as e:
        logger.error("Error fetching leaderboard: %s", e)
        return []
