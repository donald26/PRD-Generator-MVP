/**
 * Phase Review — artifact tabs, side-by-side editor, approve/reject.
 */

let _reviewData = null;       // Cached review response
let _activeTab = null;        // Currently active artifact name
let _editedContent = {};      // Track edits: {artifactName: editedText}
let _originalContent = {};    // Original content for diff detection

// ── Screen renderer ─────────────────────────────────────────────────────

async function renderReviewScreen(params) {
  showScreen('review');
  const sessionId = params.session || AppState.currentSessionId;
  const phaseNumber = parseInt(params.phase || '1');
  AppState.currentSessionId = sessionId;

  const project = store.getProject(AppState.currentProjectId);
  const phaseDef = PHASES.find(p => p.number === phaseNumber);
  renderBreadcrumb([
    { label: 'Projects', hash: '#projects' },
    { label: project ? project.name : 'Project', hash: `#assessments?project=${AppState.currentProjectId}` },
    { label: 'Dashboard', hash: `#dashboard?session=${sessionId}` },
    { label: `Phase ${phaseNumber} Review` },
  ]);

  document.getElementById('review-title').textContent =
    `Phase ${phaseNumber}: ${phaseDef ? phaseDef.name : ''} — Review`;

  // Reset state
  _editedContent = {};
  _originalContent = {};
  _activeTab = null;

  const tabsEl = document.getElementById('review-tabs');
  const contentEl = document.getElementById('review-content');
  const actionsEl = document.getElementById('review-actions');

  tabsEl.innerHTML = '';
  contentEl.innerHTML = '<p class="text-sm text-gray-400">Loading...</p>';
  actionsEl.innerHTML = '';

  try {
    const data = await api.getPhaseReview(sessionId, phaseNumber);
    _reviewData = data;

    // Store originals
    for (const [name, content] of Object.entries(data.artifacts)) {
      _originalContent[name] = content;
    }

    // Render tabs
    const artifactNames = Object.keys(data.artifacts);
    const editable = new Set(data.editable || []);

    tabsEl.innerHTML = artifactNames.map(name => {
      const label = ARTIFACT_LABELS[name] || name;
      const editIcon = editable.has(name) ? ' <span class="text-xs">✏️</span>' : '';
      return `<button class="review-tab px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 border-transparent text-gray-500 hover:text-gray-700"
                data-artifact="${name}"
                onclick="switchReviewTab('${name}')">
        ${label}${editIcon}
      </button>`;
    }).join('');

    // Show first artifact
    if (artifactNames.length > 0) {
      switchReviewTab(artifactNames[0]);
    }

    // Render actions (only if phase is in review state)
    if (data.phase_status === 'review') {
      actionsEl.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Approved by</label>
            <input id="review-approved-by" type="text" placeholder="your.email@company.com"
                   class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
            <input id="review-notes" type="text" placeholder="Approval notes..."
                   class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          </div>
          <div class="flex gap-2">
            <button onclick="handleApprove('${sessionId}', ${phaseNumber})"
                    class="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700">
              Approve Phase
            </button>
            <button onclick="handleRejectModal('${sessionId}', ${phaseNumber})"
                    class="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 border border-red-200">
              Reject
            </button>
          </div>
        </div>
      `;
    } else {
      actionsEl.innerHTML = `<p class="text-sm text-green-600 font-medium">This phase has been approved.</p>`;
    }

  } catch (err) {
    contentEl.innerHTML = `<p class="text-red-500">Error loading review: ${esc(err.message)}</p>`;
  }
}

// ── Tab switching ───────────────────────────────────────────────────────

function switchReviewTab(artifactName) {
  _activeTab = artifactName;

  // Update tab styles
  document.querySelectorAll('.review-tab').forEach(tab => {
    const isActive = tab.dataset.artifact === artifactName;
    tab.classList.toggle('border-blue-500', isActive);
    tab.classList.toggle('text-blue-600', isActive);
    tab.classList.toggle('border-transparent', !isActive);
    tab.classList.toggle('text-gray-500', !isActive);
  });

  // Get content
  const content = _editedContent[artifactName] || _originalContent[artifactName] || '';
  const editable = (_reviewData && _reviewData.editable || []).includes(artifactName);

  const contentEl = document.getElementById('review-content');

  if (editable) {
    // Side-by-side: rendered + editor
    contentEl.innerHTML = `
      <div class="flex items-center gap-2 mb-2">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700">Editable</span>
        <span class="text-xs text-gray-400">Changes will be included when you approve</span>
      </div>
      <div class="grid grid-cols-2 gap-4" style="height: calc(100vh - 380px); min-height: 400px;">
        <div id="review-rendered" class="overflow-auto border border-gray-200 rounded-lg p-4 bg-white markdown-body">
          ${marked.parse(content)}
        </div>
        <div class="flex flex-col">
          <textarea id="review-editor"
                    class="flex-1 w-full px-3 py-3 text-sm font-mono border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    oninput="onReviewEdit('${artifactName}')">${escTextarea(content)}</textarea>
        </div>
      </div>
    `;
  } else {
    // Full-width rendered
    contentEl.innerHTML = `
      <div class="flex items-center gap-2 mb-2">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">Read-only</span>
      </div>
      <div class="overflow-auto border border-gray-200 rounded-lg p-4 bg-white markdown-body" style="height: calc(100vh - 380px); min-height: 400px;">
        ${marked.parse(content)}
      </div>
    `;
  }
}

// ── Editor live preview ─────────────────────────────────────────────────

function onReviewEdit(artifactName) {
  const editor = document.getElementById('review-editor');
  const rendered = document.getElementById('review-rendered');
  if (!editor || !rendered) return;

  _editedContent[artifactName] = editor.value;
  rendered.innerHTML = marked.parse(editor.value);
}

// ── Approve ─────────────────────────────────────────────────────────────

async function handleApprove(sessionId, phaseNumber) {
  const approvedBy = document.getElementById('review-approved-by').value.trim();
  if (!approvedBy) {
    showToast('Please enter who is approving.', 'error');
    return;
  }

  const notes = document.getElementById('review-notes').value.trim();

  // Collect edits (only artifacts that were actually changed)
  const editedArtifacts = {};
  let hasEdits = false;
  for (const [name, edited] of Object.entries(_editedContent)) {
    if (edited !== _originalContent[name]) {
      editedArtifacts[name] = edited;
      hasEdits = true;
    }
  }

  try {
    const result = await api.approvePhase(sessionId, phaseNumber, {
      approved_by: approvedBy,
      notes,
      edited_artifacts: hasEdits ? editedArtifacts : null,
    });

    showToast(`Phase ${phaseNumber} approved!`, 'success');

    if (result.next_phase) {
      showToast(`Phase ${result.next_phase} is now unlocked.`, 'info', 3000);
    }

    navigate(`#dashboard?session=${sessionId}`);
  } catch (err) {
    showToast('Approval failed: ' + err.message, 'error');
  }
}

// ── Reject ──────────────────────────────────────────────────────────────

function handleRejectModal(sessionId, phaseNumber) {
  showModal('Reject Phase ' + phaseNumber, `
    <p class="text-sm text-gray-600 mb-3">Provide feedback for regeneration:</p>
    <textarea id="reject-feedback" rows="4" placeholder="What should be changed..."
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"></textarea>
  `, {
    confirmLabel: 'Reject & Regenerate',
    onConfirm: () => handleReject(sessionId, phaseNumber),
  });
}

async function handleReject(sessionId, phaseNumber) {
  const feedback = document.getElementById('reject-feedback').value.trim();
  if (!feedback) {
    showToast('Please provide feedback.', 'error');
    return;
  }

  try {
    await api.rejectPhase(sessionId, phaseNumber, feedback);
    showToast(`Phase ${phaseNumber} rejected. You can regenerate.`, 'warning');
    navigate(`#dashboard?session=${sessionId}`);
  } catch (err) {
    showToast('Rejection failed: ' + err.message, 'error');
  }
}

// ── Utility ─────────────────────────────────────────────────────────────

function escTextarea(str) {
  return (str || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
