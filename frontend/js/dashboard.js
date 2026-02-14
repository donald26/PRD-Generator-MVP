/**
 * Phase Dashboard — 3-column card layout with status, progress, and actions.
 */

const PHASES = [
  {
    number: 1, name: 'Foundation',
    label: 'Context + PRD + Capabilities',
    artifacts: ['context_summary', 'corpus_summary', 'prd', 'capabilities'],
    requires: null,
  },
  {
    number: 2, name: 'Planning',
    label: 'Cards + Epics + Features + Roadmap',
    artifacts: ['capability_cards', 'epics', 'features', 'roadmap'],
    requires: 1,
  },
  {
    number: 3, name: 'Detail',
    label: 'Stories + Architecture + Canvas',
    artifacts: ['user_stories', 'technical_architecture', 'lean_canvas'],
    requires: 2,
  },
];

const ARTIFACT_LABELS = {
  context_summary: 'Context Summary',
  corpus_summary: 'Corpus Summary',
  prd: 'PRD',
  capabilities: 'Capabilities',
  capability_cards: 'Capability Cards',
  epics: 'Epics',
  features: 'Features',
  roadmap: 'Roadmap',
  user_stories: 'User Stories',
  technical_architecture: 'Architecture',
  lean_canvas: 'Lean Canvas',
};

// ── Screen renderer ─────────────────────────────────────────────────────

async function renderDashboardScreen(params) {
  showScreen('dashboard');
  const sessionId = params.session || AppState.currentSessionId;
  AppState.currentSessionId = sessionId;

  const project = store.getProject(AppState.currentProjectId);
  renderBreadcrumb([
    { label: 'Projects', hash: '#projects' },
    { label: project ? project.name : 'Project', hash: `#assessments?project=${AppState.currentProjectId}` },
    { label: 'Dashboard' },
  ]);

  const container = document.getElementById('phase-cards');
  container.innerHTML = '<p class="text-sm text-gray-400 col-span-3">Loading...</p>';

  try {
    const data = await api.getSession(sessionId);
    AppState.sessionData = data;

    const session = data.session;
    const gates = data.phase_gates || [];

    // Session info bar
    const meta = store.getSessionMeta(sessionId);
    const flowType = (meta && meta.flow_type) || (session && session.flow_type) || 'greenfield';
    document.getElementById('dashboard-session-info').innerHTML = `
      ${renderFlowBadge(flowType)}
      <span class="ml-2 font-mono">${sessionId.slice(0, 12)}...</span>
    `;

    // Build gate map
    const gateMap = {};
    gates.forEach(g => { gateMap[g.phase_number] = g; });

    // Render phase cards
    container.innerHTML = PHASES.map(phase => {
      const gate = gateMap[phase.number];
      const phaseStatus = computePhaseStatus(phase, gateMap);
      return renderPhaseCard(phase, gate, phaseStatus, sessionId);
    }).join('');

    // Show export button if all phases approved
    const exportEl = document.getElementById('dashboard-export');
    const allApproved = [1, 2, 3].every(pn => gateMap[pn] && gateMap[pn].status === 'approved');
    if (allApproved) {
      exportEl.innerHTML = `
        <div class="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-green-800">All phases approved</p>
            <p class="text-xs text-green-600">Download the consolidated Assessment Pack containing all artifacts.</p>
          </div>
          <a href="${api.exportPackUrl(sessionId)}"
             class="px-5 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700">
            Download Assessment Pack
          </a>
        </div>
      `;
    } else {
      exportEl.innerHTML = '';
    }

    // Start polling for any generating phases
    PHASES.forEach(phase => {
      const gate = gateMap[phase.number];
      if (gate && gate.status === 'generating') {
        startPhasePolling(sessionId, phase.number);
      }
    });

  } catch (err) {
    container.innerHTML = `<p class="text-red-500 col-span-3">Error loading session: ${esc(err.message)}</p>`;
  }
}

// ── Status computation ──────────────────────────────────────────────────

function computePhaseStatus(phase, gateMap) {
  const gate = gateMap[phase.number];

  // If gate exists, use its status
  if (gate) {
    if (gate.status === 'review') return 'draft';
    return gate.status; // generating, approved, rejected, failed
  }

  // No gate yet — check if prerequisites met
  if (phase.requires) {
    const priorGate = gateMap[phase.requires];
    if (!priorGate || priorGate.status !== 'approved') return 'locked';
  }

  return 'ready';
}

// ── Phase card rendering ────────────────────────────────────────────────

