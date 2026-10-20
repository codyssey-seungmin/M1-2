import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import current_uid
from app.models import ChatInput
from app.routers import chat as chat_router
from app.services import records_ref
from main import app


class APIContractTests(unittest.TestCase):
    def test_required_routes_are_in_swagger(self):
        paths = app.openapi()["paths"]
        expected = {
            "/api/data": {"get", "post"},
            "/api/data/summary": {"get"},
            "/api/data/{id}": {"put", "delete"},
            "/api/conversations": {"get", "post"},
            "/api/conversations/{id}": {"get", "delete"},
            "/api/chat": {"post"},
        }
        for path, methods in expected.items():
            self.assertTrue(methods.issubset(paths[path].keys()), path)

    def test_missing_token_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            current_uid(None)
        self.assertEqual(error.exception.status_code, 401)

    @patch("app.auth.firebase_app")
    @patch("app.auth.auth.verify_id_token", return_value={"uid": "reader-a"})
    def test_verified_token_supplies_uid(self, verify, firebase_app):
        token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="example")
        self.assertEqual(current_uid(token), "reader-a")
        verify.assert_called_once_with("example", app=firebase_app.return_value)

    @patch("app.services.get_db")
    def test_record_path_is_scoped_to_verified_uid(self, get_db):
        records_ref("reader-a")
        get_db.return_value.collection.assert_called_once_with("data")
        get_db.return_value.collection.return_value.document.assert_called_once_with("reader-a")

    @patch("app.routers.chat.OpenAI")
    @patch("app.routers.chat.user_summary")
    @patch("app.routers.chat.conversations_ref")
    @patch("app.routers.chat.openai_model", return_value="test-model")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_chat_injects_summary_and_saves_dialogue(self, _model, conversations, summary, openai):
        summary.return_value = {
            "period": {"start": "2026-10-01", "end": "2026-10-14"},
            "count": 14, "total_value": 210, "average_value": 15,
            "max_value": 20, "min_value": 10, "best_date": "2026-10-08", "best_day_total": 20,
            "recent_average": 20, "previous_average": 10, "trend": "상승",
            "trend_percent": 100, "this_month_total": 210, "last_month_total": 0,
            "monthly_totals": {"2026-10": 210},
        }
        ref = MagicMock(id="conversation-1")
        ref.id = "conversation-1"
        conversations.return_value.document.return_value = ref
        openai.return_value.responses.create.return_value.output_text = "최근 독서량이 늘었습니다."

        result = chat_router.chat(ChatInput(message="최근 추세는?"), uid="reader-a")

        self.assertEqual(result["conversation_id"], "conversation-1")
        self.assertEqual(len(result["messages"]), 2)
        kwargs = openai.return_value.responses.create.call_args.kwargs
        self.assertIn("최근 7개 기록 평균: 20분", kwargs["instructions"])
        self.assertFalse(kwargs["store"])
        self.assertEqual(kwargs["max_output_tokens"], 400)
        self.assertEqual(ref.set.call_args.args[0]["messages"][1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
