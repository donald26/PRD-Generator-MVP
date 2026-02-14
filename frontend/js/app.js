/**
 * App shell — hash-based router, global state, screen orchestration.
 */

// ── Global state ────────────────────────────────────────────────────────

const AppState = {
  currentProjectId: null,
  currentSessionId: null,
  sessionData: null,
  questionnaireSchema: null,
  pollTimers: {},
};

// ── Route table ─────────────────────────────────────────────────────────

const ROUTES = {
  '#projects':      renderProjectsScreen,
  '#assessments':   renderAssessmentsScreen,
  '#questionnaire': renderQuestionnaireScreen,
  '#upload':        renderUploadScreen,
  '#dashboard':     renderDashboardScreen,
  '#review':        renderReviewScreen,
};

// ── Router ──────────────────────────────────────────────────────────────

function navigate(hash) {
  window.location.hash = hash;
}

function getHashParams() {
  const hash = window.location.hash;
  const qIdx = hash.indexOf('?');
  const route = qIdx >= 0 ? hash.slice(0, qIdx) : hash;
  const params = {};
  if (qIdx >= 0) {
    const qs = hash.slice(qIdx + 1);
    qs.split('&').forEach(pair => {
      const [k, v] = pair.split('=');
      if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || '');
    });
  }
  return { route, params };
}

function onHashChange() {
  // Stop any active polling
  Object.values(AppState.pollTimers).forEach(clearTimeout);
  AppState.pollTimers = {};

  const { route, params } = getHashParams();

  // Update state from URL params
  if (params.project) AppState.currentProjectId = params.project;
  if (params.session) AppState.currentSessionId = params.session;

  // Hide all screens
  document.querySelectorAll('[data-screen]').forEach(el => el.classList.add('hidden'));

  // Find and call route handler
  const handler = ROUTES[route];
  if (handler) {
    handler(params);
  } else {
    // Default to projects
    navigate('#projects');
  }
}

// ── Screen visibility helper ────────────────────────────────────────────

function showScreen(screenId) {
  const el = document.querySelector(`[data-screen="${screenId}"]`);
  if (el) el.classList.remove('hidden');
}

// ── Init ────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  window.addEventListener('hashchange', onHashChange);

  // Check API health
  api.health().then(() => {
    document.getElementById('api-status').innerHTML =
      '<span class="w-2 h-2 rounded-full bg-green-500 inline-block"></span> Connected';
  }).catch(() => {
    document.getElementById('api-status').innerHTML =
      '<span class="w-2 h-2 rounded-full bg-red-500 inline-block"></span> Disconnected';
  });

  // Initial route
  if (!window.location.hash || window.location.hash === '#') {
    navigate('#projects');
  } else {
    onHashChange();
  }
});

// ═══════════════════════════════════════════════════════════════════════
// Screen Renderers
// ═══════════════════════════════════════════════════════════════════════

// ── Screen 1: Projects ──────────────────────────────────────────────────

function renderProjectsScreen() {
  showScreen('projects');
  renderBreadcrumb([{ label: 'Projects' }]);

  const projects = store.getProjects();
  const grid = document.getElementById('projects-grid');
  const form = document.getElementById('new-project-form');

  if (projects.length === 0) {
    grid.innerHTML = renderEmptyState('📁', 'No projects yet', 'Create your first project to get started.');
  } else {
    grid.innerHTML = projects.map(p => {
      const count = p.session_ids ? p.session_ids.length : 0;
      return `<div class="bg-white rounded-lg border border-gray-200 shadow-sm p-5 cursor-pointer hover:shadow-md hover:border-blue-300 transition-shadow"
                   onclick="navigate('#assessments?project=${p.id}')">
        <h3 class="font-semibold text-gray-900 mb-1">${esc(p.name)}</h3>
        <p class="text-sm text-gray-500 mb-3">${esc(p.client)} &middot; ${esc(p.industry)}</p>
        <div class="flex justify-between items-center text-xs text-gray-400">
          <span>${count} assessment${count !== 1 ? 's' : ''}</span>
          <span>${timeAgo(p.created_at)}</span>
        </div>
      </div>`;
    }).join('');
  }

  // Wire new project form
  form.onsubmit = (e) => {
    e.preventDefault();
    const name = document.getElementById('proj-name').value.trim();
    const client = document.getElementById('proj-client').value.trim();
    const industry = document.getElementById('proj-industry').value;
    if (!name || !client) { showToast('Name and client are required.', 'error'); return; }
    store.createProject(name, client, industry);
    form.reset();
    document.getElementById('new-project-panel').classList.add('hidden');
    renderProjectsScreen();
    showToast('Project created.', 'success');
  };
}

