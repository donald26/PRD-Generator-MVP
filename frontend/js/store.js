/**
 * localStorage Manager — projects CRUD + draft questionnaire answers.
 */
const STORAGE_KEY = 'prdgen_v2';

const store = {
  // ── Projects ──────────────────────────────────────────────────────────

  getProjects() {
    return _load().projects || [];
  },

  getProject(id) {
    return this.getProjects().find(p => p.id === id) || null;
  },

  createProject(name, client, industry) {
    const data = _load();
    const project = {
      id: 'proj_' + _uid(),
      name,
      client,
      industry,
      created_at: new Date().toISOString(),
      session_ids: [],
    };
    data.projects = data.projects || [];
    data.projects.push(project);
    _save(data);
    return project;
  },

  updateProject(id, updates) {
    const data = _load();
    const idx = (data.projects || []).findIndex(p => p.id === id);
    if (idx === -1) return null;
    Object.assign(data.projects[idx], updates);
    _save(data);
    return data.projects[idx];
  },

  deleteProject(id) {
    const data = _load();
    data.projects = (data.projects || []).filter(p => p.id !== id);
    _save(data);
  },

  addSessionToProject(projectId, sessionId) {
    const data = _load();
    const project = (data.projects || []).find(p => p.id === projectId);
    if (!project) return;
    if (!project.session_ids.includes(sessionId)) {
      project.session_ids.push(sessionId);
    }
    _save(data);
  },

  // ── Draft Answers (auto-save before API submission) ───────────────────

  saveDraftAnswers(sessionId, answers) {
    const data = _load();
    data.drafts = data.drafts || {};
    data.drafts[sessionId] = answers;
    _save(data);
  },

  getDraftAnswers(sessionId) {
    const data = _load();
    return (data.drafts || {})[sessionId] || {};
  },

  clearDraftAnswers(sessionId) {
    const data = _load();
    if (data.drafts) delete data.drafts[sessionId];
    _save(data);
  },

  // ── Session metadata cache (questionnaire schema, flow_type) ──────────

  cacheSessionMeta(sessionId, meta) {
    const data = _load();
    data.sessionMeta = data.sessionMeta || {};
    data.sessionMeta[sessionId] = meta;
    _save(data);
  },

  getSessionMeta(sessionId) {
    const data = _load();
    return (data.sessionMeta || {})[sessionId] || null;
  },
};

// ── Internal helpers ──────────────────────────────────────────────────────

function _load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function _save(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function _uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}
