let statusesConfig = {
  default_status: "applied",
  statuses: [],
  labels: {},
  progression: { pipeline: [], closed: [], aliases: {} },
};
let lastRevision = 0;
let allJobs = [];
let searchQuery = "";
let fitFilter = "";
let jobDatePreset = "7d";
let jobDateFrom = "";
let jobDateTo = "";
let profileData = { sections: [] };
let profileEditors = new Map();
let turndownService = null;
let pageSize = 10;
let currentPage = 1;
const selectedJobIndices = new Set();
const selectedTrashIndices = new Set();
let allTrash = [];
let trashRetentionDays = 30;
let jobsSubView = "jobs";
let confirmResolver = null;
const REVISION_POLL_MS = 3000;
const DASHBOARD_PERIOD_KEY = "tracker.dashboard.period";
const JOB_DATE_FILTER_KEY = "tracker.jobs.dateFilter";
const DASHBOARD_PERIODS = ["week", "month", "quarter", "year", "beginning"];
const JOB_DATE_PRESETS = ["7d", "14d", "28d", "2m", "quarter", "6m", "ytd", "year", "all", "custom"];
const JOB_DATE_PRESET_LABELS = {
  "7d": "last 7 days",
  "14d": "last 14 days",
  "28d": "last 28 days",
  "2m": "last 2 months",
  quarter: "this quarter",
  "6m": "last 6 months",
  ytd: "year to date",
  year: "last 12 months",
  all: "all time",
  custom: "custom range",
};
const STATUS_BAR_COLORS = {
  draft: "#6b7280",
  applied: "#3b82f6",
  phone_screen: "#06b6d4",
  interview: "#a855f7",
  offer: "#22c55e",
  rejected: "#ef4444",
  withdrawn: "#f59e0b",
  no_response: "#94a3b8",
};
let dashboardPeriod = "beginning";
let statusChart = null;
let funnelChart = null;
let dashboardChartTotal = 0;
let latestAnalytics = null;

const $ = (sel) => document.querySelector(sel);
const jobsBody = $("#jobs-body");
const dialog = $("#job-dialog");
const linkDialog = $("#link-dialog");
const profileDialog = $("#profile-dialog");
const linkForm = $("#link-form");
const form = $("#job-form");
const profileForm = $("#profile-form");
const confirmDialog = $("#confirm-dialog");
const confirmForm = $("#confirm-form");
const trashBody = $("#trash-body");
const messageEl = $("#message");
const btnDelete = $("#btn-delete");

function showMessage(text, isError = false) {
  messageEl.textContent = text;
  messageEl.classList.toggle("error", isError);
  messageEl.classList.remove("hidden");
  setTimeout(() => messageEl.classList.add("hidden"), 4000);
}

function confirmAction({ title, message, confirmLabel = "Confirm", danger = false }) {
  return new Promise((resolve) => {
    $("#confirm-title").textContent = title;
    $("#confirm-message").textContent = message;
    const okBtn = $("#btn-confirm-ok");
    okBtn.textContent = confirmLabel;
    okBtn.classList.toggle("danger", danger);
    okBtn.classList.toggle("primary", !danger);
    confirmResolver = resolve;
    confirmDialog.showModal();
  });
}

confirmForm.addEventListener("submit", (e) => {
  e.preventDefault();
  confirmDialog.close();
  if (confirmResolver) confirmResolver(true);
  confirmResolver = null;
});

$("#btn-confirm-cancel").addEventListener("click", () => {
  confirmDialog.close();
  if (confirmResolver) confirmResolver(false);
  confirmResolver = null;
});

confirmDialog.addEventListener("cancel", () => {
  if (confirmResolver) confirmResolver(false);
  confirmResolver = null;
});

function formatJobListPreview(labels) {
  const preview = labels.slice(0, 3).join(", ");
  const suffix = labels.length > 3 ? ` and ${labels.length - 3} more` : "";
  return labels.length ? `\n\n${preview}${suffix}` : "";
}

async function confirmMoveToTrash(labels) {
  const count = labels.length;
  const noun = count === 1 ? "job" : "jobs";
  return confirmAction({
    title: "Move to Recycle Bin?",
    message: `Move ${count} ${noun} to the Recycle Bin? You can restore them within ${trashRetentionDays} days. After that they are permanently deleted.${formatJobListPreview(labels)}`,
    confirmLabel: "Move to Recycle Bin",
    danger: true,
  });
}

async function confirmPermanentDelete(labels) {
  const count = labels.length;
  const noun = count === 1 ? "job" : "jobs";
  return confirmAction({
    title: "Delete permanently?",
    message: `Permanently delete ${count} ${noun}? This action is irreversible and cannot be undone.${formatJobListPreview(labels)}`,
    confirmLabel: "Delete permanently",
    danger: true,
  });
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || res.statusText || "Request failed");
  }
  return data;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function title(job) {
  const c = job.company || "—";
  const r = job.role || "—";
  return `${c} — ${r}`;
}

function statusLabel(code) {
  return statusesConfig.labels?.[code] || code;
}

const FIT_LEVELS = {
  strong: { label: "Strong", storage: "strong fit" },
  moderate: { label: "Moderate", storage: "moderate fit" },
  weak: { label: "Weak", storage: "weak fit" },
  unset: { label: "Unset", storage: "" },
};

function normalizeFitLevel(fitRating) {
  const raw = (fitRating || "").trim().toLowerCase();
  if (!raw) return "unset";
  if (raw.includes("strong") || raw === "high") return "strong";
  if (raw.includes("weak") || raw.includes("poor") || raw === "low") return "weak";
  if (raw.includes("moderate") || raw.includes("good") || raw === "medium") return "moderate";
  return "unset";
}

function fitLabel(level) {
  return FIT_LEVELS[level]?.label || FIT_LEVELS.unset.label;
}

function fitStorageValue(level) {
  return FIT_LEVELS[level]?.storage ?? "";
}

function fitCell(job) {
  const level = normalizeFitLevel(job.fit_rating);
  if (level === "unset") return '<span class="missing">—</span>';
  return `<span class="fit-badge fit-${level}">${escapeHtml(fitLabel(level))}</span>`;
}

function fitSelectValue(fitRating) {
  const level = normalizeFitLevel(fitRating);
  return fitStorageValue(level);
}

function formatDateTime(iso) {
  if (!iso) return "";
  // Date-only legacy values (YYYY-MM-DD) parse reliably as local midnight
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso}T00:00:00` : iso;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function jobCreatedAt(job) {
  return job.created_at || job.date || "";
}

function jobModifiedAt(job) {
  return job.modified_at || jobCreatedAt(job);
}

function parseJobDate(iso) {
  if (!iso) return null;
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso}T00:00:00` : iso;
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}

function startOfLocalDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function endOfLocalDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}

function subtractMonths(date, months) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  copy.setMonth(copy.getMonth() - months);
  return copy;
}

function loadJobDateFilter() {
  try {
    const raw = localStorage.getItem(JOB_DATE_FILTER_KEY);
    if (!raw) return { preset: "7d", from: "", to: "" };
    const data = JSON.parse(raw);
    const preset = JOB_DATE_PRESETS.includes(data.preset) ? data.preset : "7d";
    return {
      preset,
      from: typeof data.from === "string" ? data.from : "",
      to: typeof data.to === "string" ? data.to : "",
    };
  } catch {
    return { preset: "7d", from: "", to: "" };
  }
}

