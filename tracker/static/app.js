let statusesConfig = { default_status: "draft", statuses: [], labels: {} };
let lastRevision = 0;
let allJobs = [];
let searchQuery = "";
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
  const opts = statusesConfig.statuses
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === current ? "selected" : ""}>${escapeHtml(statusLabel(s))}</option>`
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
  if (!q) return jobs;
  return jobs.filter(({ job }) => jobSearchText(job).includes(q));
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
    jobsBody.innerHTML = '<tr><td colspan="5" class="empty">No applications yet. Add one above.</td></tr>';
    updatePaginationControls(1, 0, 0);
    updateSelectAllButton();
    return;
  }
  if (!items.length) {
    jobsBody.innerHTML = `<tr><td colspan="5" class="empty">No jobs match “${escapeHtml(searchQuery.trim())}”.</td></tr>`;
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
      try {
        await api(`/api/jobs/${idx}`, {
          method: "PUT",
          body: JSON.stringify({ status: e.target.value }),
        });
        showMessage("Status updated");
        await loadJobs(false);
      } catch (err) {
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
  selectEl.innerHTML = statusesConfig.statuses
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === selected ? "selected" : ""}>${escapeHtml(statusLabel(s))}</option>`
    )
    .join("");
}

async function loadStatuses() {
  statusesConfig = await api("/api/statuses");
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
}

async function bulkChangeStatus() {
  const indices = [...selectedJobIndices];
  if (!indices.length) return;
  const status = $("#bulk-status").value;
  try {
    const result = await api("/api/jobs/bulk", {
      method: "POST",
      body: JSON.stringify({ indices, action: "update_status", status }),
    });
    clearSelection();
    await loadJobs(false);
    showMessage(`Updated status for ${result.updated} job${result.updated === 1 ? "" : "s"}`);
  } catch (err) {
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
}

document.querySelectorAll(".app-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    if (tab.dataset.tab === "jobs") showJobsView();
    switchTab(tab.dataset.tab);
  });
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

(async function init() {
  try {
    await loadStatuses();
    await loadProfile();
    const { revision } = await api("/api/revision");
    lastRevision = revision;
    await loadJobs();
    await loadTrash(false);
    startRevisionPolling();
  } catch (err) {
    jobsBody.innerHTML = `<tr><td colspan="5" class="empty">Failed to load: ${escapeHtml(err.message)}</td></tr>`;
  }
})();
