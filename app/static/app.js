// Project-to-Reach: Personal AI Marketing Agent Frontend Controller
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ================= TOAST NOTIFICATIONS =================

function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// ================= MODAL CONTROLLER =================

function openModal(id) {
  const el = $('#' + id);
  if (el) el.classList.add('show');
}

function closeModal(id) {
  const el = $('#' + id);
  if (el) el.classList.remove('show');
}

document.querySelectorAll('.modal-backdrop').forEach(modal => {
  modal.addEventListener('click', e => {
    if (e.target === modal) modal.classList.remove('show');
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.show').forEach(m => m.classList.remove('show'));
  }
});

// ================= API CLIENT =================

async function api(path, opts = {}) {
  const res = await fetch('/api/v1' + path, {
    headers: opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...opts
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || 'Request failed. Please try again.');
  }
  return data;
}

// ================= NAVIGATION ROUTER =================

const VIEW_TITLES = {
  'overview': 'Overview',
  'projects': 'Projects & Ground Truth',
  'generator': 'Campaign Generator',
  'studio': 'Content Studio',
  'approvals': 'Approval Queue',
  'calendar': 'Content Calendar',
  'distribution': 'Distribution Tracker',
  'analytics': 'Analytics & Reach',
  'settings': 'Settings & AI Configuration'
};

function navigate(viewName) {
  // Update hash
  window.location.hash = viewName;

  // Toggle active view panel
  $$('.view-panel').forEach(p => p.classList.remove('active'));
  const targetPanel = $('#view-' + viewName);
  if (targetPanel) {
    targetPanel.classList.add('active');
  } else {
    $('#view-overview').classList.add('active');
    viewName = 'overview';
  }

  // Toggle sidebar active nav
  $$('.nav-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-view') === viewName);
  });

  // Update breadcrumb
  const title = VIEW_TITLES[viewName] || 'Overview';
  const titleEl = $('#current-view-title');
  if (titleEl) titleEl.textContent = title;

  // Lazy refresh section data if needed
  if (viewName === 'settings') {
    loadAuditLogs();
  }
}

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.replace('#', '') || 'overview';
  navigate(hash);
});

// ================= PROJECT ACTIONS =================

// Add Project Form
const projectForm = $('#project-form');
if (projectForm) {
  projectForm.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(projectForm);
    const payload = Object.fromEntries(fd);
    const errEl = $('#project-error');
    errEl.textContent = '';
    const btn = projectForm.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Saving project & analyzing…';

    try {
      await api('/projects', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Project saved and brief generated!');
      closeModal('project-modal');
      setTimeout(() => window.location.reload(), 600);
    } catch (err) {
      errEl.textContent = err.message;
      btn.disabled = false;
      btn.textContent = 'Save Project';
    }
  });
}

// Project Brief Modal
let activeBriefProjectId = null;
async function openProjectBriefModal(projectId) {
  activeBriefProjectId = projectId;
  openModal('brief-modal');
  const contentEl = $('#brief-content');
  contentEl.innerHTML = '<div class="text-muted">Loading project brief…</div>';

  try {
    const project = await api(`/projects/${projectId}`);
    $('#brief-project-name').textContent = `${project.name} · Project Brief`;
    const b = project.brief;

    if (!b) {
      contentEl.innerHTML = `
        <div class="empty-state compact">
          <p>No brief analyzed yet for this project.</p>
          <button class="primary small-btn" onclick="reanalyzeBrief()">Analyze Now</button>
        </div>
      `;
      return;
    }

    const featuresHtml = (b.verified_features || []).map(f => `<li>${escapeHtml(f)}</li>`).join('') || '<li>None recorded yet</li>';
    const evidenceHtml = (b.evidence_and_sources || []).map(e => `<li>${escapeHtml(e)}</li>`).join('') || '<li>Project description</li>';
    const unknownsHtml = (b.unknown_or_unverified_claims || []).map(u => `<li>${escapeHtml(u)}</li>`).join('') || '<li>No unknown claims identified</li>';

    contentEl.innerHTML = `
      <div class="brief-section">
        <h4>Problem Statement</h4>
        <p>${escapeHtml(b.problem || 'Not specified')}</p>
      </div>
      <div class="brief-section">
        <h4>Solution</h4>
        <p>${escapeHtml(b.solution || 'Not specified')}</p>
      </div>
      <div class="brief-section">
        <h4>Target Audience & UVP</h4>
        <p><b>Audience:</b> ${escapeHtml(b.target_audience || 'General builders')}</p>
        <p><b>Unique Value Proposition:</b> ${escapeHtml(b.unique_value_proposition || 'Not specified')}</p>
      </div>
      <div class="brief-section">
        <h4>Verified Capabilities & Features</h4>
        <ul style="margin:4px 0 0; padding-left:18px;">${featuresHtml}</ul>
      </div>
      <div class="brief-section">
        <h4>Ground-Truth Evidence & Sources</h4>
        <ul style="margin:4px 0 0; padding-left:18px; color:var(--muted);">${evidenceHtml}</ul>
      </div>
      <div class="brief-section" style="background:#fff7f7; padding:10px; border-radius:7px; border:1px solid #fee2e2;">
        <h4 style="color:var(--coral);">Unknown / Unverified Claims</h4>
        <ul style="margin:4px 0 0; padding-left:18px; font-size:11px; color:#991b1b;">${unknownsHtml}</ul>
      </div>
    `;
  } catch (err) {
    contentEl.innerHTML = `<div class="form-error">Failed to load brief: ${err.message}</div>`;
  }
}

