import unittest
from unittest.mock import patch
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools
from agent import VoteGuideAgent

MOCK_STAGES = {
  "stages": [
    {"id": 1, "name": "Election Announcement", "icon": "campaign", "duration": "1-7 days",
     "description": "Test description", "key_actions": ["Action 1"],
     "who_is_involved": ["Commission"], "citizen_action": "Stay informed"},
    {"id": 5, "name": "Voting Day", "icon": "how_to_vote", "duration": "1 day",
     "description": "Voting description", "key_actions": ["Cast ballot"],
     "who_is_involved": ["Voters"], "citizen_action": "Go vote"}
  ]
}

MOCK_GLOSSARY = {
  "terms": [
    {"term": "Ballot", "definition": "Official voting document"},
    {"term": "Democracy", "definition": "Government by the people"}
  ]
}

MOCK_QUIZ = {
  "questions": [
    {"id": 1, "question": "First stage?", "options": ["A","B","C","D"],
     "correct": 2, "explanation": "Because announcement is first"}
  ]
}


class TestTools(unittest.TestCase):

    @patch("tools.load_json_file", return_value=MOCK_STAGES)
    def test_get_all_stages_returns_list(self, mock):
        result = tools.get_all_stages()
        self.assertIsInstance(result, list)

    @patch("tools.load_json_file", return_value=MOCK_STAGES)
    def test_get_all_stages_sorted_by_id(self, mock):
        result = tools.get_all_stages()
        ids = [s["id"] for s in result]
        self.assertEqual(ids, sorted(ids))

    @patch("tools.load_json_file", return_value=MOCK_STAGES)
    def test_get_stage_by_id_found(self, mock):
        result = tools.get_stage_by_id(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Election Announcement")

    @patch("tools.load_json_file", return_value=MOCK_STAGES)
    def test_get_stage_by_id_not_found(self, mock):
        result = tools.get_stage_by_id(99)
        self.assertIsNone(result)

    @patch("tools.load_json_file", return_value=MOCK_GLOSSARY)
    def test_search_glossary_exact(self, mock):
        result = tools.search_glossary("ballot")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["term"], "Ballot")

    @patch("tools.load_json_file", return_value=MOCK_GLOSSARY)
    def test_search_glossary_partial(self, mock):
        result = tools.search_glossary("dem")
        self.assertEqual(len(result), 1)

    @patch("tools.load_json_file", return_value=MOCK_GLOSSARY)
    def test_search_glossary_no_match(self, mock):
        result = tools.search_glossary("zzznomatch")
        self.assertEqual(len(result), 0)

    @patch("tools.load_json_file", return_value=MOCK_QUIZ)
    def test_quiz_safe_strips_correct(self, mock):
        result = tools.get_quiz_questions_safe()
        for q in result:
            self.assertNotIn("correct", q)

    @patch("tools.load_json_file", return_value=MOCK_QUIZ)
    def test_check_quiz_correct_answer(self, mock):
        result = tools.check_quiz_answer(1, 2)
        self.assertTrue(result["correct"])
        self.assertIn("explanation", result)

    @patch("tools.load_json_file", return_value=MOCK_QUIZ)
    def test_check_quiz_wrong_answer(self, mock):
        result = tools.check_quiz_answer(1, 0)
        self.assertFalse(result["correct"])
        self.assertIn("explanation", result)

    @patch("tools.load_json_file", return_value=MOCK_QUIZ)
    def test_check_quiz_invalid_id(self, mock):
        result = tools.check_quiz_answer(999, 0)
        self.assertIn("error", result)


class TestAgent(unittest.TestCase):

    @patch("agent.genai.GenerativeModel")
    @patch("agent.VoteGuideAgent._load_json", return_value={})
    def test_detect_stage_registration(self, mock_load, mock_model):
        agent = VoteGuideAgent.__new__(VoteGuideAgent)
        agent.stages = {"stages": []}
        agent.glossary = {}
        agent.roles = {}
        agent.history = []
        result = agent._detect_relevant_stage("how do I register to vote")
        self.assertEqual(result, 2)

    @patch("agent.genai.GenerativeModel")
    @patch("agent.VoteGuideAgent._load_json", return_value={})
    def test_detect_stage_voting(self, mock_load, mock_model):
        agent = VoteGuideAgent.__new__(VoteGuideAgent)
        agent.stages = {"stages": []}
        agent.history = []
        result = agent._detect_relevant_stage("what happens on voting day")
        self.assertEqual(result, 5)

    @patch("agent.genai.GenerativeModel")
    @patch("agent.VoteGuideAgent._load_json", return_value={})
    def test_detect_stage_no_match(self, mock_load, mock_model):
        agent = VoteGuideAgent.__new__(VoteGuideAgent)
        agent.stages = {"stages": []}
        agent.history = []
        result = agent._detect_relevant_stage("what is the weather like today")
        self.assertIsNone(result)


class TestAPI(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        with patch("agent.genai.GenerativeModel"), \
             patch("agent.VoteGuideAgent._load_json", return_value={}):
            import main
            self.client = TestClient(main.app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_chat_empty_message_rejected(self):
        response = self.client.post("/api/chat", json={"message": "", "language": "en"})
        self.assertEqual(response.status_code, 422)

    def test_chat_long_message_rejected(self):
        response = self.client.post("/api/chat", json={"message": "x" * 501, "language": "en"})
        self.assertEqual(response.status_code, 422)

    @patch("tools.load_json_file", return_value=MOCK_QUIZ)
    def test_quiz_endpoint_no_correct_field(self, mock):
        response = self.client.get("/api/quiz")
        self.assertEqual(response.status_code, 200)
        questions = response.json()["questions"]
        for q in questions:
            self.assertNotIn("correct", q)


if __name__ == "__main__":
    unittest.main()
