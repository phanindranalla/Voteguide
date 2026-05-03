import os
import json
import logging
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
You are VoteGuide, a friendly and strictly impartial election education assistant. Your sole purpose is to help citizens understand the democratic process clearly, confidently, and in plain language.

Core behaviour rules:
- Explain election concepts in simple, jargon-free language
- When technical terms are necessary, define them immediately
- You are politically neutral at all times — never endorse any party, candidate, political ideology, or opinion
- Cover the universal election process applicable to most democracies worldwide
- Keep answers under 120 words unless the user explicitly asks for more detail
- If a question is politically partisan, politely redirect: "I focus on the election process itself rather than political opinions — here is what I can tell you about how this part of the process works..."
- Always end your response with one short follow-up question to encourage continued learning
- Never discuss current election results, polling numbers, specific politicians, or party performance
- Never make up facts — if unsure, say so clearly

You have deep knowledge of:
- The 8 universal stages of a general election
- Voter rights and responsibilities
- Roles of Election Commission, candidates, observers, voters
- Common election terminology and concepts
- How different voting systems work globally
"""


class VoteGuideAgent:
    def __init__(self) -> None:
        """Initialize VoteGuide agent with Gemini model and preloaded election data."""
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT
        )
        self.chat_session = self.model.start_chat(history=[])
        self.stages = self._load_json("data/election_stages.json")
        self.glossary = self._load_json("data/glossary.json")
        self.roles = self._load_json("data/roles.json")
        self.history = []
        logger.info("VoteGuideAgent initialized successfully")

    def _load_json(self, filepath: str) -> dict:
        """Load and return JSON data from filepath. Returns empty dict on error."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return {}

    def chat(self, user_message: str) -> dict:
        """Send message to Gemini and return structured response.

        Args:
            user_message: The user's question or input

        Returns:
            dict with keys: response (str), suggested_stage (int or None),
            history_length (int)
        """
        try:
            stage_names = [s["name"] for s in self.stages.get("stages", [])]
            enriched_prompt = f"""User question: {user_message}

Available election stages for reference: {", ".join(stage_names)}

Answer helpfully, stay politically neutral, and end with one follow-up question."""

            response = self.chat_session.send_message(enriched_prompt)
            response_text = response.text

            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": response_text})

            suggested = self._detect_relevant_stage(user_message)
            logger.info(f"Chat response generated, suggested_stage={suggested}")

            return {
                "response": response_text,
                "suggested_stage": suggested,
                "history_length": len(self.history)
            }
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": "I am having trouble connecting right now. Please try again in a moment.",
                "suggested_stage": None,
                "history_length": len(self.history)
            }

    def _detect_relevant_stage(self, message: str) -> int | None:
        """Detect which election stage is most relevant to the user's message based on keywords.

        Returns stage id (1-8) or None if no match found.
        """
        message_lower = message.lower()

        keyword_map = {
            1: ["announcement", "declared", "schedule", "dates", "when is"],
            2: ["register", "registration", "voter id", "enroll", "sign up"],
            3: ["nomination", "candidate", "file", "eligib", "contest"],
            4: ["campaign", "rally", "manifesto", "advertis", "debate"],
            5: ["vote", "ballot", "polling station", "voting day", "cast"],
            6: ["count", "tally", "counting", "results coming", "tabulate"],
            7: ["result", "winner", "declared won", "officially", "gazette"],
            8: ["transition", "sworn", "oath", "takes office", "handover"]
        }

        for stage_id, keywords in keyword_map.items():
            if any(kw in message_lower for kw in keywords):
                return stage_id
        return None

    def get_glossary_term(self, term: str) -> dict | None:
        """Search glossary for a term by exact or partial case-insensitive match.

        Args:
            term: The election term to search for

        Returns:
            Matching glossary entry dict or None
        """
        term_lower = term.lower()
        terms = self.glossary.get("terms", [])

        # First try exact match
        for item in terms:
            if item["term"].lower() == term_lower:
                return item

        # Then try partial match
        for item in terms:
            if term_lower in item["term"].lower():
                return item

        return None
