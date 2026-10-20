from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from ..auth import current_uid
from ..models import ConversationInput
from ..services import conversations_ref, read_owned_document, serialize_doc


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", status_code=201)
def create_conversation(payload: ConversationInput, uid: str = Depends(current_uid)):
    now = datetime.now(timezone.utc)
    ref = conversations_ref(uid).document()
    ref.set({"title": payload.title, "messages": [message.model_dump() for message in payload.messages], "created_at": now, "updated_at": now})
    return serialize_doc(ref.get())


@router.get("")
def list_conversations(uid: str = Depends(current_uid)):
    items = [serialize_doc(doc) for doc in conversations_ref(uid).stream()]
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return [{"id": item["id"], "title": item["title"], "created_at": item["created_at"], "updated_at": item["updated_at"], "message_count": len(item.get("messages", []))} for item in items]


@router.get("/{id}")
def get_conversation(id: str, uid: str = Depends(current_uid)):
    return serialize_doc(read_owned_document(conversations_ref(uid), id))


@router.delete("/{id}", status_code=204)
def delete_conversation(id: str, uid: str = Depends(current_uid)):
    collection = conversations_ref(uid)
    read_owned_document(collection, id)
    collection.document(id).delete()
    return Response(status_code=204)