async function reanalyzeBrief() {
  if (!activeBriefProjectId) return;
  const btn = $('#reanalyze-brief-btn');
  btn.disabled = true;
  btn.textContent = 'Analyzing…';
  try {
    await api(`/projects/${activeBriefProjectId}/analyze`, { method: 'POST' });
    showToast('Project brief updated from latest sources!');
    await openProjectBriefModal(activeBriefProjectId);
  } catch (err) {
    showToast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Re-analyze Brief ⚡';
  }
}

// Upload Documentation Modal
function openUploadModal(projectId, projectName) {
  $('#upload-project-id').value = projectId;
  $('#upload-error').textContent = '';
  $('#upload-file-input').value = '';
  openModal('upload-modal');
}

const uploadForm = $('#upload-form');
if (uploadForm) {
  uploadForm.addEventListener('submit', async e => {
    e.preventDefault();
    const projectId = $('#upload-project-id').value;
    const fileInput = $('#upload-file-input');
    if (!fileInput.files.length) return;

    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    const errEl = $('#upload-error');
    errEl.textContent = '';
    const btn = uploadForm.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Ingesting…';

    try {
      await api(`/projects/${projectId}/sources/upload`, {
        method: 'POST',
        body: fd
      });
      showToast('Document ingested into project ground truth!');
      closeModal('upload-modal');
      setTimeout(() => window.location.reload(), 600);
    } catch (err) {
      errEl.textContent = err.message;
      btn.disabled = false;
      btn.textContent = 'Upload & Ingest';
    }
  });
}

// Fetch GitHub README
async function fetchGithubReadme(projectId, repoUrl) {
  if (!confirm(`Fetch public README.md from ${repoUrl}?`)) return;
  showToast('Fetching public GitHub README…');
  try {
    const res = await api(`/projects/${projectId}/sources/fetch-github`, {
      method: 'POST',
      body: JSON.stringify({ github_url: repoUrl })
    });
    showToast('GitHub README ingested into project sources!');
    setTimeout(() => window.location.reload(), 600);
  } catch (err) {
    alert(`Could not fetch GitHub README: ${err.message}`);
  }
}

// Quick transition to campaign generator with preselected project
function selectProjectForCampaign(projectId, projectName) {
  const select = $('#gen-project-select');
  if (select) select.value = projectId;
  navigate('generator');
}

// ================= CAMPAIGN GENERATOR =================

const campaignForm = $('#campaign-gen-form');
if (campaignForm) {
  campaignForm.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(campaignForm);
    const platforms = fd.getAll('platforms');
    if (!platforms.length) {
      $('#gen-error').textContent = 'Please select at least one platform.';
      return;
    }

    const payload = {
      project_id: Number(fd.get('project_id')),
      objective: fd.get('objective'),
      duration_days: Number(fd.get('duration_days')),
      audience: fd.get('audience'),
      tone: fd.get('tone'),
      cta: fd.get('cta'),
      platforms: platforms
    };

    const errEl = $('#gen-error');
    errEl.textContent = '';
    const btn = $('#generate-submit-btn');
    btn.disabled = true;
    btn.textContent = '✳ Generating multi-channel campaign…';

    try {
      await api('/campaigns', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Campaign generated with multi-channel drafts!');
      setTimeout(() => {
        window.location.hash = 'approvals';
        window.location.reload();
      }, 700);
    } catch (err) {
      errEl.textContent = err.message;
      btn.disabled = false;
      btn.textContent = '✳ Generate Campaign Drafts';
    }
  });
}

// ================= CONTENT STUDIO & APPROVALS =================

function filterStudio(type, value, btn) {
  btn.closest('.filter-group').querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const activePlatform = $('.filter-btn[data-filter-platform].active').getAttribute('data-filter-platform');
  const activeStatus = $('.filter-btn[data-filter-status].active').getAttribute('data-filter-status');

  $$('.asset-card').forEach(card => {
    const cardPlatform = card.getAttribute('data-platform');
    const cardStatus = card.getAttribute('data-status');

    const matchPlatform = activePlatform === 'all' || cardPlatform === activePlatform;
    const matchStatus = activeStatus === 'all' || cardStatus === activeStatus;

    card.style.display = (matchPlatform && matchStatus) ? '' : 'none';
  });
}

