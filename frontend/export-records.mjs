export function serializeRecords(records, exportedAt) {
  return `${JSON.stringify({
    exported_at: exportedAt,
    count: records.length,
    records: records.map((record) => ({
      id: record.id,
      date: record.date,
      value: record.value,
      memo: record.memo ?? "",
      created_at: record.created_at ?? null,
      updated_at: record.updated_at ?? null,
    })),
  }, null, 2)}\n`;
}