function saveJobDateFilter() {
  try {
    localStorage.setItem(
      JOB_DATE_FILTER_KEY,
      JSON.stringify({ preset: jobDatePreset, from: jobDateFrom, to: jobDateTo })
    );
  } catch {
    /* ignore */
  }
}

function jobDateFilterBounds() {
  const now = new Date();
  const today = startOfLocalDay(now);
  const defaultEnd = endOfLocalDay(now);

  if (jobDatePreset === "all") return null;

  if (jobDatePreset === "custom") {
    const from = jobDateFrom ? parseJobDate(jobDateFrom) : null;
    const to = jobDateTo ? parseJobDate(jobDateTo) : null;
    if (!from && !to) return null;
    return {
      start: from ? startOfLocalDay(from) : null,
      end: to ? endOfLocalDay(to) : defaultEnd,
    };
  }

  let start = today;
  switch (jobDatePreset) {
    case "7d":
      start = new Date(today);
      start.setDate(start.getDate() - 6);
      break;
    case "14d":
      start = new Date(today);
      start.setDate(start.getDate() - 13);
      break;
    case "28d":
      start = new Date(today);
      start.setDate(start.getDate() - 27);
      break;
    case "2m":
      start = subtractMonths(today, 2);
      break;
    case "quarter": {
      const quarterMonth = Math.floor(today.getMonth() / 3) * 3;
      start = new Date(today.getFullYear(), quarterMonth, 1);
      break;
    }
    case "6m":
      start = subtractMonths(today, 6);
      break;
    case "ytd":
      start = new Date(today.getFullYear(), 0, 1);
      break;
    case "year":
      start = subtractMonths(today, 12);
      break;
    default:
      start = new Date(today);
      start.setDate(start.getDate() - 6);
  }
  return { start, end: defaultEnd };
}

function jobInDateRange(job) {
  const bounds = jobDateFilterBounds();
  if (!bounds) return true;
  const created = parseJobDate(jobCreatedAt(job));
  if (!created) return false;
  if (bounds.start && created < bounds.start) return false;
  if (bounds.end && created > bounds.end) return false;
  return true;
}

function jobDateFilterDescription() {
  if (jobDatePreset === "all") return "";
  if (jobDatePreset === "custom") {
    if (jobDateFrom && jobDateTo) return `${jobDateFrom} to ${jobDateTo}`;
    if (jobDateFrom) return `from ${jobDateFrom}`;
    if (jobDateTo) return `until ${jobDateTo}`;
    return "custom range";
  }
  return JOB_DATE_PRESET_LABELS[jobDatePreset] || jobDatePreset;
}

function syncJobDateFilterUi() {
  const presetEl = $("#job-date-preset");
  const fromWrap = $("#job-date-from-wrap");
  const toWrap = $("#job-date-to-wrap");
  const fromEl = $("#job-date-from");
  const toEl = $("#job-date-to");
  if (!presetEl) return;
  presetEl.value = jobDatePreset;
  const custom = jobDatePreset === "custom";
  if (fromWrap) fromWrap.hidden = !custom;
  if (toWrap) toWrap.hidden = !custom;
  if (fromEl) fromEl.value = jobDateFrom;
  if (toEl) toEl.value = jobDateTo;
}

function applyJobDateFilterChange({ preset, from = jobDateFrom, to = jobDateTo } = {}) {
  if (preset && JOB_DATE_PRESETS.includes(preset)) jobDatePreset = preset;
  jobDateFrom = from || "";
  jobDateTo = to || "";
  saveJobDateFilter();
  syncJobDateFilterUi();
  currentPage = 1;
  renderJobs();
}

function periodStartDate(period, now = new Date()) {
  const today = startOfLocalDay(now);
  if (period === "week") {
    const day = today.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    return new Date(today.getFullYear(), today.getMonth(), today.getDate() + mondayOffset);
  }
  if (period === "month") {
    return new Date(today.getFullYear(), today.getMonth(), 1);
  }
  if (period === "quarter") {
    const quarterMonth = Math.floor(today.getMonth() / 3) * 3;
    return new Date(today.getFullYear(), quarterMonth, 1);
  }
  if (period === "year") {
    return new Date(today.getFullYear(), 0, 1);
  }
  return null;
}

function periodLabel(period) {
  const labels = {
    week: "this week",
    month: "this month",
    quarter: "this quarter",
    year: "this year",
    beginning: "from the beginning",
  };
  return labels[period] || period;
}

function loadDashboardPeriod() {
  try {
    const saved = localStorage.getItem(DASHBOARD_PERIOD_KEY);
    if (DASHBOARD_PERIODS.includes(saved)) return saved;
  } catch {
    /* ignore */
  }
  return "beginning";
}

function saveDashboardPeriod(period) {
  try {
    localStorage.setItem(DASHBOARD_PERIOD_KEY, period);
  } catch {
    /* ignore */
  }
}

function jobsInPeriod(period) {
  const start = periodStartDate(period);
  if (!start) return allJobs;
  return allJobs.filter((item) => {
    const created = parseJobDate(jobCreatedAt(item.job));
    if (!created) return false;
    return created >= start;
  });
}