// Copy Asset Text
function copyAssetContent(assetId) {
  const card = $(`#asset-card-${assetId}`) || $(`#approval-card-${assetId}`);
  if (!card) return;

  const hook = card.querySelector('.asset-hook, h3')?.textContent || '';
  const body = card.querySelector('.asset-body-preview, .content-text')?.textContent || '';
  const text = `${hook}\n\n${body}`;

  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied content to clipboard!');
  }).catch(() => {
    showToast('Failed to copy. Please copy manually.');
  });
}

// Update Asset Status (Approve / Reject)
async function updateAssetStatus(assetId, newStatus) {
  try {
    await api(`/assets/${assetId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status: newStatus })
    });
    showToast(newStatus === 'approved' ? '✓ Post Approved!' : 'Post Rejected.');
    setTimeout(() => window.location.reload(), 500);
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

// Edit Asset Modal
async function openEditModal(assetId) {
  const form = $('#edit-form');
  form.reset();
  $('#edit-error').textContent = '';
  $('#edit-asset-id').value = assetId;

  try {
    const asset = await api(`/assets/${assetId}`);
    $('#edit-hook').value = asset.hook || '';
    $('#edit-body').value = asset.body || '';
    $('#edit-cta').value = asset.cta || '';
    $('#edit-scheduled-for').value = asset.scheduled_for || '';
    $('#edit-brief').value = asset.creative_brief || '';
    $('#edit-platform-title').textContent = (asset.platform || '').toUpperCase();

    // Toggle button visibility based on status
    const isApproved = asset.status === 'approved';
    $('#edit-approve-btn').style.display = isApproved ? 'none' : '';
    $('#edit-reject-btn').style.display = asset.status === 'rejected' ? 'none' : '';

    openModal('edit-modal');
  } catch (err) {
    showToast(`Failed to load asset: ${err.message}`);
  }
}

const editForm = $('#edit-form');
if (editForm) {
  editForm.addEventListener('submit', async e => {
    e.preventDefault();
    const id = $('#edit-asset-id').value;
    const payload = {
      hook: $('#edit-hook').value,
      body: $('#edit-body').value,
      cta: $('#edit-cta').value,
      scheduled_for: $('#edit-scheduled-for').value,
      creative_brief: $('#edit-brief').value
    };

    const errEl = $('#edit-error');
    errEl.textContent = '';
    try {
      await api(`/assets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      showToast('Changes saved! (Approved assets returned to review)');
      closeModal('edit-modal');
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      errEl.textContent = err.message;
    }
  });
}

async function setAssetStatusFromEdit(status) {
  const id = $('#edit-asset-id').value;
  await updateAssetStatus(id, status);
  closeModal('edit-modal');
}

// Regenerate Asset Modal
function openRegenModal(assetId) {
  $('#regen-asset-id').value = assetId;
  $('#regen-instruction').value = '';
  $('#regen-error').textContent = '';
  openModal('regen-modal');
}

const regenForm = $('#regen-form');
if (regenForm) {
  regenForm.addEventListener('submit', async e => {
    e.preventDefault();
    const id = $('#regen-asset-id').value;
    const instruction = $('#regen-instruction').value;
    const btn = $('#regen-submit-btn');
    btn.disabled = true;
    btn.textContent = '⚡ Regenerating…';
    const errEl = $('#regen-error');
    errEl.textContent = '';

    try {
      await api(`/assets/${id}/regenerate`, {
        method: 'POST',
        body: JSON.stringify({ instruction })
      });
      showToast('Draft regenerated and sent for review!');
      closeModal('regen-modal');
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      errEl.textContent = err.message;
      btn.disabled = false;
      btn.textContent = '⚡ Regenerate Draft';
    }
  });
}

