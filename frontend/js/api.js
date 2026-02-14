/**
 * V2 API Client — all fetch calls to the phased generation backend.
 */
const API_BASE = 'http://localhost:8000/api/v2';

const api = {
  // ── Sessions ──────────────────────────────────────────────────────────

  async createSession(flowType) {
    return _post('/sessions', { flow_type: flowType });
  },

  async listSessions(status = null, limit = 50) {
    let url = `/sessions?limit=${limit}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    return _get(url);
  },

  async getSession(sessionId) {
    return _get(`/sessions/${sessionId}`);
  },

  // ── Questionnaire ─────────────────────────────────────────────────────

  async getQuestionnaire(sessionId) {
    return _get(`/sessions/${sessionId}/questionnaire`);
  },

  async submitQuestionnaire(sessionId, answers) {
    return _post(`/sessions/${sessionId}/questionnaire`, { answers });
  },

  // ── Documents ─────────────────────────────────────────────────────────

  async uploadDocuments(sessionId, files) {
    const form = new FormData();
    files.forEach(f => form.append('files', f));
    return _postMultipart(`/sessions/${sessionId}/upload`, form);
  },

  // ── Phases ────────────────────────────────────────────────────────────

  async startPhase(sessionId, phaseNumber) {
    return _post(`/sessions/${sessionId}/phases/${phaseNumber}/generate`);
  },

  async getPhaseStatus(sessionId, phaseNumber) {
    return _get(`/sessions/${sessionId}/phases/${phaseNumber}/status`);
  },

  async getPhaseReview(sessionId, phaseNumber) {
    return _get(`/sessions/${sessionId}/phases/${phaseNumber}/review`);
  },

  async approvePhase(sessionId, phaseNumber, { approved_by, notes = '', edited_artifacts = null }) {
    const body = { approved_by, notes };
    if (edited_artifacts) body.edited_artifacts = edited_artifacts;
    return _post(`/sessions/${sessionId}/phases/${phaseNumber}/approve`, body);
  },

  async rejectPhase(sessionId, phaseNumber, feedback) {
    return _post(`/sessions/${sessionId}/phases/${phaseNumber}/reject`, { feedback });
  },

  // ── Snapshots ─────────────────────────────────────────────────────────

  async getSnapshots(sessionId) {
    return _get(`/sessions/${sessionId}/snapshots`);
  },

  snapshotDownloadUrl(sessionId, phaseNumber) {
    return `${API_BASE}/sessions/${sessionId}/snapshots/${phaseNumber}/download`;
  },

  exportPackUrl(sessionId) {
    return `${API_BASE}/sessions/${sessionId}/export`;
  },

  // ── Health ────────────────────────────────────────────────────────────

  async health() {
    const res = await fetch('http://localhost:8000/');
    return res.json();
  },
};

// ── Internal helpers ──────────────────────────────────────────────────────

async function _get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function _post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function _postMultipart(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}
