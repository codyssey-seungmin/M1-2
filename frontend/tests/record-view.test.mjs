import test from "node:test";
import assert from "node:assert/strict";

import { getRecordView } from "../record-view.mjs";

const records = Array.from({ length: 121 }, (_, index) => ({
  id: String(index),
  date:
    index < 31
      ? `2026-10-${String(31 - index).padStart(2, "0")}`
      : `2026-09-${String(30 - ((index - 31) % 30)).padStart(2, "0")}`,
}));

test("기본 목록은 121개 중 최신 10개만 보인다", () => {
  const view = getRecordView(records);
  assert.equal(view.total, 121);
  assert.equal(view.visible.length, 10);
  assert.equal(view.remaining, 111);
});

test("더 보기를 누르면 다음 10개가 보인다", () => {
  const view = getRecordView(records, "", 20);
  assert.equal(view.visible.length, 20);
  assert.equal(view.remaining, 101);
});

test("월별 필터와 더 보기를 함께 적용한다", () => {
  const first = getRecordView(records, "2026-10", 10);
  const next = getRecordView(records, "2026-10", 20);
  assert.equal(first.total, 31);
  assert.equal(first.visible.length, 10);
  assert.equal(next.visible.length, 20);
  assert.ok(next.visible.every((record) => record.date.startsWith("2026-10")));
});

test("기록이 없어져 선택한 월이 사라지면 전체 기간으로 돌아간다", () => {
  const view = getRecordView(records, "2026-08", 10);
  assert.equal(view.month, "");
  assert.equal(view.total, 121);
});