function renderPhaseCard(phase, gate, status, sessionId) {
  const isLocked = status === 'locked';
  const opacity = isLocked ? 'opacity-50' : '';

  const artifactList = phase.artifacts.map(a => {
    const label = ARTIFACT_LABELS[a] || a;
    let statusIcon = '';
    if (gate && status === 'generating') {
      // Will be updated by polling
      statusIcon = `<span id="artifact-status-${phase.number}-${a}" class="text-xs text-gray-400">pending</span>`;
    } else if (status === 'approved' || status === 'draft') {
      statusIcon = status === 'approved' ? '<span class="text-green-500 text-xs">done</span>' : '<span class="text-purple-500 text-xs">ready</span>';
    }
    return `<div class="flex items-center justify-between py-0.5">
      <span class="text-sm text-gray-700">${label}</span>
      ${statusIcon}
    </div>`;
  }).join('');

  let progressHtml = '';
  if (status === 'generating') {
    const pct = (gate && gate.overall_progress) || 0;
    progressHtml = `<div id="phase-progress-${phase.number}" class="mt-3">
      ${renderProgressBar(pct, 'Generating...')}
    </div>`;
  }

  let actionsHtml = '';
  switch (status) {
    case 'locked':
      actionsHtml = `<p class="text-xs text-gray-400 mt-3">Requires Phase ${phase.requires} approval</p>`;
      break;
    case 'ready':
      actionsHtml = `<button onclick="generatePhase('${sessionId}', ${phase.number})"
                       class="mt-3 w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
        Generate Phase ${phase.number}
      </button>`;
      break;
    case 'generating':
      actionsHtml = `<p class="text-xs text-amber-600 mt-3 flex items-center gap-1.5">
        <span class="spinner"></span> Generation in progress...
      </p>`;
      break;
    case 'draft':
      actionsHtml = `<button onclick="navigate('#review?session=${sessionId}&phase=${phase.number}')"
                       class="mt-3 w-full px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700">
        Review Artifacts
      </button>`;
      break;
    case 'approved':
      actionsHtml = `<div class="mt-3 flex gap-2">
        <button onclick="navigate('#review?session=${sessionId}&phase=${phase.number}')"
                class="flex-1 px-3 py-2 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
          View
        </button>
        <a href="${api.snapshotDownloadUrl(sessionId, phase.number)}"
           class="flex-1 px-3 py-2 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 text-center">
          Download
        </a>
      </div>`;
      if (gate && gate.approved_by) {
        actionsHtml += `<p class="text-xs text-gray-400 mt-1">Approved by ${esc(gate.approved_by)}</p>`;
      }
      break;
    case 'rejected':
      actionsHtml = `<div class="mt-3">
        <p class="text-xs text-red-600 mb-2">Feedback: ${esc((gate && gate.rejection_feedback) || 'No feedback')}</p>
        <button onclick="generatePhase('${sessionId}', ${phase.number})"
                class="w-full px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700">
          Regenerate
        </button>
      </div>`;
      break;
    case 'failed':
      actionsHtml = `<div class="mt-3">
        <p class="text-xs text-red-600 mb-2">Generation failed. Please try again.</p>
        <button onclick="generatePhase('${sessionId}', ${phase.number})"
                class="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
          Retry
        </button>
      </div>`;
      break;
  }

  return `
    <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-5 ${opacity}" id="phase-card-${phase.number}">
      <div class="flex items-center justify-between mb-3">
        <div>
          <span class="text-xs font-medium text-gray-400 uppercase">Phase ${phase.number}</span>
          <h3 class="font-semibold text-gray-900">${phase.name}</h3>
        </div>
        ${renderStatusBadge(status)}
      </div>
      <p class="text-xs text-gray-500 mb-3">${phase.label}</p>
      <div class="border-t border-gray-100 pt-3">
        ${artifactList}
      </div>
      ${progressHtml}
      ${actionsHtml}
    </div>
  `;
}

// ── Generate action ─────────────────────────────────────────────────────

async function generatePhase(sessionId, phaseNumber) {
  try {
    showToast(`Starting Phase ${phaseNumber} generation...`, 'info');
    await api.startPhase(sessionId, phaseNumber);
    startPhasePolling(sessionId, phaseNumber);
    // Re-render the dashboard to show generating state
    renderDashboardScreen({ session: sessionId });
  } catch (err) {
    showToast('Failed to start generation: ' + err.message, 'error');
  }
}

// ── Progress polling ────────────────────────────────────────────────────

function startPhasePolling(sessionId, phaseNumber) {
  const timerKey = `phase_${phaseNumber}`;

  async function poll() {
    try {
      const data = await api.getPhaseStatus(sessionId, phaseNumber);

      // Update progress bar
      const progressEl = document.getElementById(`phase-progress-${phaseNumber}`);
      if (progressEl) {
        progressEl.innerHTML = renderProgressBar(data.overall_progress || 0, 'Generating...');
      }

      // Update per-artifact status
      if (data.artifacts) {
        for (const [artType, artData] of Object.entries(data.artifacts)) {
          const statusEl = document.getElementById(`artifact-status-${phaseNumber}-${artType}`);
          if (statusEl) {
            const statusLabel = artData.status === 'completed' ? 'done' :
                               artData.status === 'cached' ? 'cached' :
                               artData.status === 'processing' ? 'generating...' : artData.status;
            const color = (artData.status === 'completed' || artData.status === 'cached') ? 'text-green-500' :
                          artData.status === 'processing' ? 'text-amber-500' : 'text-gray-400';
            statusEl.className = `text-xs ${color}`;
            statusEl.textContent = statusLabel;
          }
        }
      }

      // Check if done
      if (data.overall_status === 'review' || data.overall_status === 'approved') {
        clearTimeout(AppState.pollTimers[timerKey]);
        delete AppState.pollTimers[timerKey];
        showToast(`Phase ${phaseNumber} ready for review.`, 'success');
        renderDashboardScreen({ session: sessionId });
        return;
      }

      if (data.overall_status === 'failed') {
        clearTimeout(AppState.pollTimers[timerKey]);
        delete AppState.pollTimers[timerKey];
        showToast(`Phase ${phaseNumber} generation failed.`, 'error');
        renderDashboardScreen({ session: sessionId });
        return;
      }

      // Continue polling
      AppState.pollTimers[timerKey] = setTimeout(poll, 3000);
    } catch (err) {
      console.error('Poll error:', err);
      AppState.pollTimers[timerKey] = setTimeout(poll, 5000);
    }
  }

  // Start immediately
  poll();
}

// ── Navigation helper ───────────────────────────────────────────────────

function navigateBackToDashboard() {
  navigate(`#dashboard?session=${AppState.currentSessionId}`);
}
