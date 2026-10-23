import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.models import ConversationInput, ReadingInput
from app.routers import conversations, data
from app.services import list_records, read_owned_document, valid_document_id


class HandlerTests(unittest.TestCase):
    @patch("app.services.records_ref")
    def test_record_list_sorts_same_day_by_creation_time(self, records_ref):
        def snapshot(document_id, created_at, day="2026-10-20"):
            item = MagicMock(id=document_id)
            item.to_dict.return_value = {"date": day, "value": 30, "created_at": created_at}
            return item

        records_ref.return_value.stream.return_value = [
            snapshot("newer-id", "2026-10-20T09:00:00+00:00"),
            snapshot("older-id", "2026-10-20T10:00:00+00:00"),
            snapshot("previous-day", "2026-10-19T23:00:00+00:00", "2026-10-19"),
        ]
        self.assertEqual(
            [item["id"] for item in list_records("reader-a")],
            ["older-id", "newer-id", "previous-day"],
        )

    @patch("app.routers.data.serialize_doc", return_value={"id": "record-1"})
    @patch("app.routers.data.records_ref")
    def test_data_create_update_delete_use_the_users_collection(self, records_ref, serialize_doc):
        collection = records_ref.return_value
        ref = collection.document.return_value
        ref.get.return_value.exists = True
        payload = ReadingInput(date="2026-10-20", value=35, memo="테스트")

        self.assertEqual(data.create_data(payload, uid="reader-a"), {"id": "record-1"})
        self.assertEqual(data.update_data("record-1", payload, uid="reader-a"), {"id": "record-1"})
        self.assertEqual(data.delete_data("record-1", uid="reader-a").status_code, 204)
        self.assertEqual(records_ref.call_args_list[0].args, ("reader-a",))
        self.assertTrue(all(call.args == ("reader-a",) for call in records_ref.call_args_list))
        self.assertEqual(ref.set.call_args.args[0]["value"], 35)
        self.assertEqual(ref.update.call_args.args[0]["date"], "2026-10-20")
        ref.delete.assert_called_once()

    def test_missing_or_invalid_document_is_rejected(self):
        collection = MagicMock()
        collection.document.return_value.get.return_value.exists = False
        with self.assertRaises(HTTPException) as missing:
            read_owned_document(collection, "record-1")
        self.assertEqual(missing.exception.status_code, 404)
        with self.assertRaises(HTTPException) as invalid:
            valid_document_id("../reader-b")
        self.assertEqual(invalid.exception.status_code, 400)

    @patch("app.routers.conversations.serialize_doc", return_value={"id": "dialogue-1"})
    @patch("app.routers.conversations.conversations_ref")
    def test_conversation_save_load_delete(self, conversations_ref, serialize_doc):
        collection = conversations_ref.return_value
        ref = collection.document.return_value
        ref.get.return_value.exists = True
        payload = ConversationInput(title="내 독서 습관", messages=[{"role": "user", "content": "어때?"}])

        self.assertEqual(conversations.create_conversation(payload, uid="reader-a"), {"id": "dialogue-1"})
        self.assertEqual(conversations.get_conversation("dialogue-1", uid="reader-a"), {"id": "dialogue-1"})
        self.assertEqual(conversations.delete_conversation("dialogue-1", uid="reader-a").status_code, 204)
        self.assertTrue(all(call.args == ("reader-a",) for call in conversations_ref.call_args_list))
        self.assertEqual(ref.set.call_args.args[0]["messages"][0]["content"], "어때?")
        ref.delete.assert_called_once()

    @patch("app.routers.conversations.conversations_ref")
    def test_conversation_list_omits_messages_but_detail_can_include_them(self, conversations_ref):
        older = MagicMock(id="old")
        older.to_dict.return_value = {
            "title": "이전 대화", "messages": [{"role": "user", "content": "안녕"}],
            "created_at": "2026-10-18", "updated_at": "2026-10-18",
        }
        newer = MagicMock(id="new")
        newer.to_dict.return_value = {
            "title": "최근 대화", "messages": [{"role": "user", "content": "질문"}, {"role": "assistant", "content": "답변"}],
            "created_at": "2026-10-19", "updated_at": "2026-10-20",
        }
        conversations_ref.return_value.stream.return_value = [older, newer]
        items = conversations.list_conversations(uid="reader-a")
        self.assertEqual([item["id"] for item in items], ["new", "old"])
        self.assertEqual(items[0]["message_count"], 2)
        self.assertNotIn("messages", items[0])


if __name__ == "__main__":
    unittest.main()
