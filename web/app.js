
const START_DATE_STR = "2026-01-18"; // 18.01.2026
const MONTHS_TOTAL = 4;

const STORAGE_KEY = "sepehr_ba_timeline_v2";
const SETTINGS_KEY = "sepehr_ba_timeline_settings_v1";


const I18N = {
  de: {
    title: "Bachelorarbeit von Sepehr",
    timeLabel: "Zeit seit Start · Restzeit (4 Monate)",
    kwLabel: "Projektwoche (KW) ab 18.01.2026",
    progressLabel: "Fortschritt",
    hint: "Tipp: Aufgaben kannst du pro Woche hinzufügen, Status ändern und löschen – es wird automatisch gespeichert.",
    thWeek: "KW",
    thRange: "Zeitraum",
    thTasks: "Aufgaben",
    thActions: "Aktionen",

    addWeek: "+ Woche hinzufügen",
    addToCurrent: "Aufgabe zur aktuellen Woche",
    export: "Export (JSON)",
    import: "Import (JSON)",
    reset: "Alles zurücksetzen",

    placeholderCurrent: "Neue Aufgabe (für aktuelle Woche) …",
    placeholderInline: "Aufgabe hinzufügen …",
    addInline: "+ Hinzufügen",
    deleteWeek: "Woche löschen",
    deleteTask: "Löschen",

    notStarted: "Nicht angefangen",
    started: "Angefangen",
    done: "Erledigt",

    youAreHere: "Du bist hier",
    noTasks: "Noch keine Aufgaben",

    confirmReset: "Wirklich alles löschen und neu starten?",
    confirmDeleteWeek: "Diese Woche wirklich löschen?",
    importInvalid: "Import-Datei ist ungültig.",
    importOk: "Import erfolgreich!",
    exportNamePrefix: "BA_Timeline_Sepehr",

    daysSince: "seit Start",
    daysLeft: "übrig",
    rangeSep: "→",
    until: "bis",
    projectWeek: "KW",
    of: "von",
    daySingular: "Tag",
    dayPlural: "Tage",

    progressText: (percent, done, total, started) => `${percent}% erledigt · ${done}/${total} erledigt · ${started} angefangen`,

    themeDark: "🌙 Dark",
    themeLight: "☀️ Light",
  },
  en: {
    title: "Bachelor thesis by Sepehr",
    timeLabel: "Time since start · Remaining (4 months)",
    kwLabel: "Project week (WK) from Jan 18, 2026",
    progressLabel: "Progress",
    hint: "Tip: Add tasks per week, change status, and delete everything is saved automatically.",
    thWeek: "WK",
    thRange: "Date range",
    thTasks: "Tasks",
    thActions: "Actions",

    addWeek: "+ Add week",
    addToCurrent: "Add task to current week",
    export: "Export (JSON)",
    import: "Import (JSON)",
    reset: "Reset everything",

    placeholderCurrent: "New task (for current week) …",
    placeholderInline: "Add task …",
    addInline: "+ Add",
    deleteWeek: "Delete week",
    deleteTask: "Delete",

    notStarted: "Not started",
    started: "In progress",
    done: "Done",

    youAreHere: "You are here",
    noTasks: "No tasks yet",

    confirmReset: "Really delete everything and start over?",
    confirmDeleteWeek: "Really delete this week?",
    importInvalid: "Import file is invalid.",
    importOk: "Import successful!",
    exportNamePrefix: "BA_Timeline_Sepehr",

    daysSince: "since start",
    daysLeft: "left",
    rangeSep: "→",
    until: "to",
    projectWeek: "WK",
    of: "of",
    daySingular: "day",
    dayPlural: "days",

    progressText: (percent, done, total, started) => `${percent}% done · ${done}/${total} done · ${started} in progress`,

    themeDark: "🌙 Dark",
    themeLight: "☀️ Light",
  }
};


function toDateAtMidnight(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function addMonths(date, months) {
  const d = new Date(date);
  d.setMonth(d.getMonth() + months);
  return d;
}

function diffDays(a, b) {
  const ms = toDateAtMidnight(b) - toDateAtMidnight(a);
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function uid() {
  return Math.random().toString(16).slice(2) + "-" + Date.now().toString(16);
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmtDate(date, lang) {
  const d = new Date(date);
  const locale = lang === "en" ? "en-GB" : "de-DE";
  return d.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "numeric" });
}

function unitDay(n) {
  return Math.abs(n) === 1 ? t.daySingular : t.dayPlural;
}

// =====================
// Settings (theme/lang)
// =====================
function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { lang: "de", theme: "dark" };
    const s = JSON.parse(raw);
    return {
      lang: (s.lang === "en" ? "en" : "de"),
      theme: (s.theme === "light" ? "light" : "dark"),
    };
  } catch {
    return { lang: "de", theme: "dark" };
  }
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