// Version History Modal
async function openHistoryModal(assetId) {
  openModal('history-modal');
  const container = $('#history-container');
  container.innerHTML = '<div class="text-muted">Loading revision history…</div>';

  try {
    const versions = await api(`/assets/${assetId}/versions`);
    if (!versions.length) {
      container.innerHTML = '<div class="empty-state compact"><p>No previous edits recorded. This is the original draft.</p></div>';
      return;
    }

    container.innerHTML = versions.map((v, i) => `
      <div class="history-item">
        <div class="history-meta">Revision ${versions.length - i} · Saved ${v.created_at}</div>
        <h5 style="margin:0 0 6px;">${escapeHtml(v.hook)}</h5>
        <div style="font-size:11.5px; color:var(--ink-secondary); white-space:pre-line;">${escapeHtml(v.body)}</div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="form-error">Could not load revisions: ${err.message}</div>`;
  }
}

// ================= DISTRIBUTION TRACKER =================

function openMarkSharedModal(targetId, targetName) {
  $('#target-id-input').value = targetId;
  $('#target-modal-title').textContent = `Record Live Post: ${targetName}`;
  $('#target-live-url').value = '';
  $('#target-notes').value = '';
  openModal('target-modal');
}

const targetForm = $('#target-form');
if (targetForm) {
  targetForm.addEventListener('submit', async e => {
    e.preventDefault();
    const id = $('#target-id-input').value;
    const payload = {
      live_url: $('#target-live-url').value,
      notes: $('#target-notes').value
    };

    try {
      await api(`/distribution/targets/${id}/shared`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast('Recorded live community share!');
      closeModal('target-modal');
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      showToast(`Error: ${err.message}`);
    }
  });
}

function openAddTargetModal() {
  const targetName = prompt("Enter target community (e.g. r/Python or LinkedIn Group):");
  if (!targetName) return;
  const url = prompt("Enter community URL (e.g. https://reddit.com/r/Python):") || "";
  const rules = prompt("Any specific community rules or self-promo guidelines?") || "";

  // Attach to latest campaign
  api('/campaigns').then(campaigns => {
    if (!campaigns.length) {
      alert("Please create a campaign first.");
      return;
    }
    const campId = campaigns[0].id;
    return api('/distribution/targets', {
      method: 'POST',
      body: JSON.stringify({
        campaign_id: campId,
        platform: targetName.startsWith('r/') ? 'Reddit' : 'LinkedIn',
        target_name: targetName,
        url: url,
        rules_summary: rules
      })
    });
  }).then(() => {
    showToast('Target channel added!');
    setTimeout(() => window.location.reload(), 500);
  }).catch(err => {
    showToast(`Error: ${err.message}`);
  });
}

// ================= ANALYTICS =================

function openMetricModal(assetId = null) {
  const select = $('#metric-asset-select');
  if (assetId && select) {
    select.value = assetId;
  }
  $('#metric-error').textContent = '';
  openModal('metric-modal');
}

const metricForm = $('#metric-form');
if (metricForm) {
  metricForm.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(metricForm);
    const payload = {
      asset_id: Number(fd.get('asset_id')),
      impressions: Number(fd.get('impressions') || 0),
      reach: Number(fd.get('reach') || 0),
      engagements: Number(fd.get('engagements') || 0),
      clicks: Number(fd.get('clicks') || 0),
      video_views: Number(fd.get('video_views') || 0),
      conversions: Number(fd.get('conversions') || 0),
      notes: fd.get('notes') || ''
    };

    const errEl = $('#metric-error');
    errEl.textContent = '';
    try {
      await api('/analytics/metrics', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast('Performance metrics saved and analyzed!');
      closeModal('metric-modal');
      setTimeout(() => {
        window.location.hash = 'analytics';
        window.location.reload();
      }, 500);
    } catch (err) {
      errEl.textContent = err.message;
    }
  });
}

// ================= SETTINGS & AI CONFIGURATION =================

const settingsForm = $('#settings-form');
if (settingsForm) {
  settingsForm.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(settingsForm);
    const payload = Object.fromEntries(fd);

    try {
      await api('/settings', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast('Settings saved successfully!');
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      showToast(`Error saving settings: ${err.message}`);
    }
  });
}

async function testLocalLLMConnection() {
  const btn = $('#test-llm-btn');
  const resultEl = $('#test-llm-result');
  btn.disabled = true;
  btn.textContent = 'Testing…';
  resultEl.textContent = '';

  const payload = {
    ollama_url: $('#setting-ollama-url').value,
    ollama_model: $('#setting-ollama-model').value
  };

  try {
    const res = await api('/settings/test-local-llm', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    resultEl.innerHTML = `<span style="color:var(--mint);">✓ ${res.message}</span>`;
  } catch (err) {
    resultEl.innerHTML = `<span style="color:var(--coral);">✕ ${err.message}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Test Connection';
  }
}

async function loadAuditLogs() {
  const container = $('#audit-log-container');
  if (!container) return;
  try {
    const logs = await api('/audit');
    if (!logs.length) {
      container.innerHTML = '<div class="text-muted" style="font-size:11px;">No audit events yet.</div>';
      return;
    }
    container.innerHTML = logs.map(l => `
      <div class="audit-item">
        <span><b>${escapeHtml(l.action)}</b> (${escapeHtml(l.entity_type)} #${l.entity_id}): ${escapeHtml(l.details || '')}</span>
        <small class="text-muted">${l.created_at.slice(11, 19)}</small>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="form-error">Could not load audit log: ${err.message}</div>`;
  }
}

// ================= UTILITIES =================

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '') || 'overview';
  navigate(hash);
});