function formatPercent(count, total) {
  if (!total) return "0%";
  const pct = (count / total) * 100;
  if (pct === 0 || pct === 100) return `${pct}%`;
  const rounded = Math.round(pct * 10) / 10;
  return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(1)}%`;
}

function statusBarColor(code, index) {
  if (STATUS_BAR_COLORS[code]) return STATUS_BAR_COLORS[code];
  const fallback = ["#64748b", "#0ea5e9", "#8b5cf6", "#14b8a6", "#eab308", "#f97316"];
  return fallback[index % fallback.length];
}

function syncPeriodButtons() {
  document.querySelectorAll(".period-btn").forEach((btn) => {
    const active = btn.dataset.period === dashboardPeriod;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function statusAliases() {
  return statusesConfig.progression?.aliases || {};
}

function resolveStatusCode(raw) {
  const aliases = statusAliases();
  const status = (raw || "").trim() || statusesConfig.default_status;
  return aliases[status] || status;
}

function selectableStatuses() {
  const aliases = statusAliases();
  return (statusesConfig.statuses || []).filter((code) => !(code in aliases));
}

function formatAnalyticsPercent(value) {
  const n = Number(value) || 0;
  if (n === 0 || n === 100) return `${n}%`;
  return Number.isInteger(n) ? `${n}%` : `${n.toFixed(1)}%`;
}

function buildLocalAnalytics(period = dashboardPeriod) {
  const aliases = statusAliases();
  const pipeline = statusesConfig.progression?.pipeline || [];
  const closed = statusesConfig.progression?.closed || [];
  const filtered = jobsInPeriod(period).map((item) => item.job);
  const total = filtered.length;
  const countsMap = new Map((statusesConfig.statuses || []).map((code) => [code, 0]));
  const resolved = [];
  for (const job of filtered) {
    const status = resolveStatusCode(job.status);
    resolved.push(status);
    countsMap.set(status, (countsMap.get(status) || 0) + 1);
  }
  const counts = (statusesConfig.statuses || []).map((code) => {
    const count = countsMap.get(code) || 0;
    return {
      status: code,
      label: statusLabel(code),
      count,
      percent: total ? Math.round((count / total) * 1000) / 10 : 0,
    };
  });

  const ranks = Object.fromEntries(pipeline.map((code, idx) => [code, idx]));
  const reached = pipeline.map(() => 0);
  const current = pipeline.map(() => 0);
  let active = 0;
  let success = 0;
  let closedCount = 0;
  const successStatus = pipeline[pipeline.length - 1] || "";
  const activeSet = new Set(pipeline.slice(0, -1));

  for (const status of resolved) {
    if (closed.includes(status)) {
      closedCount += 1;
      if (pipeline.length) reached[0] += 1;
      continue;
    }
    if (status === successStatus) success += 1;
    else if (activeSet.has(status) || status in ranks) active += 1;
    const rank = ranks[status];
    if (rank === undefined) continue;
    current[rank] += 1;
    for (let i = 0; i <= rank; i += 1) reached[i] += 1;
  }

  const stages = pipeline.map((code, idx) => {
    let conversion = null;
    if (idx > 0) {
      conversion = reached[idx - 1] ? Math.round((reached[idx] / reached[idx - 1]) * 1000) / 10 : 0;
    }
    return {
      status: code,
      label: statusLabel(code),
      current: current[idx],
      reached: reached[idx],
      reached_percent: total ? Math.round((reached[idx] / total) * 1000) / 10 : 0,
      conversion_from_previous: conversion,
    };
  });

  const decided = success + closedCount;
  return {
    period,
    total,
    counts,
    progression: {
      pipeline,
      closed,
      stages,
      active,
      success,
      closed_count: closedCount,
      offer_rate: total ? Math.round((success / total) * 1000) / 10 : 0,
      close_rate: total ? Math.round((closedCount / total) * 1000) / 10 : 0,
      success_among_decided: decided ? Math.round((success / decided) * 1000) / 10 : 0,
    },
  };
}

function destroyStatusChart() {
  if (statusChart) {
    statusChart.destroy();
    statusChart = null;
  }
}

function destroyFunnelChart() {
  if (funnelChart) {
    funnelChart.destroy();
    funnelChart = null;
  }
}

function ensureStatusChart(labels, data, colors) {
  const canvas = $("#status-chart");
  if (!canvas || typeof Chart === "undefined") return;

  if (statusChart) {
    statusChart.data.labels = labels;
    statusChart.data.datasets[0].data = data;
    statusChart.data.datasets[0].backgroundColor = colors;
    statusChart.update();
    return;
  }

  statusChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: "#1a2332",
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: "58%",
      animation: { animateRotate: true, duration: 450 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f1419",
          titleColor: "#e7ecf3",
          bodyColor: "#e7ecf3",
          borderColor: "#2d3a4d",
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label(ctx) {
              const count = Number(ctx.raw) || 0;
              const total = dashboardChartTotal || 0;
              return ` ${ctx.label}: ${count} (${formatPercent(count, total)})`;
            },
          },
        },
      },
    },
  });
}

function ensureFunnelChart(stages) {
  const canvas = $("#funnel-chart");
  if (!canvas || typeof Chart === "undefined") return;
  const labels = stages.map((s) => s.label);
  const data = stages.map((s) => s.reached);
  const colors = stages.map((s, index) => statusBarColor(s.status, index));

  if (funnelChart) {
    funnelChart.data.labels = labels;
    funnelChart.data.datasets[0].data = data;
    funnelChart.data.datasets[0].backgroundColor = colors;
    funnelChart.update();
    return;
  }

  funnelChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Reached stage",
          data,
          backgroundColor: colors,
          borderRadius: 6,
          maxBarThickness: 42,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 450 },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { color: "#8b9cb3", precision: 0 },
          grid: { color: "rgba(45, 58, 77, 0.65)" },
        },
        y: {
          ticks: { color: "#e7ecf3" },
          grid: { display: false },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f1419",
          titleColor: "#e7ecf3",
          bodyColor: "#e7ecf3",
          borderColor: "#2d3a4d",
          borderWidth: 1,
          callbacks: {
            label(ctx) {
              const stage = stages[ctx.dataIndex];
              if (!stage) return ` ${ctx.raw}`;
              const parts = [` reached ${stage.reached} (${formatAnalyticsPercent(stage.reached_percent)})`];
              if (stage.conversion_from_previous != null) {
                parts.push(`conv. ${formatAnalyticsPercent(stage.conversion_from_previous)}`);
              }
              return parts.join(" ·");
            },
          },
        },
      },
    },
  });
}

function renderAnalytics(data) {
  latestAnalytics = data;
  const summaryEl = $("#dashboard-summary");
  const listEl = $("#status-breakdown");
  const chartWrap = $("#chart-wrap");
  const chartEmpty = $("#chart-empty");
  const canvas = $("#status-chart");
  const progSummary = $("#progression-summary");
  const stagesEl = $("#progression-stages");
  if (!summaryEl || !listEl) return;

  syncPeriodButtons();

  const total = data.total || 0;
  dashboardChartTotal = total;
  const noun = total === 1 ? "application" : "applications";
  summaryEl.textContent = `${total} ${noun} ${periodLabel(data.period || dashboardPeriod)}`;

  const progression = data.progression || {};
  if (progSummary) {
    progSummary.hidden = total === 0;
    $("#prog-active").textContent = String(progression.active || 0);
    $("#prog-success").textContent = String(progression.success || 0);
    $("#prog-closed").textContent = String(progression.closed_count || 0);
    $("#prog-offer-rate").textContent = formatAnalyticsPercent(progression.offer_rate);
  }

  const counts = data.counts || [];
  const withCount = counts.filter((row) => row.count > 0);

  if (!total) {
    destroyStatusChart();
    destroyFunnelChart();
    if (canvas) canvas.classList.add("hidden");
    if (chartEmpty) chartEmpty.classList.remove("hidden");
    if (chartWrap) chartWrap.classList.add("is-empty");
    listEl.innerHTML = '<li class="status-breakdown-empty">No applications in this time range.</li>';
    if (stagesEl) stagesEl.innerHTML = "";
    return;
  }

  if (canvas) canvas.classList.remove("hidden");
  if (chartEmpty) chartEmpty.classList.add("hidden");
  if (chartWrap) chartWrap.classList.remove("is-empty");

  ensureStatusChart(
    withCount.map((row) => row.label || statusLabel(row.status)),
    withCount.map((row) => row.count),
    withCount.map((row, index) => statusBarColor(row.status, index))
  );

  listEl.innerHTML = counts
    .map((row, index) => {
      const pct = formatAnalyticsPercent(row.percent);
      const color = statusBarColor(row.status, index);
      const zeroClass = row.count === 0 ? " is-zero" : "";
      return `<li class="status-breakdown-row${zeroClass}">
        <span class="status-swatch" style="background:${color}" aria-hidden="true"></span>
        <span class="status-breakdown-label">${escapeHtml(row.label || statusLabel(row.status))}</span>
        <span class="status-breakdown-count">${row.count}</span>
        <span class="status-breakdown-pct">${escapeHtml(pct)}</span>
        <div class="status-breakdown-track" aria-hidden="true">
          <div class="status-breakdown-fill" style="width:${row.percent || 0}%;background:${color}"></div>
        </div>
      </li>`;
    })
    .join("");

  const stages = progression.stages || [];
  ensureFunnelChart(stages);
  if (stagesEl) {
    stagesEl.innerHTML = stages
      .map((stage, index) => {
        const color = statusBarColor(stage.status, index);
        const conv =
          stage.conversion_from_previous == null
            ? "—"
            : formatAnalyticsPercent(stage.conversion_from_previous);
        return `<li class="progression-stage-row">
          <span class="status-swatch" style="background:${color}" aria-hidden="true"></span>
          <span class="progression-stage-label">${escapeHtml(stage.label)}</span>
          <span class="progression-stage-meta">now ${stage.current}</span>
          <span class="progression-stage-meta">reached ${stage.reached}</span>
          <span class="progression-stage-conv">${escapeHtml(conv)}</span>
        </li>`;
      })
      .join("");
  }
}

function renderDashboardFromLocal() {
  renderAnalytics(buildLocalAnalytics(dashboardPeriod));
}

async function fetchAndRenderAnalytics() {
  try {
    const data = await api(`/api/analytics?period=${encodeURIComponent(dashboardPeriod)}`);
    renderAnalytics(data);
  } catch (err) {
    renderDashboardFromLocal();
    const summaryEl = $("#dashboard-summary");
    if (summaryEl && !allJobs.length) {
      summaryEl.textContent = `Analytics unavailable: ${err.message}`;
    }
  }
}

function renderDashboard() {
  renderDashboardFromLocal();
}

function applyLocalJobStatus(index, status) {
  const item = allJobs.find((i) => i.index === index);
  if (!item) return false;
  item.job.status = resolveStatusCode(status);
  if (item.job.modified_at !== undefined) {
    item.job.modified_at = new Date().toISOString().slice(0, 19);
  }
  return true;
}

function applyLocalJobStatuses(indices, status) {
  let updated = 0;
  for (const index of indices) {
    if (applyLocalJobStatus(index, status)) updated += 1;
  }
  return updated;
}

function setDashboardPeriod(period) {
  if (!DASHBOARD_PERIODS.includes(period)) return;
  dashboardPeriod = period;
  saveDashboardPeriod(period);
  renderDashboardFromLocal();
  fetchAndRenderAnalytics();
}

function fileLink(path, label) {
  if (!path) return `<span class="missing">${label}: —</span>`;
  const url = `/api/files?path=${encodeURIComponent(path)}`;
  return `<a href="${url}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
}

