let statusesConfig = { default_status: "draft", statuses: [] };

const $ = (sel) => document.querySelector(sel);
const jobsBody = $("#jobs-body");
const dialog = $("#job-dialog");
const form = $("#job-form");
const messageEl = $("#message");

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

function fileLink(path, label) {
  if (!path) return `<span class="missing">${label}: —</span>`;
  const url = `/api/files?path=${encodeURIComponent(path)}`;
  return `<a href="${url}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
}

function attachmentCell(job) {
  const cv = job.cv_file;
  const cover = job.cover_letter_file;
  const parts = [];
  if (cv) {
    parts.push(fileLink(cv, "CV"));
    const pdf = cv.replace(/\.tex$/i, ".pdf");
    if (pdf !== cv) parts.push(fileLink(pdf, "CV PDF"));
  } else {
    parts.push('<span class="missing">CV: —</span>');
  }
  if (cover) {
    parts.push(fileLink(cover, "Letter"));
    const pdf = cover.replace(/\.tex$/i, ".pdf");
    if (pdf !== cover) parts.push(fileLink(pdf, "Letter PDF"));
  } else {
    parts.push('<span class="missing">Letter: —</span>');
  }
  return `<div class="attachments">${parts.join("")}</div>`;
}

function statusSelect(index, current) {
  const opts = statusesConfig.statuses
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === current ? "selected" : ""}>${escapeHtml(s)}</option>`
    )
    .join("");
  return `<select class="status-select" data-index="${index}" aria-label="Status">${opts}</select>`;
}

function renderJobs(items) {
  if (!items.length) {
    jobsBody.innerHTML = '<tr><td colspan="6" class="empty">No applications yet. Add one above.</td></tr>';
    return;
  }
  jobsBody.innerHTML = items
    .map(({ index, job }) => {
      const link = job.source
        ? `<a href="${escapeHtml(job.source)}" target="_blank" rel="noopener">Open</a>`
        : '<span class="missing">—</span>';
      const notes = job.notes
        ? `<span class="notes-preview" title="${escapeHtml(job.notes)}">${escapeHtml(job.notes)}</span>`
        : '<span class="missing">—</span>';
      return `<tr>
        <td><strong>${escapeHtml(title(job))}</strong><br><small class="missing">${escapeHtml(job.date || "")}</small></td>
        <td>${link}</td>
        <td>${statusSelect(index, job.status || statusesConfig.default_status)}</td>
        <td>${attachmentCell(job)}</td>
        <td>${notes}</td>
        <td class="actions">
          <button type="button" class="small btn-edit" data-index="${index}">Edit</button>
          <button type="button" class="small danger btn-delete" data-index="${index}">Delete</button>
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
      } catch (err) {
        showMessage(err.message, true);
        await loadJobs();
      }
    });
  });

  jobsBody.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", () => openEdit(parseInt(btn.dataset.index, 10)));
  });

  jobsBody.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = parseInt(btn.dataset.index, 10);
      if (!confirm("Delete this application?")) return;
      try {
        await api(`/api/jobs/${idx}`, { method: "DELETE" });
        showMessage("Deleted");
        await loadJobs();
      } catch (err) {
        showMessage(err.message, true);
      }
    });
  });
}

async function loadStatuses() {
  statusesConfig = await api("/api/statuses");
}

async function loadJobs() {
  const items = await api("/api/jobs");
  renderJobs(items);
}

function openAdd() {
  $("#dialog-title").textContent = "Add job";
  $("#job-index").value = "";
  form.reset();
  $("#field-status").innerHTML = statusesConfig.statuses
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === statusesConfig.default_status ? "selected" : ""}>${escapeHtml(s)}</option>`
    )
    .join("");
  dialog.showModal();
}

async function openEdit(index) {
  const items = await api("/api/jobs");
  const item = items.find((i) => i.index === index);
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
  $("#field-status").innerHTML = statusesConfig.statuses
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${s === (job.status || statusesConfig.default_status) ? "selected" : ""}>${escapeHtml(s)}</option>`
    )
    .join("");
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
    await loadJobs();
  } catch (err) {
    showMessage(err.message, true);
  }
});

$("#btn-add").addEventListener("click", openAdd);
$("#btn-cancel").addEventListener("click", () => dialog.close());

(async function init() {
  try {
    await loadStatuses();
    await loadJobs();
  } catch (err) {
    jobsBody.innerHTML = `<tr><td colspan="6" class="empty">Failed to load: ${escapeHtml(err.message)}</td></tr>`;
  }
})();