let settings = loadSettings();
let t = I18N[settings.lang];


document.body.dataset.theme = settings.theme;


function defaultState() {
  const start = toDateAtMidnight(START_DATE_STR);
  const end = addMonths(start, MONTHS_TOTAL);

  const totalDays = diffDays(start, end);
  const totalWeeks = Math.ceil(totalDays / 7);

  const weeks = [];
  for (let i = 0; i < totalWeeks; i++) {
    const ws = addDays(start, i * 7);
    const we = addDays(ws, 6);
    weeks.push({
      id: uid(),
      weekIndex: i + 1,
      startISO: toDateAtMidnight(ws).toISOString(),
      endISO: toDateAtMidnight(we).toISOString(),
      tasks: [] 
    });
  }

  return { weeks };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.weeks)) return defaultState();
    return parsed;
  } catch {
    return defaultState();
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

let state = loadState();

const titleText = document.getElementById("titleText");
const timeLabel = document.getElementById("timeLabel");
const kwLabel = document.getElementById("kwLabel");
const progressLabel = document.getElementById("progressLabel");
const hintText = document.getElementById("hintText");

const thWeek = document.getElementById("thWeek");
const thRange = document.getElementById("thRange");
const thTasks = document.getElementById("thTasks");
const thActions = document.getElementById("thActions");

const daysValueEl = document.getElementById("daysValue");
const rangeValueEl = document.getElementById("rangeValue");
const kwValueEl = document.getElementById("kwValue");
const kwSubEl = document.getElementById("kwSub");

const progressTextEl = document.getElementById("progressText");
const progressFillEl = document.getElementById("progressFill");

const weeksTbody = document.getElementById("weeksTbody");

const addWeekBtn = document.getElementById("addWeekBtn");
const addTaskToCurrentBtn = document.getElementById("addTaskToCurrentBtn");
const globalTaskInput = document.getElementById("globalTaskInput");
const resetBtn = document.getElementById("resetBtn");

const exportBtn = document.getElementById("exportBtn");
const importBtn = document.getElementById("importBtn");
const importFile = document.getElementById("importFile");

const langBtn = document.getElementById("langBtn");
const themeBtn = document.getElementById("themeBtn");


function computeProjectMeta() {
  const start = toDateAtMidnight(START_DATE_STR);
  const end = addMonths(start, MONTHS_TOTAL);
  const today = toDateAtMidnight(new Date());

  const elapsed = diffDays(start, today);
  const total = diffDays(start, end);
  const remaining = total - elapsed;

  const weekNow = Math.floor(elapsed / 7) + 1;
  const totalWeeks = Math.ceil(total / 7);

  const weekClamped = clamp(weekNow, 1, totalWeeks);

  return {
    start, end, today,
    elapsed: Math.max(0, elapsed),
    total: Math.max(0, total),
    remaining: Math.max(0, remaining),
    weekNow: weekClamped,
    totalWeeks
  };
}

function getCurrentWeekId() {
  const meta = computeProjectMeta();
  const w = state.weeks.find(x => x.weekIndex === meta.weekNow);
  return w ? w.id : (state.weeks[0]?.id ?? null);
}


function computeProgress() {
  let total = 0;
  let done = 0;
  let started = 0;

  for (const w of state.weeks) {
    for (const task of (w.tasks || [])) {
      total += 1;
      if (task.status === "done") done += 1;
      else if (task.status === "started") started += 1;
    }
  }

  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  return { total, done, started, percent };
}

function applyTexts() {
  
  titleText.textContent = t.title;
  timeLabel.textContent = t.timeLabel;
  kwLabel.textContent = t.kwLabel;
  progressLabel.textContent = t.progressLabel;
  hintText.textContent = t.hint;

  thWeek.textContent = t.thWeek;
  thRange.textContent = t.thRange;
  thTasks.textContent = t.thTasks;
  thActions.textContent = t.thActions;

  addWeekBtn.textContent = t.addWeek;
  addTaskToCurrentBtn.textContent = t.addToCurrent;
  exportBtn.textContent = t.export;
  importBtn.textContent = t.import;
  resetBtn.textContent = t.reset;

  globalTaskInput.placeholder = t.placeholderCurrent;

  langBtn.textContent = settings.lang.toUpperCase();

  themeBtn.textContent = (settings.theme === "dark") ? t.themeDark : t.themeLight;
}

function renderHeader() {
  const meta = computeProjectMeta();
  const rangeText = `${fmtDate(meta.start, settings.lang)} ${t.rangeSep} ${fmtDate(meta.end, settings.lang)}`;

  daysValueEl.textContent =
  `${meta.elapsed} ${unitDay(meta.elapsed)} ${t.daysSince} · ` +
  `${meta.remaining} ${unitDay(meta.remaining)} ${t.daysLeft}`;

  rangeValueEl.textContent = rangeText;

  kwValueEl.textContent = `${t.projectWeek} ${meta.weekNow} ${t.of} ${meta.totalWeeks}`;
  kwSubEl.textContent = `${fmtDate(meta.start, settings.lang)} ${t.until} ${fmtDate(meta.end, settings.lang)}`;
}

function renderProgress() {
  const p = computeProgress();
  progressTextEl.textContent = t.progressText(p.percent, p.done, p.total, p.started);
  progressFillEl.style.width = `${p.percent}%`;
}

function statusChip(status) {
  if (status === "done") return `<span class="chip ok">${t.done}</span>`;
  if (status === "started") return `<span class="chip warn">${t.started}</span>`;
  return `<span class="chip bad">${t.notStarted}</span>`;
}

function renderWeeks() {
  const meta = computeProjectMeta();
  const currentWeekIndex = meta.weekNow;

  weeksTbody.innerHTML = state.weeks.map(week => {
    const isCurrent = week.weekIndex === currentWeekIndex;

    const tasks = (week.tasks?.length ? week.tasks : []);

    const tasksHtml = tasks.map(task => {
      return `
        <div class="task" data-weekid="${week.id}" data-taskid="${task.id}">
          <div class="text">${escapeHtml(task.text)}</div>
          <div class="meta">
            ${statusChip(task.status)}
            <select class="status" data-action="status">
              <option value="not_started" ${task.status==="not_started"?"selected":""}>${t.notStarted}</option>
              <option value="started" ${task.status==="started"?"selected":""}>${t.started}</option>
              <option value="done" ${task.status==="done"?"selected":""}>${t.done}</option>
            </select>
            <button class="smallBtn danger" data-action="deleteTask">${t.deleteTask}</button>
          </div>
        </div>
      `;
    }).join("");

    return `
      <tr class="${isCurrent ? "highlight" : ""}" data-weekid="${week.id}">
        <td>
          <div class="kw">${t.projectWeek} ${week.weekIndex}</div>
          <div class="range">${isCurrent ? t.youAreHere : ""}</div>
        </td>
        <td>
          <div>${fmtDate(week.startISO, settings.lang)}</div>
          <div class="range">${t.until} ${fmtDate(week.endISO, settings.lang)}</div>
        </td>
        <td>
          <div class="tasks">${tasksHtml || `<span class="range">${t.noTasks}</span>`}</div>

          <div class="addInline">
            <input class="inlineField" placeholder="${t.placeholderInline}" data-action="inlineInput" />
            <button class="smallBtn" data-action="addTask">${t.addInline}</button>
          </div>
        </td>
        <td>
          <button class="smallBtn danger" data-action="deleteWeek">${t.deleteWeek}</button>
        </td>
      </tr>
    `;
  }).join("");
}

function rerender() {
  saveState();
  applyTexts();
  renderHeader();
  renderProgress();
  renderWeeks();
}


addWeekBtn.addEventListener("click", () => {
  const last = state.weeks[state.weeks.length - 1];
  const lastEnd = last ? toDateAtMidnight(last.endISO) : toDateAtMidnight(START_DATE_STR);
  const newStart = addDays(lastEnd, 1);
  const newEnd = addDays(newStart, 6);
  const nextIndex = (last?.weekIndex ?? 0) + 1;

  state.weeks.push({
    id: uid(),
    weekIndex: nextIndex,
    startISO: newStart.toISOString(),
    endISO: newEnd.toISOString(),
    tasks: []
  });

  rerender();
});

addTaskToCurrentBtn.addEventListener("click", () => {
  const text = (globalTaskInput.value || "").trim();
  if (!text) return;

  const weekId = getCurrentWeekId();
  if (!weekId) return;

  const w = state.weeks.find(x => x.id === weekId);
  if (!w) return;

  w.tasks.push({ id: uid(), text, status: "not_started" });
  globalTaskInput.value = "";
  rerender();
});

resetBtn.addEventListener("click", () => {
  if (!confirm(t.confirmReset)) return;
  localStorage.removeItem(STORAGE_KEY);
  state = defaultState();
  rerender();
});


weeksTbody.addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;

  const action = btn.dataset.action;
  const row = e.target.closest("tr[data-weekid]");
  const weekId = row?.dataset.weekid;
  if (!weekId) return;

  if (action === "deleteWeek") {
    if (!confirm(t.confirmDeleteWeek)) return;
    state.weeks = state.weeks.filter(w => w.id !== weekId);
    state.weeks.forEach((w, i) => w.weekIndex = i + 1);
    rerender();
    return;
  }

  if (action === "addTask") {
    const input = row.querySelector('input[data-action="inlineInput"]');
    const text = (input?.value || "").trim();
    if (!text) return;

    const w = state.weeks.find(x => x.id === weekId);
    if (!w) return;

    w.tasks.push({ id: uid(), text, status: "not_started" });
    if (input) input.value = "";
    rerender();
    return;
  }

  if (action === "deleteTask") {
    const taskEl = e.target.closest(".task");
    const taskId = taskEl?.dataset.taskid;
    if (!taskId) return;

    const w = state.weeks.find(x => x.id === weekId);
    if (!w) return;

    w.tasks = w.tasks.filter(x => x.id !== taskId);
    rerender();
  }
});