function attachmentCell(job) {
  const parts = [];
  if (job.cv_file) {
    const pdf = job.cv_file.replace(/\.tex$/i, ".pdf");
    parts.push(fileLink(pdf, "CV PDF"));
  } else {
    parts.push('<span class="missing">CV PDF: —</span>');
  }
  if (job.cover_letter_file) {
    const pdf = job.cover_letter_file.replace(/\.tex$/i, ".pdf");
    parts.push(fileLink(pdf, "Cover Letter PDF"));
  }
  if (!parts.length) return '<span class="missing">—</span>';
  return `<div class="attachments">${parts.join("")}</div>`;
}

function statusSelect(index, current) {
  const resolved = resolveStatusCode(current);
  const opts = selectableStatuses()
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === resolved ? "selected" : ""}>${escapeHtml(statusLabel(s))}</option>`
    )
    .join("");
  return `<select class="status-select" data-index="${index}" aria-label="Status">${opts}</select>`;
}

function titleCell(job, index) {
  const text = title(job);
  let titleHtml;
  if (job.source) {
    titleHtml = `<a href="${escapeHtml(job.source)}" target="_blank" rel="noopener" class="job-title-link"><strong>${escapeHtml(text)}</strong></a>`;
  } else {
    titleHtml = `<strong>${escapeHtml(text)}</strong> <button type="button" class="small btn-add-link" data-index="${index}">Add link</button>`;
  }
  const createdRaw = jobCreatedAt(job);
  const modifiedRaw = jobModifiedAt(job);
  const created = formatDateTime(createdRaw);
  const parts = [];
  if (created) {
    parts.push(`<small class="timestamp">Created ${escapeHtml(created)}</small>`);
  }
  if (modifiedRaw && modifiedRaw !== createdRaw) {
    parts.push(
      `<small class="timestamp-updated">Updated ${escapeHtml(formatDateTime(modifiedRaw))}</small>`
    );
  }
  const timestamps = parts.length ? `<div class="timestamps">${parts.join("")}</div>` : "";
  return `${titleHtml}${timestamps}`;
}

function jobSearchText(job) {
  const fields = [
    job.company,
    job.role,
    job.status,
    statusLabel(job.status || statusesConfig.default_status),
    job.notes,
    job.source,
    job.cv_file,
    job.cover_letter_file,
    job.sector,
    job.role_type,
    job.channel,
    job.contact_person,
    job.fit_rating,
    jobCreatedAt(job),
    jobModifiedAt(job),
  ];
  return fields.filter(Boolean).join(" ").toLowerCase();
}

function filterJobs(jobs) {
  const q = searchQuery.trim().toLowerCase();
  return jobs.filter(({ job }) => {
    if (!jobInDateRange(job)) return false;
    if (fitFilter && normalizeFitLevel(job.fit_rating) !== fitFilter) return false;
    if (q && !jobSearchText(job).includes(q)) return false;
    return true;
  });
}

function activeFilterDescription() {
  const parts = [];
  const q = searchQuery.trim();
  if (q) parts.push(`“${q}”`);
  if (fitFilter) parts.push(`fit: ${fitLabel(fitFilter)}`);
  const dateDesc = jobDateFilterDescription();
  if (dateDesc) parts.push(`date: ${dateDesc}`);
  return parts.join(", ");
}

function getFilteredJobs() {
  return filterJobs(allJobs);
}

function updateBulkBar() {
  const count = selectedJobIndices.size;
  $("#bulk-bar").classList.toggle("hidden", count === 0);
  $("#bulk-count").textContent = `${count} selected`;
}

function updateSelectAllButton() {
  const btn = $("#btn-select-all-filtered");
  if (!btn) return;
  const filtered = getFilteredJobs();
  if (!filtered.length) {
    btn.disabled = true;
    btn.textContent = "Select all";
    return;
  }
  btn.disabled = false;
  const allSelected = filtered.every(({ index }) => selectedJobIndices.has(index));
  btn.textContent = allSelected ? "Deselect all" : "Select all";
}

function syncRowSelectionStyles() {
  jobsBody.querySelectorAll("tr.job-row").forEach((row) => {
    const index = parseInt(row.dataset.index, 10);
    const selected = selectedJobIndices.has(index);
    row.classList.toggle("selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
  });
}

function toggleJobSelection(index) {
  if (selectedJobIndices.has(index)) selectedJobIndices.delete(index);
  else selectedJobIndices.add(index);
  updateBulkBar();
  updateSelectAllButton();
  syncRowSelectionStyles();
}

function clearSelection() {
  selectedJobIndices.clear();
  updateBulkBar();
  updateSelectAllButton();
  syncRowSelectionStyles();
}

function toggleSelectAllFiltered() {
  const filtered = getFilteredJobs();
  const allSelected = filtered.length > 0 && filtered.every(({ index }) => selectedJobIndices.has(index));
  if (allSelected) {
    filtered.forEach(({ index }) => selectedJobIndices.delete(index));
  } else {
    filtered.forEach(({ index }) => selectedJobIndices.add(index));
  }
  updateBulkBar();
  updateSelectAllButton();
  syncRowSelectionStyles();
}

function pruneSelection() {
  const valid = new Set(allJobs.map(({ index }) => index));
  for (const index of selectedJobIndices) {
    if (!valid.has(index)) selectedJobIndices.delete(index);
  }
  updateBulkBar();
  updateSelectAllButton();
}
function updatePaginationControls(totalPages, total, filteredTotal) {
  const suffix =
    filteredTotal !== total ? ` (${filteredTotal} of ${total} shown)` : ` (${total} total)`;
  $("#page-info").textContent = `Page ${currentPage} of ${totalPages}${suffix}`;
  $("#btn-prev").disabled = currentPage <= 1;
  $("#btn-next").disabled = currentPage >= totalPages;
}

function renderJobs() {
  const filtered = filterJobs(allJobs);
  const items = filtered;
  if (!allJobs.length) {
    jobsBody.innerHTML = '<tr><td colspan="6" class="empty">No applications yet. Add one above.</td></tr>';
    updatePaginationControls(1, 0, 0);
    updateSelectAllButton();
    return;
  }
  if (!items.length) {
    const desc = activeFilterDescription() || "your filters";
    jobsBody.innerHTML = `<tr><td colspan="6" class="empty">No jobs match ${escapeHtml(desc)}.</td></tr>`;
    updatePaginationControls(1, allJobs.length, 0);
    updateSelectAllButton();
    return;
  }

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * pageSize;
  const pageItems = items.slice(start, start + pageSize);
  updatePaginationControls(totalPages, allJobs.length, items.length);

  jobsBody.innerHTML = pageItems
    .map(({ index, job }) => {
      const notes = job.notes
        ? `<span class="notes-preview">${escapeHtml(job.notes)}</span>`
        : '<span class="missing">—</span>';
      const selectedClass = selectedJobIndices.has(index) ? "selected" : "";
      const ariaSelected = selectedJobIndices.has(index) ? "true" : "false";
      return `<tr class="job-row ${selectedClass}" data-index="${index}" aria-selected="${ariaSelected}" tabindex="0">
        <td>${titleCell(job, index)}</td>
        <td>${statusSelect(index, job.status || statusesConfig.default_status)}</td>
        <td>${fitCell(job)}</td>
        <td>${attachmentCell(job)}</td>
        <td>${notes}</td>
        <td class="actions">
          <div class="actions-inner">
            <button type="button" class="small btn-edit" data-index="${index}">Edit</button>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  jobsBody.querySelectorAll("tr.job-row").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest("a, button, select, input, textarea, label")) return;
      toggleJobSelection(parseInt(row.dataset.index, 10));
    });
    row.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      if (e.target.closest("a, button, select, input, textarea, label")) return;
      e.preventDefault();
      toggleJobSelection(parseInt(row.dataset.index, 10));
    });
  });

  jobsBody.querySelectorAll(".status-select").forEach((sel) => {
    sel.addEventListener("change", async (e) => {
      const idx = parseInt(e.target.dataset.index, 10);
      const nextStatus = e.target.value;
      const item = allJobs.find((i) => i.index === idx);
      const previousStatus = item?.job?.status || statusesConfig.default_status;
      applyLocalJobStatus(idx, nextStatus);
      renderDashboard();
      try {
        await api(`/api/jobs/${idx}`, {
          method: "PUT",
          body: JSON.stringify({ status: nextStatus }),
        });
        showMessage("Status updated");
        await loadJobs(false);
      } catch (err) {
        applyLocalJobStatus(idx, previousStatus);
        renderDashboard();
        showMessage(err.message, true);
        await loadJobs(false);
      }
    });
  });

  jobsBody.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", () => openEdit(parseInt(btn.dataset.index, 10)));
  });

  jobsBody.querySelectorAll(".btn-add-link").forEach((btn) => {
    btn.addEventListener("click", () => openLinkDialog(parseInt(btn.dataset.index, 10)));
  });

  updateSelectAllButton();
}

