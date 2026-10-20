"""Create a reproducible synthetic reading dataset for one Firebase user."""

import argparse
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from app.firebase import get_db  # noqa: E402


BOOKS = ("달과 6펜스", "아주 작은 습관의 힘", "어린 왕자", "생각에 관한 생각")


def make_sample_records(today: date | None = None) -> list[dict]:
    today = today or date.today()
    result = []
    for index in range(120):
        day = today - timedelta(days=119 - index)
        weekend_bonus = 14 if day.weekday() >= 5 else 0
        minutes = 18 + (index * 7 % 29) + weekend_bonus + index // 30 * 3
        result.append({"date": day.isoformat(), "value": minutes, "memo": f"과제용 예시 기록 · {BOOKS[index // 30]}"})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="120개의 과제용 독서 시계열 데이터를 생성합니다.")
    parser.add_argument("--uid", help="Firebase 익명 인증으로 발급된 사용자 UID")
    parser.add_argument("--apply", action="store_true", help="Firestore에 실제로 저장")
    args = parser.parse_args()
    records = make_sample_records()
    if not args.apply:
        print(f"미리보기: {len(records)}개, 기간 {records[0]['date']} ~ {records[-1]['date']}")
        print("실제 저장은 --uid <사용자 UID> --apply를 함께 사용하세요.")
        return
    if not args.uid or not args.uid.isalnum() or len(args.uid) > 128:
        parser.error("--apply 사용 시 올바른 --uid가 필요합니다.")
    collection = get_db().collection("data").document(args.uid).collection("records")
    batch = get_db().batch()
    added = 0
    for record in records:
        ref = collection.document(f"sample-{record['date']}")
        if ref.get().exists:
            continue
        batch.set(ref, record)
        added += 1
    if added:
        batch.commit()
    print(f"과제용 예시 데이터 {added}개 저장 완료, 기존 예시 기록 {len(records) - added}개 유지")


if __name__ == "__main__":
    main()