function toggleNewProjectPanel() {
  const panel = document.getElementById('new-project-panel');
  panel.classList.toggle('hidden');
  if (!panel.classList.contains('hidden')) {
    document.getElementById('proj-name').focus();
  }
}

// ── Screen 2: Assessments ───────────────────────────────────────────────

async function renderAssessmentsScreen(params) {
  showScreen('assessments');
  const projectId = params.project || AppState.currentProjectId;
  AppState.currentProjectId = projectId;
  const project = store.getProject(projectId);

  if (!project) { navigate('#projects'); return; }

  renderBreadcrumb([
    { label: 'Projects', hash: '#projects' },
    { label: project.name },
  ]);

  document.getElementById('assessments-project-name').textContent = project.name;
  const list = document.getElementById('assessments-list');
  const pathPanel = document.getElementById('path-select-panel');
  pathPanel.classList.add('hidden');

  // Load sessions from API
  if (!project.session_ids || project.session_ids.length === 0) {
    list.innerHTML = renderEmptyState('📋', 'No assessments yet', 'Create a new assessment to begin.');
    return;
  }

  list.innerHTML = '<p class="text-sm text-gray-400">Loading...</p>';

  try {
    const data = await api.listSessions();
    const sessions = data.sessions.filter(s => project.session_ids.includes(s.id));

    if (sessions.length === 0) {
      list.innerHTML = renderEmptyState('📋', 'No assessments found', 'Create a new assessment to begin.');
      return;
    }

    list.innerHTML = sessions.map(s => {
      const statusBadge = renderStatusBadge(mapSessionStatus(s.status));
      const flowBadge = renderFlowBadge(s.flow_type);
      const route = getSessionRoute(s);
      return `<div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 cursor-pointer hover:shadow-md hover:border-blue-300 transition-shadow mb-3"
                   onclick="navigate('${route}')">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">${flowBadge} ${statusBadge}</div>
          <span class="text-xs text-gray-400">${timeAgo(s.updated_at || s.created_at)}</span>
        </div>
        <p class="text-xs text-gray-500 font-mono">${s.id.slice(0, 12)}...</p>
      </div>`;
    }).join('');
  } catch (err) {
    list.innerHTML = `<p class="text-sm text-red-500">Error loading sessions: ${esc(err.message)}</p>`;
  }
}

function mapSessionStatus(status) {
  if (status.startsWith('phase_')) return 'generating';
  return STATUS_CONFIG[status] ? status : 'intake';
}

function getSessionRoute(session) {
  const s = session.status;
  if (s === 'intake' || s === 'questionnaire_done') {
    return `#questionnaire?session=${session.id}`;
  }
  return `#dashboard?session=${session.id}`;
}

function showPathSelection() {
  document.getElementById('path-select-panel').classList.remove('hidden');
}

async function selectPath(flowType) {
  const projectId = AppState.currentProjectId;
  if (!projectId) return;

  try {
    const result = await api.createSession(flowType);
    store.addSessionToProject(projectId, result.session_id);
    store.cacheSessionMeta(result.session_id, {
      flow_type: result.flow_type,
      questionnaire: result.questionnaire,
      questionnaire_version: result.questionnaire_version,
    });
    AppState.currentSessionId = result.session_id;
    navigate(`#questionnaire?session=${result.session_id}`);
  } catch (err) {
    showToast('Failed to create session: ' + err.message, 'error');
  }
}

