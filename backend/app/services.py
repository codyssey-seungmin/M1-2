from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .firebase import get_db


def records_ref(uid: str):
    return get_db().collection("data").document(uid).collection("records")


def conversations_ref(uid: str):
    return get_db().collection("conversations").document(uid).collection("items")


def valid_document_id(document_id: str) -> str:
    if not document_id or len(document_id) > 128 or not all(c.isalnum() or c in "-_" for c in document_id):
        raise HTTPException(status_code=400, detail="잘못된 문서 ID입니다.")
    return document_id


def serialize_doc(snapshot):
    data = snapshot.to_dict() or {}
    for key in ("date", "created_at", "updated_at"):
        if isinstance(data.get(key), (date, datetime)):
            data[key] = data[key].isoformat()
    return {"id": snapshot.id, **data}


def list_records(uid: str) -> list[dict]:
    items = [serialize_doc(doc) for doc in records_ref(uid).stream()]
    return sorted(items, key=lambda item: (item["date"], item["id"]), reverse=True)


def read_owned_document(collection, document_id: str):
    snapshot = collection.document(valid_document_id(document_id)).get()
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    return snapshot


def calculate_summary(records: list[dict], today: date | None = None) -> dict:
    today = today or datetime.now(ZoneInfo("Asia/Seoul")).date()
    if not records:
        return {
            "period": {"start": None, "end": None}, "count": 0, "total_value": 0,
            "average_value": 0, "max_value": 0, "min_value": 0,
            "best_date": None, "best_day_total": 0, "recent_average": None, "previous_average": None,
            "trend": "데이터 부족", "trend_percent": None,
            "this_month_total": 0, "last_month_total": 0,
            "weekly_series": [{"date": (today - timedelta(days=6 - i)).isoformat(), "value": 0} for i in range(7)],
            "monthly_totals": {},
        }

    chronological = sorted(records, key=lambda item: (item["date"], item.get("id", "")))
    values = [float(item["value"]) for item in chronological]
    daily = defaultdict(float)
    monthly = defaultdict(float)
    for item in chronological:
        value = float(item["value"])
        daily[item["date"]] += value
        monthly[item["date"][:7]] += value

    recent = values[-7:]
    previous = values[-14:-7]
    recent_average = round(mean(recent), 1)
    previous_average = round(mean(previous), 1) if len(previous) == 7 else None
    trend = "데이터 부족"
    change = None
    if len(recent) == 7 and previous_average is not None and previous_average > 0:
        change = round((mean(recent) / mean(previous) - 1) * 100, 1)
        trend = "상승" if change >= 5 else "하락" if change <= -5 else "유지"

    last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    best_date, best_day_total = max(daily.items(), key=lambda item: item[1])
    return {
        "period": {"start": chronological[0]["date"], "end": chronological[-1]["date"]},
        "count": len(records),
        "total_value": round(sum(values), 1),
        "average_value": round(mean(values), 1),
        "max_value": max(values),
        "min_value": min(values),
        "best_date": best_date,
        "best_day_total": round(best_day_total, 1),
        "recent_average": recent_average,
        "previous_average": previous_average,
        "trend": trend,
        "trend_percent": change,
        "this_month_total": round(monthly.get(today.strftime("%Y-%m"), 0), 1),
        "last_month_total": round(monthly.get(last_month, 0), 1),
        "weekly_series": [
            {"date": (today - timedelta(days=6 - i)).isoformat(), "value": round(daily[(today - timedelta(days=6 - i)).isoformat()], 1)}
            for i in range(7)
        ],
        "monthly_totals": {key: round(value, 1) for key, value in sorted(monthly.items())},
    }


def user_summary(uid: str) -> dict:
    return calculate_summary(list_records(uid))
