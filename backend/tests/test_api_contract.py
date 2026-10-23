import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from google.api_core.exceptions import GoogleAPICallError
from openai import OpenAIError

from app.auth import current_uid
from app.models import ChatInput
from app.routers import chat as chat_router
from app.services import records_ref
from main import app, database_error


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
    @patch("app.auth.auth.verify_id_token", side_effect=ValueError("invalid"))
    def test_invalid_token_is_rejected(self, _verify, _firebase_app):
        token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
        with self.assertRaises(HTTPException) as error:
            current_uid(token)
        self.assertEqual(error.exception.status_code, 401)

    @patch("app.auth.firebase_app")
    @patch("app.auth.auth.verify_id_token", side_effect=firebase_auth.ExpiredIdTokenError("expired", None))
    def test_expired_token_is_rejected(self, _verify, _firebase_app):
        token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired")
        with self.assertRaises(HTTPException) as error:
            current_uid(token)
        self.assertEqual(error.exception.status_code, 401)

    def test_database_error_has_safe_503_response(self):
        self.assertIn(GoogleAPICallError, app.exception_handlers)
        response = asyncio.run(database_error(None, GoogleAPICallError("private backend detail")))
        self.assertEqual(response.status_code, 503)
        self.assertIn("데이터베이스", json.loads(response.body)["detail"])
        self.assertNotIn("private backend detail", response.body.decode())

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
    @patch.dict("os.environ", {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
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
        self.assertEqual(openai.call_args.kwargs["base_url"], "https://api.openai.com/v1")
        kwargs = openai.return_value.responses.create.call_args.kwargs
        self.assertIn("최근 7개 기록 평균: 20분", kwargs["instructions"])
        self.assertFalse(kwargs["store"])
        self.assertEqual(kwargs["max_output_tokens"], 400)
        self.assertEqual(ref.set.call_args.args[0]["messages"][1]["role"], "assistant")

    @patch("app.routers.chat.OpenAI")
    @patch("app.routers.chat.user_summary")
    @patch("app.routers.chat.conversations_ref")
    @patch.dict("os.environ", {
        "AI_PROVIDER": "codyssey", "CODYSSEY_API_KEY": "virtual-test-key",
        "CODYSSEY_MODEL": "test-gpt-model", "OPENAI_API_KEY": "official-test-key",
    })
    def test_codyssey_uses_virtual_key_and_chat_completions(self, conversations, summary, openai):
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
        response = openai.return_value.chat.completions.create.return_value
        response.choices = [MagicMock(message=MagicMock(content="최근 독서량이 늘었습니다."))]

        result = chat_router.chat(ChatInput(message="최근 추세는?"), uid="reader-a")

        self.assertEqual(result["reply"], "최근 독서량이 늘었습니다.")
        self.assertEqual(len(result["messages"]), 2)
        self.assertEqual(openai.call_args.kwargs["api_key"], "virtual-test-key")
        self.assertEqual(openai.call_args.kwargs["base_url"], "https://copa.codyssey.kr/v1")
        kwargs = openai.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "test-gpt-model")
        self.assertIn("최근 7개 기록 평균: 20분", kwargs["messages"][0]["content"])
        self.assertEqual(kwargs["messages"][0]["role"], "system")
        self.assertEqual(kwargs["max_tokens"], 4000)
        self.assertEqual(ref.set.call_args.args[0]["messages"][1]["role"], "assistant")

    @patch.dict("os.environ", {
        "AI_PROVIDER": "codyssey", "CODYSSEY_API_KEY": "", "CODYSSEY_MODEL": "test-gpt-model",
        "OPENAI_API_KEY": "official-test-key",
    })
    def test_codyssey_never_falls_back_to_official_key(self):
        with self.assertRaises(HTTPException) as error:
            chat_router.chat(ChatInput(message="최근 추세는?"), uid="reader-a")
        self.assertEqual(error.exception.status_code, 503)

    @patch("app.routers.chat.OpenAI")
    @patch("app.routers.chat.user_summary", return_value={"count": 0})
    @patch("app.routers.chat.conversations_ref")
    @patch.dict("os.environ", {
        "AI_PROVIDER": "codyssey", "CODYSSEY_API_KEY": "virtual-test-key", "CODYSSEY_MODEL": "test-gpt-model",
    })
    def test_ai_failure_has_safe_502_response_and_does_not_save(self, conversations, _summary, openai):
        openai.return_value.chat.completions.create.side_effect = OpenAIError("private provider detail")
        with self.assertRaises(HTTPException) as error:
            chat_router.chat(ChatInput(message="최근 추세는?"), uid="reader-a")
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("private provider detail", error.exception.detail)
        conversations.return_value.document.assert_not_called()

    def test_chat_prompt_omits_percentage_when_trend_is_unknown(self):
        summary = {
            "period": {"start": "2026-10-20", "end": "2026-10-20"},
            "count": 1, "total_value": 20, "average_value": 20,
            "max_value": 20, "min_value": 20, "best_date": "2026-10-20", "best_day_total": 20,
            "recent_average": 20, "previous_average": None, "trend": "데이터 부족",
            "trend_percent": None, "this_month_total": 20, "last_month_total": 0,
            "monthly_totals": {"2026-10": 20},
        }
        instructions = chat_router.system_instructions(summary)
        self.assertIn("추세: 데이터 부족", instructions)
        self.assertNotIn("None%", instructions)


if __name__ == "__main__":
    unittest.main()