// ── Screen 4: Questionnaire ─────────────────────────────────────────────
// (delegated to questionnaire.js — renderQuestionnaireScreen)

// ── Screen 5: Upload ────────────────────────────────────────────────────

function renderUploadScreen(params) {
  showScreen('upload');
  const sessionId = params.session || AppState.currentSessionId;
  AppState.currentSessionId = sessionId;

  const project = store.getProject(AppState.currentProjectId);
  renderBreadcrumb([
    { label: 'Projects', hash: '#projects' },
    { label: project ? project.name : 'Project', hash: `#assessments?project=${AppState.currentProjectId}` },
    { label: 'Upload Documents' },
  ]);

  const fileList = document.getElementById('upload-file-list');
  const dropZone = document.getElementById('upload-drop-zone');
  const fileInput = document.getElementById('upload-file-input');
  let selectedFiles = [];

  fileList.innerHTML = '';

  function updateFileDisplay() {
    if (selectedFiles.length === 0) {
      fileList.innerHTML = '<p class="text-sm text-gray-400">No files selected</p>';
    } else {
      fileList.innerHTML = selectedFiles.map((f, i) =>
        `<div class="flex items-center justify-between py-1.5 px-2 bg-gray-50 rounded text-sm mb-1">
          <span class="text-gray-700">${esc(f.name)}</span>
          <button onclick="removeUploadFile(${i})" class="text-red-400 hover:text-red-600 text-xs ml-2">Remove</button>
        </div>`
      ).join('');
    }
    document.getElementById('upload-count').textContent = `${selectedFiles.length} file(s) selected`;
  }

  // Store in window for event handlers
  window._uploadFiles = selectedFiles;
  window.removeUploadFile = (idx) => {
    selectedFiles.splice(idx, 1);
    updateFileDisplay();
  };

  dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add('border-blue-400', 'bg-blue-50'); };
  dropZone.ondragleave = () => { dropZone.classList.remove('border-blue-400', 'bg-blue-50'); };
  dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-blue-400', 'bg-blue-50');
    const files = Array.from(e.dataTransfer.files).filter(f =>
      ['.txt', '.md', '.docx'].some(ext => f.name.toLowerCase().endsWith(ext))
    );
    selectedFiles.push(...files);
    updateFileDisplay();
  };

  fileInput.onchange = () => {
    selectedFiles.push(...Array.from(fileInput.files));
    updateFileDisplay();
    fileInput.value = '';
  };

  document.getElementById('upload-submit-btn').onclick = async () => {
    if (selectedFiles.length === 0) { showToast('Please select at least one file.', 'error'); return; }
    try {
      document.getElementById('upload-submit-btn').disabled = true;
      document.getElementById('upload-submit-btn').textContent = 'Uploading...';
      await api.uploadDocuments(sessionId, selectedFiles);
      showToast(`${selectedFiles.length} file(s) uploaded.`, 'success');
      navigate(`#dashboard?session=${sessionId}`);
    } catch (err) {
      showToast('Upload failed: ' + err.message, 'error');
      document.getElementById('upload-submit-btn').disabled = false;
      document.getElementById('upload-submit-btn').textContent = 'Upload & Continue';
    }
  };

  document.getElementById('upload-skip-btn').onclick = () => {
    navigate(`#dashboard?session=${sessionId}`);
  };

  updateFileDisplay();
}

// ── Screen 6: Dashboard ─────────────────────────────────────────────────
// (delegated to dashboard.js — renderDashboardScreen)

// ── Screen 6b: Review ───────────────────────────────────────────────────
// (delegated to review.js — renderReviewScreen)

// ── Utility ─────────────────────────────────────────────────────────────

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
