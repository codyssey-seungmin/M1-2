from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from ..auth import current_uid
from ..models import ReadingInput
from ..services import list_records, read_owned_document, records_ref, serialize_doc, user_summary


router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", status_code=201)
def create_data(payload: ReadingInput, uid: str = Depends(current_uid)):
    now = datetime.now(timezone.utc)
    ref = records_ref(uid).document()
    ref.set({**payload.model_dump(mode="json"), "created_at": now, "updated_at": now})
    return serialize_doc(ref.get())


@router.get("")
def get_data(uid: str = Depends(current_uid)):
    return list_records(uid)


@router.get("/summary")
def get_summary(uid: str = Depends(current_uid)):
    return user_summary(uid)


@router.put("/{id}")
def update_data(id: str, payload: ReadingInput, uid: str = Depends(current_uid)):
    collection = records_ref(uid)
    read_owned_document(collection, id)
    ref = collection.document(id)
    ref.update({**payload.model_dump(mode="json"), "updated_at": datetime.now(timezone.utc)})
    return serialize_doc(ref.get())


@router.delete("/{id}", status_code=204)
def delete_data(id: str, uid: str = Depends(current_uid)):
    collection = records_ref(uid)
    read_owned_document(collection, id)
    collection.document(id).delete()
    return Response(status_code=204)