function openLinkDialog(index) {
  const item = allJobs.find((i) => i.index === index);
  if (!item) {
    showMessage("Job not found", true);
    return;
  }
  $("#link-job-index").value = String(index);
  $("#link-job-label").textContent = title(item.job);
  $("#field-link-url").value = item.job.source || "";
  linkDialog.showModal();
  $("#field-link-url").focus();
}

linkForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const indexStr = $("#link-job-index").value;
  const url = $("#field-link-url").value.trim();
  if (!url) return;
  try {
    await api(`/api/jobs/${indexStr}`, {
      method: "PUT",
      body: JSON.stringify({ source: url }),
    });
    linkDialog.close();
    showMessage("Link added");
    await loadJobs(false);
  } catch (err) {
    showMessage(err.message, true);
  }
});

$("#btn-link-cancel").addEventListener("click", () => linkDialog.close());

function ensureMarkdownTools() {
  if (!turndownService && typeof TurndownService !== "undefined") {
    turndownService = new TurndownService({
      headingStyle: "atx",
      bulletListMarker: "-",
      emDelimiter: "*",
      strongDelimiter: "**",
    });
  }
}

function sectionMarkdown(section) {
  if (section.raw) return section.raw;
  if (section.items?.length) return section.items.map((item) => `- ${item}`).join("\n");
  return "";
}

function markdownToHtml(markdown) {
  if (typeof marked === "undefined") return escapeHtml(markdown).replace(/\n/g, "<br>");
  return marked.parse(markdown, { breaks: true, gfm: true });
}

function htmlToMarkdown(html) {
  ensureMarkdownTools();
  if (!turndownService) {
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    return tmp.textContent || "";
  }
  return turndownService.turndown(html).trim();
}

function destroyProfileEditors() {
  profileEditors.clear();
}

function renderProfile(data) {
  profileData = data;
  const el = $("#profile-content");
  if (!data.sections?.length) {
    el.innerHTML = '<p class="empty">No profile found in AGENTS.md.</p>';
    return;
  }
  el.innerHTML = data.sections
    .map(
      (section) => `
      <div class="profile-block">
        <h3>${escapeHtml(section.title)}</h3>
        <div class="profile-markdown">${markdownToHtml(sectionMarkdown(section))}</div>
      </div>`
    )
    .join("");
}

function createWysiwygEditor(section, index) {
  const wrap = document.createElement("div");
  wrap.className = "profile-section-field";

  const title = document.createElement("span");
  title.className = "profile-section-title";
  title.textContent = section.title;

  const editorWrap = document.createElement("div");
  editorWrap.className = "profile-wysiwyg-wrap";

  const toolbar = document.createElement("div");
  toolbar.className = "wysiwyg-toolbar";
  toolbar.innerHTML = `
    <button type="button" class="wysiwyg-btn" data-cmd="bold" title="Bold"><strong>B</strong></button>
    <button type="button" class="wysiwyg-btn" data-cmd="italic" title="Italic"><em>I</em></button>
    <button type="button" class="wysiwyg-btn" data-cmd="insertUnorderedList" title="Bullet list">•</button>
    <button type="button" class="wysiwyg-btn" data-cmd="link" title="Insert link">Link</button>
  `;

  const editable = document.createElement("div");
  editable.className = "profile-wysiwyg";
  editable.contentEditable = "true";
  editable.spellcheck = true;
  editable.dataset.sectionIndex = String(index);
  editable.innerHTML = markdownToHtml(sectionMarkdown(section));

  toolbar.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-cmd]");
    if (!btn) return;
    e.preventDefault();
    editable.focus();
    const cmd = btn.dataset.cmd;
    if (cmd === "link") {
      const url = prompt("Link URL:");
      if (url) document.execCommand("createLink", false, url.trim());
      return;
    }
    document.execCommand(cmd, false, null);
  });

  editorWrap.append(toolbar, editable);
  wrap.append(title, editorWrap);
  profileEditors.set(index, editable);
  return wrap;
}

