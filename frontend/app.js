import { initializeApp } from "@firebase/app";
import { getAuth, onAuthStateChanged, signInAnonymously } from "@firebase/auth";
import { serializeRecords } from "./export-records.mjs";
import { getRecordView } from "./record-view.mjs";

const config = window.APP_CONFIG || {};
const RECORD_PAGE_SIZE = 10;
const THEME_STORAGE_KEY = "pageful-theme";
const state = {
  user: null,
  records: [],
  recordMonth: "",
  recordVisibleCount: RECORD_PAGE_SIZE,
  summary: null,
  conversations: [],
  conversationId: null,
  messages: [],
};
const $ = (id) => document.getElementById(id);

function applyTheme(theme) {
  const dark = theme === "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  $("theme-toggle").textContent = dark ? "라이트 모드" : "다크 모드";
  $("theme-toggle").setAttribute("aria-pressed", String(dark));
  document.querySelector('meta[name="theme-color"]').content = dark
    ? "#211e1b"
    : "#f6f0e7";
}

function initializeTheme() {
  try {
    applyTheme(localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    applyTheme("light");
  }
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    // 저장소가 차단된 브라우저에서는 현재 화면에만 테마를 적용합니다.
  }
}

function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function setStatus(message, kind = "") {
  const element = $("app-status");
  element.textContent = message;
  element.className = `status-banner ${kind}`.trim();
}

function setFeedback(id, message) {
  $(id).textContent = message;
}

function formatMinutes(value) {
  const minutes = Math.round(Number(value) || 0);
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}시간 ${minutes % 60}분` : `${minutes}분`;
}

function readableDate(value) {
  if (!value) return "—";
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ko-KR", {
        month: "short",
        day: "numeric",
      }).format(date);
}

function prettyTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("ko-KR", {
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(date);
}

function setFormsDisabled(disabled) {
  for (const selector of [
    "#record-form input",
    "#record-form button",
    "#record-month",
    "#chat-form input",
    "#chat-form button",
    "#new-chat",
    "#copy-user-id",
  ]) {
    document.querySelectorAll(selector).forEach((element) => {
      element.disabled = disabled;
    });
  }
}

async function api(path, options = {}) {
  if (!state.user) throw new Error("사용자 인증을 기다리고 있습니다.");
  const token = await state.user.getIdToken();
  const response = await fetch(
    `${config.apiBaseUrl.replace(/\/$/, "")}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    },
  );
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? "입력 내용을 다시 확인해 주세요."
      : detail || "요청을 처리하지 못했습니다.";
    throw new Error(message);
  }
  return body;
}

function renderSummary() {
  const summary = state.summary;
  if (!summary) return;
  $("month-total").textContent = formatMinutes(summary.this_month_total);
  $("record-count").textContent = `${summary.count}개`;
  $("record-period").textContent = summary.count
    ? `${summary.period.start} ~ ${summary.period.end}`
    : "아직 기록이 없어요";
  $("trend-value").textContent = summary.trend;
  $("trend-detail").textContent =
    summary.trend_percent === null
      ? "비교할 기록이 더 필요해요"
      : `직전 7개 기록 대비 ${summary.trend_percent > 0 ? "+" : ""}${summary.trend_percent}%`;
  $("month-comparison").textContent = summary.count
    ? `지난달 ${formatMinutes(summary.last_month_total)}`
    : "첫 기록을 추가해 보세요";
  $("total-time").textContent = formatMinutes(summary.total_value);
  $("average-time").textContent = `${summary.average_value}분`;
  $("best-day").textContent = summary.best_date
    ? `${readableDate(summary.best_date)} · ${summary.best_day_total}분`
    : "—";
  $("insight-copy").textContent = summary.count
    ? `${summary.period.start}부터 ${summary.period.end}까지 ${summary.count}개의 독서 기록이 있어요. 최근 흐름은 ${summary.trend}입니다.`
    : "아직 독서 기록이 없습니다. 오늘 읽은 시간을 적으면 나만의 요약이 만들어집니다.";
  renderChart(summary.weekly_series);
}

