let statusesConfig = { default_status: "draft", statuses: [], labels: {} };
let lastRevision = 0;
let allJobs = [];
let pageSize = 10;
let currentPage = 1;
const REVISION_POLL_MS = 3000;

const $ = (sel) => document.querySelector(sel);
const jobsBody = $("#jobs-body");
const dialog = $("#job-dialog");
const linkDialog = $("#link-dialog");
const linkForm = $("#link-form");
const form = $("#job-form");
const messageEl = $("#message");
const btnDelete = $("#btn-delete");

function showMessage(text, isError = false) {
  messageEl.textContent = text;
  messageEl.classList.toggle("error", isError);
  messageEl.classList.remove("hidden");
  setTimeout(() => messageEl.classList.add("hidden"), 4000);
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
  } else {
    parts.push('<span class="missing">Cover Letter PDF: —</span>');
  }
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

function updatePaginationControls(totalPages, total) {
  $("#page-info").textContent = `Page ${currentPage} of ${totalPages} (${total} total)`;
  $("#btn-prev").disabled = currentPage <= 1;
  $("#btn-next").disabled = currentPage >= totalPages;
}

function renderJobs() {
  const items = allJobs;
  if (!items.length) {
    jobsBody.innerHTML = '<tr><td colspan="5" class="empty">No applications yet. Add one above.</td></tr>';
    updatePaginationControls(1, 0);
    return;
  }

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * pageSize;
  const pageItems = items.slice(start, start + pageSize);
  updatePaginationControls(totalPages, items.length);

  jobsBody.innerHTML = pageItems
    .map(({ index, job }) => {
      const notes = job.notes
        ? `<span class="notes-preview" title="${escapeHtml(job.notes)}">${escapeHtml(job.notes)}</span>`
        : '<span class="missing">—</span>';
      return `<tr>
        <td>${titleCell(job, index)}</td>
        <td>${statusSelect(index, job.status || statusesConfig.default_status)}</td>
        <td>${attachmentCell(job)}</td>
        <td>${notes}</td>
        <td class="actions">
          <button type="button" class="small btn-edit" data-index="${index}">Edit</button>
        </td>
      </tr>`;
    })
    .join("");

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

function renderProfile(data) {
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
        <ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>`
    )
    .join("");
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
  renderJobs();
}

async function pollRevision() {
  if (dialog.open || linkDialog.open) return;
  try {
    const { revision } = await api("/api/revision");
    if (revision === lastRevision) return;
    const hadPrior = lastRevision !== 0;
    lastRevision = revision;
    if (hadPrior) {
      await loadJobs(false);
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
  if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;
  try {
    await api(`/api/jobs/${indexStr}`, { method: "DELETE" });
    dialog.close();
    showMessage("Deleted");
    await loadJobs(true);
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
  const totalPages = Math.max(1, Math.ceil(allJobs.length / pageSize));
  if (currentPage < totalPages) {
    currentPage += 1;
    renderJobs();
  }
});

(async function init() {
  try {
    await loadStatuses();
    await loadProfile();
    const { revision } = await api("/api/revision");
    lastRevision = revision;
    await loadJobs();
    startRevisionPolling();
  } catch (err) {
    jobsBody.innerHTML = `<tr><td colspan="5" class="empty">Failed to load: ${escapeHtml(err.message)}</td></tr>`;
  }
})();