function renderProfileEditor() {
  destroyProfileEditors();
  const container = $("#profile-sections");
  container.innerHTML = "";
  if (!profileData.sections?.length) {
    container.innerHTML = '<p class="empty">No profile sections to edit.</p>';
    return;
  }
  profileData.sections.forEach((section, index) => {
    container.appendChild(createWysiwygEditor(section, index));
  });
}

function openProfileEditor() {
  ensureMarkdownTools();
  renderProfileEditor();
  profileDialog.showModal();
  const firstField = $("#profile-sections .profile-wysiwyg");
  if (firstField) firstField.focus();
}

async function saveProfile(e) {
  e.preventDefault();
  const sections = profileData.sections.map((section, index) => {
    const editable = profileEditors.get(index);
    return {
      title: section.title,
      raw: editable ? htmlToMarkdown(editable.innerHTML) : section.raw || "",
    };
  });
  try {
    const updated = await api("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ sections }),
    });
    destroyProfileEditors();
    renderProfile(updated);
    profileDialog.close();
    showMessage("Profile saved to AGENTS.md");
  } catch (err) {
    showMessage(err.message, true);
  }
}

function fillStatusSelect(selectEl, selected) {
  const resolved = resolveStatusCode(selected);
  selectEl.innerHTML = selectableStatuses()
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === resolved ? "selected" : ""}>${escapeHtml(statusLabel(s))}</option>`
    )
    .join("");
}

async function loadStatuses() {
  statusesConfig = await api("/api/statuses");
  if (!statusesConfig.progression) {
    statusesConfig.progression = { pipeline: [], closed: [], aliases: {} };
  }
  fillStatusSelect($("#bulk-status"), statusesConfig.default_status);
}

async function loadProfile() {
  try {
    const data = await api("/api/profile");
    renderProfile(data);
  } catch {
    $("#profile-content").innerHTML = '<p class="empty">Failed to load profile.</p>';
  }
}

async function loadJobs(resetPage = true) {
  allJobs = await api("/api/jobs");
  if (resetPage) currentPage = 1;
  pruneSelection();
  renderJobs();
  renderDashboardFromLocal();
  await fetchAndRenderAnalytics();
}

async function bulkChangeStatus() {
  const indices = [...selectedJobIndices];
  if (!indices.length) return;
  const status = $("#bulk-status").value;
  const previous = new Map(
    indices.map((idx) => {
      const item = allJobs.find((i) => i.index === idx);
      return [idx, item?.job?.status || statusesConfig.default_status];
    })
  );
  applyLocalJobStatuses(indices, status);
  renderDashboard();
  try {
    const result = await api("/api/jobs/bulk", {
      method: "POST",
      body: JSON.stringify({ indices, action: "update_status", status }),
    });
    clearSelection();
    await loadJobs(false);
    showMessage(`Updated status for ${result.updated} job${result.updated === 1 ? "" : "s"}`);
  } catch (err) {
    for (const [idx, prev] of previous) {
      applyLocalJobStatus(idx, prev);
    }
    renderDashboard();
    showMessage(err.message, true);
  }
}

async function bulkDelete() {
  const indices = [...selectedJobIndices];
  if (!indices.length) return;
  const labels = indices
    .map((idx) => allJobs.find((item) => item.index === idx))
    .filter(Boolean)
    .map((item) => title(item.job));
  if (!(await confirmMoveToTrash(labels))) return;
  try {
    const result = await api("/api/jobs/bulk", {
      method: "POST",
      body: JSON.stringify({ indices, action: "delete" }),
    });
    clearSelection();
    await loadJobs(true);
    await loadTrash(false);
    showTrashView();
    showMessage(`Moved ${result.updated} job${result.updated === 1 ? "" : "s"} to Recycle Bin`);
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function pollRevision() {
  if (dialog.open || linkDialog.open || profileDialog.open || confirmDialog.open) return;
  try {
    const { revision } = await api("/api/revision");
    if (revision === lastRevision) return;
    const hadPrior = lastRevision !== 0;
    lastRevision = revision;
    if (hadPrior) {
      await loadJobs(false);
      await loadTrash(false);
      showMessage("Applications updated");
    }
  } catch {
    /* tracker server not running */
  }
}

function startRevisionPolling() {
  setInterval(pollRevision, REVISION_POLL_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") pollRevision();
  });
}

function openAdd() {
  $("#dialog-title").textContent = "Add job";
  $("#job-index").value = "";
  form.reset();
  fillStatusSelect($("#field-status"), statusesConfig.default_status);
  $("#field-fit").value = "";
  btnDelete.classList.add("hidden");
  dialog.showModal();
}

async function openEdit(index) {
  const item = allJobs.find((i) => i.index === index);
  if (!item) {
    showMessage("Job not found", true);
    return;
  }
  const job = item.job;
  $("#dialog-title").textContent = "Edit job";
  $("#job-index").value = String(index);
  $("#field-company").value = job.company || "";
  $("#field-role").value = job.role || "";
  $("#field-source").value = job.source || "";
  $("#field-notes").value = job.notes || "";
  $("#field-cv").value = job.cv_file || "";
  $("#field-cover").value = job.cover_letter_file || "";
  fillStatusSelect($("#field-status"), job.status || statusesConfig.default_status);
  $("#field-fit").value = fitSelectValue(job.fit_rating);
  btnDelete.classList.remove("hidden");
  dialog.showModal();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    company: $("#field-company").value.trim(),
    role: $("#field-role").value.trim(),
    source: $("#field-source").value.trim(),
    status: $("#field-status").value,
    fit_rating: $("#field-fit").value,
    notes: $("#field-notes").value.trim(),
    cv_file: $("#field-cv").value.trim(),
    cover_letter_file: $("#field-cover").value.trim(),
  };
  const indexStr = $("#job-index").value;
  try {
    if (indexStr === "") {
      await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
      showMessage("Job added");
    } else {
      const idx = parseInt(indexStr, 10);
      applyLocalJobStatus(idx, payload.status);
      renderDashboard();
      await api(`/api/jobs/${indexStr}`, { method: "PUT", body: JSON.stringify(payload) });
      showMessage("Job updated");
    }
    dialog.close();
    await loadJobs(indexStr === "");
  } catch (err) {
    showMessage(err.message, true);
  }
});

btnDelete.addEventListener("click", async () => {
  const indexStr = $("#job-index").value;
  if (!indexStr) return;
  const job = allJobs.find((i) => i.index === parseInt(indexStr, 10))?.job;
  const label = job ? title(job) : "this application";
  if (!(await confirmMoveToTrash([label]))) return;
  try {
    await api(`/api/jobs/${indexStr}`, { method: "DELETE" });
    dialog.close();
    await loadJobs(true);
    await loadTrash(false);
    showTrashView();
    showMessage("Moved to Recycle Bin");
  } catch (err) {
    showMessage(err.message, true);
  }
});

$("#btn-add").addEventListener("click", openAdd);
$("#btn-cancel").addEventListener("click", () => dialog.close());

$("#page-size").addEventListener("change", (e) => {
  pageSize = parseInt(e.target.value, 10);
  currentPage = 1;
  renderJobs();
});

$("#btn-prev").addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage -= 1;
    renderJobs();
  }
});

$("#btn-next").addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(filterJobs(allJobs).length / pageSize));
  if (currentPage < totalPages) {
    currentPage += 1;
    renderJobs();
  }
});

$("#job-search").addEventListener("input", (e) => {
  searchQuery = e.target.value;
  currentPage = 1;
  renderJobs();
});

$("#fit-filter").addEventListener("change", (e) => {
  fitFilter = e.target.value;
  currentPage = 1;
  renderJobs();
});

$("#job-date-preset").addEventListener("change", (e) => {
  applyJobDateFilterChange({ preset: e.target.value });
});

$("#job-date-from").addEventListener("change", (e) => {
  applyJobDateFilterChange({ preset: "custom", from: e.target.value, to: jobDateTo });
});

$("#job-date-to").addEventListener("change", (e) => {
  applyJobDateFilterChange({ preset: "custom", from: jobDateFrom, to: e.target.value });
});

$("#btn-select-all-filtered").addEventListener("click", () => toggleSelectAllFiltered());
$("#btn-bulk-status").addEventListener("click", () => bulkChangeStatus());
$("#btn-bulk-delete").addEventListener("click", () => bulkDelete());
$("#btn-bulk-clear").addEventListener("click", () => clearSelection());

function updateTrashBulkBar() {
  const count = selectedTrashIndices.size;
  $("#trash-bulk-bar").classList.toggle("hidden", count === 0);
  $("#trash-bulk-count").textContent = `${count} selected`;
}

function clearTrashSelection() {
  selectedTrashIndices.clear();
  updateTrashBulkBar();
  trashBody.querySelectorAll("tr.trash-row").forEach((row) => {
    row.classList.remove("selected");
    row.setAttribute("aria-selected", "false");
  });
}

function toggleTrashSelection(index) {
  if (selectedTrashIndices.has(index)) selectedTrashIndices.delete(index);
  else selectedTrashIndices.add(index);
  updateTrashBulkBar();
  const row = trashBody.querySelector(`tr.trash-row[data-index="${index}"]`);
  if (row) {
    const selected = selectedTrashIndices.has(index);
    row.classList.toggle("selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
  }
}

function pruneTrashSelection() {
  const valid = new Set(allTrash.map(({ index }) => index));
  for (const index of selectedTrashIndices) {
    if (!valid.has(index)) selectedTrashIndices.delete(index);
  }
  updateTrashBulkBar();
}

function showJobsView() {
  jobsSubView = "jobs";
  $("#jobs-section-intro").hidden = false;
  $("#jobs-view").hidden = false;
  $("#trash-view").hidden = true;
}

function showTrashView() {
  jobsSubView = "trash";
  $("#jobs-section-intro").hidden = true;
  $("#jobs-view").hidden = true;
  $("#trash-view").hidden = false;
  loadTrash(false);
}

function renderTrash() {
  const badge = $("#trash-count-badge");
  if (badge) badge.textContent = String(allTrash.length);

  if (!allTrash.length) {
    trashBody.innerHTML = '<tr><td colspan="4" class="empty">Recycle Bin is empty.</td></tr>';
    updateTrashBulkBar();
    return;
  }

  trashBody.innerHTML = allTrash
    .map(({ index, job, days_remaining: daysRemaining }) => {
      const selectedClass = selectedTrashIndices.has(index) ? "selected" : "";
      const ariaSelected = selectedTrashIndices.has(index) ? "true" : "false";
      const deletedLabel = formatDateTime(job.deleted_at || "");
      const remainingLabel =
        daysRemaining === 0 ? "Today" : `${daysRemaining} day${daysRemaining === 1 ? "" : "s"}`;
      return `<tr class="trash-row job-row ${selectedClass}" data-index="${index}" aria-selected="${ariaSelected}" tabindex="0">
        <td><strong>${escapeHtml(title(job))}</strong></td>
        <td>${escapeHtml(deletedLabel || "—")}</td>
        <td>${escapeHtml(remainingLabel)}</td>
        <td class="actions">
          <div class="actions-inner">
            <button type="button" class="small btn-trash-restore" data-index="${index}">Restore</button>
            <button type="button" class="small danger btn-trash-permanent" data-index="${index}">Delete permanently</button>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  trashBody.querySelectorAll("tr.trash-row").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      toggleTrashSelection(parseInt(row.dataset.index, 10));
    });
    row.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      if (e.target.closest("button")) return;
      e.preventDefault();
      toggleTrashSelection(parseInt(row.dataset.index, 10));
    });
  });

  trashBody.querySelectorAll(".btn-trash-restore").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      await restoreTrashJobs([parseInt(btn.dataset.index, 10)]);
    });
  });

  trashBody.querySelectorAll(".btn-trash-permanent").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      await permanentDeleteTrashJobs([parseInt(btn.dataset.index, 10)]);
    });
  });

  updateTrashBulkBar();
}