weeksTbody.addEventListener("change", (e) => {
  const sel = e.target.closest('select[data-action="status"]');
  if (!sel) return;

  const taskEl = e.target.closest(".task");
  const row = e.target.closest("tr[data-weekid]");

  const weekId = row?.dataset.weekid;
  const taskId = taskEl?.dataset.taskid;
  if (!weekId || !taskId) return;

  const w = state.weeks.find(x => x.id === weekId);
  if (!w) return;

  const task = w.tasks.find(x => x.id === taskId);
  if (!task) return;

  task.status = sel.value;
  rerender();
});


exportBtn.addEventListener("click", () => {
  const payload = {
    exportedAt: new Date().toISOString(),
    version: 1,
    startDate: START_DATE_STR,
    monthsTotal: MONTHS_TOTAL,
    settings,
    state
  };

  const json = JSON.stringify(payload, null, 2);
  const blob = new Blob([json], { type: "application/json" });

  const a = document.createElement("a");
  const dateStamp = new Date().toISOString().slice(0,10).replaceAll("-","");
  a.href = URL.createObjectURL(blob);
  a.download = `${t.exportNamePrefix}_${dateStamp}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
});

importBtn.addEventListener("click", () => {
  importFile.value = "";
  importFile.click();
});

importFile.addEventListener("change", async () => {
  const file = importFile.files?.[0];
  if (!file) return;

  try {
    const text = await file.text();
    const data = JSON.parse(text);

    
    if (!data || !data.state || !Array.isArray(data.state.weeks)) {
      alert(t.importInvalid);
      return;
    }

    
    state = data.state;

    
    if (data.settings) {
      settings.lang = (data.settings.lang === "en") ? "en" : "de";
      settings.theme = (data.settings.theme === "light") ? "light" : "dark";
      saveSettings();
      document.body.dataset.theme = settings.theme;
      t = I18N[settings.lang];
    }

    saveState();
    rerender();
    alert(t.importOk);
  } catch {
    alert(t.importInvalid);
  }
});


langBtn.addEventListener("click", () => {
  settings.lang = (settings.lang === "de") ? "en" : "de";
  t = I18N[settings.lang];
  saveSettings();
  rerender();
});

themeBtn.addEventListener("click", () => {
  settings.theme = (settings.theme === "dark") ? "light" : "dark";
  document.body.dataset.theme = settings.theme;
  saveSettings();
  rerender();
});


rerender();
setInterval(() => {
  renderHeader(); 
}, 60 * 1000);
