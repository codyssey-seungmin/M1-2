export function getRecordView(records, selectedMonth = "", visibleCount = 10) {
  const months = [...new Set(records.map((record) => record.date.slice(0, 7)))]
    .sort()
    .reverse();
  const month = months.includes(selectedMonth) ? selectedMonth : "";
  const filtered = month
    ? records.filter((record) => record.date.startsWith(month))
    : records;
  const visible = filtered.slice(0, visibleCount);
  return {
    months,
    month,
    visible,
    total: filtered.length,
    remaining: filtered.length - visible.length,
  };
}