async function loadTrash(resetSelection = true) {
  try {
    const [items, info] = await Promise.all([api("/api/trash"), api("/api/trash/info")]);
    allTrash = items;
    trashRetentionDays = info.retention_days || 30;
    $("#trash-subtitle").textContent = `Deleted jobs are kept for ${trashRetentionDays} days, then removed automatically.`;
    if (info.purged > 0) {
      showMessage(`Permanently removed ${info.purged} expired job${info.purged === 1 ? "" : "s"}`);
    }
    if (resetSelection) clearTrashSelection();
    else pruneTrashSelection();
    renderTrash();
  } catch (err) {
    trashBody.innerHTML = `<tr><td colspan="4" class="empty">Failed to load Recycle Bin: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function restoreTrashJobs(indices) {
  if (!indices.length) return;
  const labels = indices
    .map((idx) => allTrash.find((item) => item.index === idx))
    .filter(Boolean)
    .map((item) => title(item.job));
  const count = indices.length;
  const ok = await confirmAction({
    title: "Restore jobs?",
    message: `Restore ${count} job${count === 1 ? "" : "s"} to Job Tracker?${formatJobListPreview(labels)}`,
    confirmLabel: "Restore",
  });
  if (!ok) return;
  try {
    const result = await api("/api/trash/bulk", {
      method: "POST",
      body: JSON.stringify({ indices, action: "restore" }),
    });
    clearTrashSelection();
    await loadTrash(false);
    await loadJobs(false);
    showJobsView();
    showMessage(`Restored ${result.updated} job${result.updated === 1 ? "" : "s"}`);
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function permanentDeleteTrashJobs(indices) {
  if (!indices.length) return;
  const labels = indices
    .map((idx) => allTrash.find((item) => item.index === idx))
    .filter(Boolean)
    .map((item) => title(item.job));
  if (!(await confirmPermanentDelete(labels))) return;
  try {
    const result = await api("/api/trash/bulk", {
      method: "POST",
      body: JSON.stringify({ indices, action: "permanent_delete" }),
    });
    clearTrashSelection();
    await loadTrash(false);
    showMessage(`Permanently deleted ${result.updated} job${result.updated === 1 ? "" : "s"}`);
  } catch (err) {
    showMessage(err.message, true);
  }
}

function switchTab(tabName) {
  document.querySelectorAll(".app-tab").forEach((tab) => {
    const selected = tab.dataset.tab === tabName;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", selected ? "true" : "false");
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const show = panel.dataset.panel === tabName;
    panel.classList.toggle("active", show);
    panel.hidden = !show;
  });
  if (tabName === "jobs" && jobsSubView === "trash") {
    showTrashView();
  }
  if (tabName === "dashboard") {
    renderDashboardFromLocal();
    fetchAndRenderAnalytics();
  }
  if (tabName === "settings") {
    loadDigestSettings();
  }
}

document.querySelectorAll(".app-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    if (tab.dataset.tab === "jobs") showJobsView();
    switchTab(tab.dataset.tab);
  });
});

document.querySelectorAll(".period-btn").forEach((btn) => {
  btn.addEventListener("click", () => setDashboardPeriod(btn.dataset.period));
});

$("#btn-open-trash").addEventListener("click", () => showTrashView());
$("#btn-back-jobs").addEventListener("click", () => showJobsView());

$("#btn-trash-restore").addEventListener("click", () => restoreTrashJobs([...selectedTrashIndices]));
$("#btn-trash-permanent").addEventListener("click", () => permanentDeleteTrashJobs([...selectedTrashIndices]));
$("#btn-trash-clear").addEventListener("click", () => clearTrashSelection());

$("#btn-edit-profile").addEventListener("click", () => openProfileEditor());

profileForm.addEventListener("submit", saveProfile);
$("#btn-profile-cancel").addEventListener("click", () => {
  destroyProfileEditors();
  profileDialog.close();
});

/* —— Digest settings —— */
const digestForm = $("#digest-form");
const digestCompaniesEl = $("#digest-companies");
const digestPreview = $("#digest-preview");

function companyRowHtml(company = {}) {
  const name = escapeHtml(company.name || "");
  const url = escapeHtml(company.careers_url || "");
  const aliases = escapeHtml((company.aliases || []).join(", "));
  return `<div class="digest-company-row">
    <div class="digest-company-fields">
      <input type="text" class="digest-co-name" placeholder="Company name" value="${name}" required />
      <input type="text" class="digest-co-aliases" placeholder="Aliases (comma-separated)" value="${aliases}" />
    </div>
    <div class="digest-company-fields">
      <input type="url" class="digest-co-url" placeholder="Careers / ATS board URL" value="${url}" />
    </div>
    <button type="button" class="danger digest-co-remove" aria-label="Remove company">Remove</button>
  </div>`;
}

function renderDigestCompanies(companies) {
  const list = companies && companies.length ? companies : [{}];
  digestCompaniesEl.innerHTML = list.map(companyRowHtml).join("");
  digestCompaniesEl.querySelectorAll(".digest-co-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".digest-company-row")?.remove();
      if (!digestCompaniesEl.children.length) {
        digestCompaniesEl.insertAdjacentHTML("beforeend", companyRowHtml({}));
        bindDigestRemoveButtons();
      }
    });
  });
}

function bindDigestRemoveButtons() {
  digestCompaniesEl.querySelectorAll(".digest-co-remove").forEach((btn) => {
    btn.onclick = () => {
      btn.closest(".digest-company-row")?.remove();
      if (!digestCompaniesEl.children.length) {
        digestCompaniesEl.insertAdjacentHTML("beforeend", companyRowHtml({}));
        bindDigestRemoveButtons();
      }
    };
  });
}

function collectDigestCompanies() {
  return [...digestCompaniesEl.querySelectorAll(".digest-company-row")]
    .map((row) => {
      const name = row.querySelector(".digest-co-name")?.value.trim() || "";
      const careers_url = row.querySelector(".digest-co-url")?.value.trim() || "";
      const aliasesRaw = row.querySelector(".digest-co-aliases")?.value || "";
      const aliases = aliasesRaw.split(",").map((a) => a.trim()).filter(Boolean);
      return { name, careers_url, aliases };
    })
    .filter((c) => c.name);
}

async function loadDigestSettings() {
  try {
    const data = await api("/api/digest/settings");
    $("#digest-enabled").checked = !!data.enabled;
    $("#digest-careers").checked = data.careers_enabled !== false;
    $("#digest-remote").checked = data.include_remote !== false;
    $("#digest-email").value = data.recipient_email || "";
    $("#digest-hour").value = data.hour ?? 8;
    $("#digest-min-score").value = data.min_score ?? 55;
    $("#digest-max-results").value = data.max_results ?? 25;
    $("#digest-location-source").value = data.location_source || "profile";
    $("#digest-locations").value = (data.locations || []).join(", ");
    renderDigestCompanies(data.preferred_companies || []);
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function saveDigestSettings(e) {
  e.preventDefault();
  const locationsRaw = $("#digest-locations").value || "";
  const body = {
    enabled: $("#digest-enabled").checked,
    careers_enabled: $("#digest-careers").checked,
    include_remote: $("#digest-remote").checked,
    recipient_email: $("#digest-email").value.trim(),
    hour: Number($("#digest-hour").value) || 8,
    weekdays: [1, 2, 3, 4, 5],
    timezone_note: "GMT+10",
    preferred_companies: collectDigestCompanies(),
    min_score: Number($("#digest-min-score").value) || 55,
    max_results: Number($("#digest-max-results").value) || 25,
    days: 3,
    pages: 2,
    company_boost: 15,
    location_source: $("#digest-location-source").value || "profile",
    locations: locationsRaw.split(",").map((s) => s.trim()).filter(Boolean),
  };
  try {
    await api("/api/digest/settings", { method: "PUT", body: JSON.stringify(body) });
    showMessage("Digest settings saved");
    await loadDigestSettings();
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function runDigestTest(dryRun) {
  digestPreview.hidden = false;
  digestPreview.textContent = dryRun ? "Running preview…" : "Sending test email…";
  try {
    const result = await api("/api/digest/test", {
      method: "POST",
      body: JSON.stringify({ dry_run: dryRun }),
    });
    const lines = [
      result.ok ? "OK" : `Skipped: ${result.reason || "unknown"}`,
      `Recipient: ${result.recipient || "(none)"}`,
      `Matches: ${result.count}`,
      result.sent ? "Email sent." : "Email not sent.",
      "",
      result.plain || "",
    ];
    digestPreview.textContent = lines.join("\n");
    showMessage(dryRun ? `Preview: ${result.count} match(es)` : result.sent ? "Test email sent" : "Digest finished");
  } catch (err) {
    digestPreview.textContent = err.message;
    showMessage(err.message, true);
  }
}

if (digestForm) {
  digestForm.addEventListener("submit", saveDigestSettings);
  $("#btn-add-company")?.addEventListener("click", () => {
    digestCompaniesEl.insertAdjacentHTML("beforeend", companyRowHtml({}));
    bindDigestRemoveButtons();
  });
  $("#btn-digest-dry")?.addEventListener("click", () => runDigestTest(true));
  $("#btn-digest-send")?.addEventListener("click", async () => {
    const ok = await confirmAction({
      title: "Send test digest?",
      message: "This will scrape jobs and send a real email via your SMTP settings. Continue?",
      confirmLabel: "Send",
      danger: false,
    });
    if (ok) runDigestTest(false);
  });
}

(async function init() {
  try {
    dashboardPeriod = loadDashboardPeriod();
    syncPeriodButtons();
    const savedDateFilter = loadJobDateFilter();
    jobDatePreset = savedDateFilter.preset;
    jobDateFrom = savedDateFilter.from;
    jobDateTo = savedDateFilter.to;
    syncJobDateFilterUi();
    await loadStatuses();
    await loadProfile();
    const { revision } = await api("/api/revision");
    lastRevision = revision;
    await loadJobs();
    await loadTrash(false);
    switchTab("dashboard");
    startRevisionPolling();
  } catch (err) {
    jobsBody.innerHTML = `<tr><td colspan="6" class="empty">Failed to load: ${escapeHtml(err.message)}</td></tr>`;
    const summaryEl = $("#dashboard-summary");
    if (summaryEl) summaryEl.textContent = `Failed to load: ${err.message}`;
  }
})();