function renderChart(series) {
  const chart = $("week-chart");
  chart.replaceChildren();
  const maxValue = Math.max(
    60,
    ...series.map((item) => Number(item.value) || 0),
  );
  const axis = document.createElement("div");
  axis.className = "chart-axis";
  for (const text of [
    `${Math.ceil(maxValue)}분`,
    `${Math.ceil(maxValue / 2)}분`,
    "0분",
  ]) {
    const label = document.createElement("span");
    label.textContent = text;
    axis.append(label);
  }
  const bars = document.createElement("div");
  bars.className = "chart-bars";
  for (const [index, item] of series.entries()) {
    const column = document.createElement("div");
    column.className = "chart-column";
    const track = document.createElement("div");
    track.className = "chart-track";
    const bar = document.createElement("div");
    bar.className = `chart-bar${index === 6 ? " highlight" : ""}`;
    bar.style.height = `${Math.max(0, Math.min(100, (Number(item.value) / maxValue) * 100))}%`;
    bar.title = `${item.date}: ${item.value}분`;
    track.append(bar);
    const label = document.createElement("span");
    label.textContent = new Intl.DateTimeFormat("ko-KR", {
      weekday: "short",
    }).format(new Date(`${item.date}T12:00:00`));
    column.append(track, label);
    bars.append(column);
  }
  chart.append(axis, bars);
  chart.setAttribute(
    "aria-label",
    `최근 7일 독서 시간: ${series.map((item) => `${item.date} ${item.value}분`).join(", ")}`,
  );
  const top = [...series].sort((a, b) => b.value - a.value)[0];
  $("chart-note").textContent = top?.value
    ? `${readableDate(top.date)}에 ${formatMinutes(top.value)} 읽어 최근 7일 중 가장 길었어요.`
    : "최근 7일의 독서 기록이 아직 없습니다.";
}

function renderRecords() {
  const list = $("record-list");
  const monthSelect = $("record-month");
  let view = getRecordView(
    state.records,
    state.recordMonth,
    state.recordVisibleCount,
  );
  if (state.recordMonth !== view.month) {
    state.recordMonth = "";
    state.recordVisibleCount = RECORD_PAGE_SIZE;
    view = getRecordView(state.records, "", RECORD_PAGE_SIZE);
  }
  monthSelect.replaceChildren(new Option("전체 기간", ""));
  for (const month of view.months) {
    const [year, monthNumber] = month.split("-");
    monthSelect.add(new Option(`${year}년 ${Number(monthNumber)}월`, month));
  }
  monthSelect.value = state.recordMonth;
  $("record-visible-count").textContent =
    `${view.total}개 중 ${view.visible.length}개 표시`;
  const more = $("record-more");
  more.hidden = view.remaining === 0;
  more.textContent = `더 보기 (${view.remaining}개 남음)`;
  list.replaceChildren();
  if (!state.records.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "아직 독서 기록이 없어요. 첫 기록을 추가해 보세요.";
    list.append(empty);
    return;
  }
  for (const record of view.visible) {
    const item = document.createElement("article");
    item.className = "record-item";
    const date = document.createElement("span");
    date.className = "record-date";
    date.textContent = readableDate(record.date);
    const body = document.createElement("div");
    body.className = "record-body";
    const value = document.createElement("strong");
    value.textContent = formatMinutes(record.value);
    const memo = document.createElement("small");
    memo.textContent = record.memo || "메모 없음";
    body.append(value, memo);
    const actions = document.createElement("div");
    actions.className = "record-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "수정";
    edit.addEventListener("click", () => editRecord(record));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "삭제";
    remove.addEventListener("click", () => deleteRecord(record));
    actions.append(edit, remove);
    item.append(date, body, actions);
    list.append(item);
  }
}

function resetRecordForm() {
  $("record-form").reset();
  $("record-id").value = "";
  $("record-date").value = localDate();
  $("record-submit").textContent = "기록 추가";
  $("record-cancel").hidden = true;
}

