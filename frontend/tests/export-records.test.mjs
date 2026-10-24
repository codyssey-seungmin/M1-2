import assert from "node:assert/strict";
import test from "node:test";

import { serializeRecords } from "../export-records.mjs";

test("JSON 내보내기는 전체 기록과 날짜·시간·메모를 포함한다", () => {
  const records = [
    { id: "a", date: "2026-10-24", value: 40, memo: "판타지 소설 독서", created_at: "2026-10-24T10:00:00Z" },
    { id: "b", date: "2026-10-23", value: 25, memo: "" },
  ];
  const exported = JSON.parse(serializeRecords(records, "2026-10-24T12:00:00Z"));

  assert.equal(exported.count, 2);
  assert.equal(exported.exported_at, "2026-10-24T12:00:00Z");
  assert.deepEqual(exported.records.map(({ date, value, memo }) => ({ date, value, memo })), [
    { date: "2026-10-24", value: 40, memo: "판타지 소설 독서" },
    { date: "2026-10-23", value: 25, memo: "" },
  ]);
  assert.equal(exported.records[1].created_at, null);
});

test("기록이 없어도 빈 JSON 파일을 만들 수 있다", () => {
  assert.deepEqual(JSON.parse(serializeRecords([], "2026-10-24T12:00:00Z")).records, []);
});