function editRecord(record) {
  $("record-id").value = record.id;
  $("record-date").value = record.date;
  $("record-value").value = record.value;
  $("record-memo").value = record.memo || "";
  $("record-submit").textContent = "수정 저장";
  $("record-cancel").hidden = false;
  $("record-form").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function refreshReading() {
  const [records, summary] = await Promise.all([
    api("/api/data"),
    api("/api/data/summary"),
  ]);
  state.records = records;
  state.summary = summary;
  $("export-records").disabled = false;
  renderRecords();
  renderSummary();
}

async function saveRecord(event) {
  event.preventDefault();
  const id = $("record-id").value;
  const payload = {
    date: $("record-date").value,
    value: Number($("record-value").value),
    memo: $("record-memo").value.trim(),
  };
  if (!payload.date || !Number.isFinite(payload.value) || payload.value <= 0) {
    setFeedback(
      "record-feedback",
      "날짜와 0보다 큰 독서 시간을 입력해 주세요.",
    );
    return;
  }
  const button = $("record-submit");
  button.disabled = true;
  setFeedback("record-feedback", "저장하고 있습니다…");
  try {
    await api(id ? `/api/data/${encodeURIComponent(id)}` : "/api/data", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    resetRecordForm();
    await refreshReading();
    setFeedback(
      "record-feedback",
      id ? "기록을 수정했습니다." : "기록을 추가했습니다.",
    );
  } catch (error) {
    setFeedback("record-feedback", error.message);
  } finally {
    button.disabled = false;
  }
}

async function deleteRecord(record) {
  if (!window.confirm(`${record.date}의 독서 기록을 삭제할까요?`)) return;
  try {
    await api(`/api/data/${encodeURIComponent(record.id)}`, {
      method: "DELETE",
    });
    if ($("record-id").value === record.id) resetRecordForm();
    await refreshReading();
    setFeedback("record-feedback", "기록을 삭제했습니다.");
  } catch (error) {
    setFeedback("record-feedback", error.message);
  }
}

function renderMessages(messages = state.messages) {
  const container = $("chat-messages");
  container.replaceChildren();
  if (!messages.length) {
    const intro = document.createElement("div");
    intro.className = "message assistant";
    const mark = document.createElement("span");
    mark.className = "mini-mark";
    mark.textContent = "P";
    const text = document.createElement("p");
    text.textContent =
      "안녕하세요. “최근 독서 습관이 좋아지고 있어?”처럼 물어보세요.";
    intro.append(mark, text);
    container.append(intro);
  }
  for (const message of messages) {
    const row = document.createElement("div");
    row.className = `message ${message.role}`;
    if (message.role === "assistant") {
      const mark = document.createElement("span");
      mark.className = "mini-mark";
      mark.textContent = "P";
      row.append(mark);
    }
    const text = document.createElement("p");
    text.textContent = message.content;
    row.append(text);
    container.append(row);
  }
  container.scrollTop = container.scrollHeight;
}

function renderConversations() {
  const list = $("conversation-list");
  list.replaceChildren();
  if (!state.conversations.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "아직 저장된 대화가 없습니다.";
    list.append(empty);
    return;
  }
  for (const conversation of state.conversations) {
    const item = document.createElement("div");
    item.className = `conversation-item${state.conversationId === conversation.id ? " active" : ""}`;
    const open = document.createElement("button");
    open.className = "conversation-open";
    open.type = "button";
    const title = document.createElement("strong");
    title.textContent = conversation.title;
    const time = document.createElement("small");
    time.textContent = `${prettyTimestamp(conversation.updated_at)} · ${conversation.message_count}개 메시지`;
    open.append(title, time);
    open.addEventListener("click", () => loadConversation(conversation.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "삭제";
    remove.setAttribute("aria-label", `${conversation.title} 대화 삭제`);
    remove.addEventListener("click", () => deleteConversation(conversation));
    item.append(open, remove);
    list.append(item);
  }
}

async function refreshConversations() {
  state.conversations = await api("/api/conversations");
  renderConversations();
}

function exportRecords() {
  if (!state.user || $("export-records").disabled) return;
  const content = serializeRecords(state.records, new Date().toISOString());
  const url = URL.createObjectURL(new Blob([content], { type: "application/json;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `pageful-reading-records-${localDate()}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  setFeedback("record-feedback", `내 기록 ${state.records.length}건의 JSON 다운로드를 시작했습니다.`);
}

async function loadConversation(id) {
  try {
    const conversation = await api(
      `/api/conversations/${encodeURIComponent(id)}`,
    );
    state.conversationId = id;
    state.messages = conversation.messages || [];
    renderMessages();
    renderConversations();
    setFeedback("chat-feedback", "이전 대화를 불러왔습니다.");
    $("assistant").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setFeedback("chat-feedback", error.message);
  }
}

async function deleteConversation(conversation) {
  if (!window.confirm(`“${conversation.title}” 대화를 삭제할까요?`)) return;
  try {
    await api(`/api/conversations/${encodeURIComponent(conversation.id)}`, {
      method: "DELETE",
    });
    if (state.conversationId === conversation.id) newConversation();
    await refreshConversations();
    setFeedback("chat-feedback", "대화를 삭제했습니다.");
  } catch (error) {
    setFeedback("chat-feedback", error.message);
  }
}

function newConversation() {
  state.conversationId = null;
  state.messages = [];
  renderMessages();
  renderConversations();
  setFeedback("chat-feedback", "새 대화를 시작할 수 있어요.");
  $("chat-input").focus();
}

async function sendChat(event) {
  event.preventDefault();
  const question = $("chat-input").value.trim();
  if (!question) return;
  const button = $("chat-submit");
  button.disabled = true;
  setFeedback(
    "chat-feedback",
    "독서 기록을 살펴보고 있어요. 첫 요청은 서버 준비로 조금 걸릴 수 있습니다.",
  );
  renderMessages([
    ...state.messages,
    { role: "user", content: question },
    { role: "assistant", content: "답변을 작성 중이에요…" },
  ]);
  try {
    const response = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message: question,
        conversation_id: state.conversationId,
      }),
    });
    state.conversationId = response.conversation_id;
    state.messages = response.messages;
    $("chat-input").value = "";
    renderMessages();
    await refreshConversations();
    setFeedback("chat-feedback", "");
  } catch (error) {
    renderMessages();
    setFeedback("chat-feedback", error.message);
  } finally {
    button.disabled = false;
  }
}

async function loadAll() {
  setStatus(
    "독서 기록을 불러오고 있습니다. 첫 요청은 서버 준비로 조금 걸릴 수 있어요.",
  );
  try {
    await Promise.all([refreshReading(), refreshConversations()]);
    setStatus("내 독서 기록과 대화만 표시됩니다.", "success");
  } catch (error) {
    setStatus(`데이터를 불러오지 못했습니다: ${error.message}`, "error");
  }
}

function start() {
  initializeTheme();
  $("theme-toggle").addEventListener("click", toggleTheme);
  $("record-date").value = localDate();
  $("record-form").addEventListener("submit", saveRecord);
  $("export-records").addEventListener("click", exportRecords);
  $("record-cancel").addEventListener("click", resetRecordForm);
  $("record-month").addEventListener("change", (event) => {
    state.recordMonth = event.target.value;
    state.recordVisibleCount = RECORD_PAGE_SIZE;
    renderRecords();
  });
  $("record-more").addEventListener("click", () => {
    state.recordVisibleCount += RECORD_PAGE_SIZE;
    renderRecords();
  });
  $("chat-form").addEventListener("submit", sendChat);
  $("new-chat").addEventListener("click", newConversation);
  $("copy-user-id").addEventListener("click", () => {
    if (!state.user) return;
    const panel = $("user-id-panel");
    panel.hidden = !panel.hidden;
    $("copy-user-id").setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) {
      $("user-id-value").value = state.user.uid;
      $("user-id-value").select();
    }
  });
  $("copy-user-id-value").addEventListener("click", async () => {
    if (!state.user) return;
    try {
      await navigator.clipboard.writeText(state.user.uid);
      $("user-id-feedback").textContent = "ID를 복사했습니다.";
    } catch {
      $("user-id-value").select();
      $("user-id-feedback").textContent =
        "자동 복사가 차단됐습니다. 선택된 ID를 직접 복사해 주세요.";
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".profile-area")) {
      $("user-id-panel").hidden = true;
      $("copy-user-id").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      $("user-id-panel").hidden = true;
      $("copy-user-id").setAttribute("aria-expanded", "false");
    }
  });
  setFormsDisabled(true);
  const required = [
    config.apiBaseUrl,
    config.firebase?.apiKey,
    config.firebase?.authDomain,
    config.firebase?.projectId,
    config.firebase?.appId,
  ];
  if (required.some((value) => !value)) {
    setStatus(
      "Firebase와 API 서버 설정이 필요합니다. README의 환경변수 설정을 확인해 주세요.",
      "error",
    );
    $("record-list").textContent = "설정 후 독서 기록이 표시됩니다.";
    $("conversation-list").textContent = "설정 후 대화 기록이 표시됩니다.";
    return;
  }
  try {
    const auth = getAuth(initializeApp(config.firebase));
    onAuthStateChanged(
      auth,
      async (user) => {
        if (!user) {
          state.user = null;
          state.records = [];
          $("export-records").disabled = true;
          setFormsDisabled(true);
          setStatus("사용자 공간을 준비하고 있습니다.");
          try {
            await signInAnonymously(auth);
          } catch (error) {
            setStatus(`익명 인증에 실패했습니다: ${error.message}`, "error");
          }
          return;
        }
        if (state.user?.uid !== user.uid) {
          state.records = [];
          state.summary = null;
          state.conversations = [];
          state.conversationId = null;
          state.messages = [];
        }
        state.user = user;
        $("export-records").disabled = true;
        setFormsDisabled(false);
        await loadAll();
      },
      (error) =>
        setStatus(`인증 상태를 확인하지 못했습니다: ${error.message}`, "error"),
    );
  } catch (error) {
    setStatus(`Firebase 설정을 확인해 주세요: ${error.message}`, "error");
  }
}

start();
