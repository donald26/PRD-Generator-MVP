/**
 * Questionnaire form — dynamic rendering, validation, auto-save, completion tracking.
 */

// ── Screen renderer (called from app.js router) ─────────────────────────

async function renderQuestionnaireScreen(params) {
  showScreen('questionnaire');
  const sessionId = params.session || AppState.currentSessionId;
  AppState.currentSessionId = sessionId;

  const project = store.getProject(AppState.currentProjectId);
  renderBreadcrumb([
    { label: 'Projects', hash: '#projects' },
    { label: project ? project.name : 'Project', hash: `#assessments?project=${AppState.currentProjectId}` },
    { label: 'Questionnaire' },
  ]);

  // Get questionnaire schema — from cache or API
  let meta = store.getSessionMeta(sessionId);
  let questions = meta ? meta.questionnaire : null;
  let flowType = meta ? meta.flow_type : null;

  // Also try to load API-saved answers
  let apiSavedAnswers = {};

  if (!questions) {
    try {
      const data = await api.getQuestionnaire(sessionId);
      questions = data.questions;
      flowType = data.flow_type;
      apiSavedAnswers = data.saved_answers || {};
      store.cacheSessionMeta(sessionId, {
        flow_type: flowType,
        questionnaire: questions,
      });
    } catch {
      // Fallback: get session detail
      try {
        const session = await api.getSession(sessionId);
        flowType = session.session ? session.session.flow_type : 'greenfield';
        showToast('Loading questionnaire...', 'info');
        const created = await api.createSession(flowType);
        questions = created.questionnaire;
        store.cacheSessionMeta(sessionId, {
          flow_type: flowType,
          questionnaire: questions,
        });
      } catch (err) {
        document.getElementById('questionnaire-sections').innerHTML =
          `<p class="text-red-500">Failed to load questionnaire: ${esc(err.message)}</p>`;
        return;
      }
    }
  }

  // Load draft answers — merge localStorage drafts over API-saved (drafts take priority)
  const draftAnswers = store.getDraftAnswers(sessionId);
  const savedAnswers = { ...apiSavedAnswers, ...draftAnswers };

  // Group questions by section
  const sections = groupBySection(questions);

  // Render header
  const flowLabel = flowType === 'modernization' ? 'Modernization' : 'Greenfield';
  document.getElementById('questionnaire-header').innerHTML = `
    <div class="flex items-center gap-2">
      <h2 class="text-lg font-semibold text-gray-900">${flowLabel} Intake</h2>
      ${renderFlowBadge(flowType)}
    </div>
    <p class="text-sm text-gray-500 mt-1">Answer the questions below to provide context for artifact generation.</p>
  `;

  // Render progress
  updateQuestionnaireProgress(questions, savedAnswers);

  // Render sections
  renderQuestionnaireSections(sections, savedAnswers, sessionId);

  // Render actions
  document.getElementById('questionnaire-actions').innerHTML = `
    <button id="q-save-draft" class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
      Save Draft
    </button>
    <button id="q-submit" class="px-5 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed">
      Submit &amp; Continue
    </button>
  `;

  document.getElementById('q-save-draft').onclick = () => {
    const answers = collectAnswers(questions);
    store.saveDraftAnswers(sessionId, answers);
    showToast('Draft saved.', 'success');
    updateQuestionnaireProgress(questions, answers);
  };

  document.getElementById('q-submit').onclick = () => submitQuestionnaire(sessionId, questions);
}

// ── Section grouping ────────────────────────────────────────────────────

function groupBySection(questions) {
  const map = new Map();
  questions.forEach(q => {
    const title = q.section_title || q.section || 'General';
    if (!map.has(title)) map.set(title, []);
    map.get(title).push(q);
  });
  return map;
}

// ── Section rendering ───────────────────────────────────────────────────

function renderQuestionnaireSections(sections, savedAnswers, sessionId) {
  const container = document.getElementById('questionnaire-sections');
  let html = '';
  let sectionIdx = 0;

  for (const [title, questions] of sections) {
    const sectionCompletion = getSectionCompletion(questions, savedAnswers);
    const isOpen = sectionIdx === 0; // First section open by default
    html += `
      <div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-3">
        <button class="w-full text-left px-5 py-4 flex items-center justify-between"
                onclick="toggleAccordion(this)">
          <div class="flex items-center gap-3">
            <span class="font-medium text-gray-900">${esc(title)}</span>
            <span class="text-xs px-2 py-0.5 rounded-full ${sectionCompletion.pct === 100 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}">
              ${sectionCompletion.answered}/${sectionCompletion.total} answered
            </span>
          </div>
          <svg class="w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>
        <div class="accordion-content ${isOpen ? 'open' : ''} px-5 pb-4">
          ${questions.map(q => renderQuestion(q, savedAnswers[q.id] || '', sessionId)).join('')}
        </div>
      </div>
    `;
    sectionIdx++;
  }

  container.innerHTML = html;
}

function renderQuestion(q, value, sessionId) {
  const required = q.required ? '<span class="text-red-500 ml-0.5">*</span>' : '';
  const inputId = `q-input-${q.id}`;

  let inputHtml = '';
  if (q.input_type === 'single_select') {
    const opts = (q.options || []).map(o =>
      `<option value="${esc(o)}" ${value === o ? 'selected' : ''}>${esc(o)}</option>`
    ).join('');
    inputHtml = `<select id="${inputId}" data-qid="${q.id}"
                   class="q-input w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                   onchange="onQuestionChange('${sessionId}')">
      <option value="">-- Select --</option>
      ${opts}
    </select>`;
  } else if (q.input_type === 'multiline_text') {
    inputHtml = `<textarea id="${inputId}" data-qid="${q.id}" rows="3"
                   class="q-input w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
                   placeholder="Enter your response..."
                   oninput="onQuestionChange('${sessionId}')">${esc(value)}</textarea>`;
  } else {
    inputHtml = `<input id="${inputId}" data-qid="${q.id}" type="text" value="${esc(value)}"
                   class="q-input w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                   placeholder="Enter your response..."
                   oninput="onQuestionChange('${sessionId}')">`;
  }

  return `
    <div class="mb-4">
      <label for="${inputId}" class="block text-sm font-medium text-gray-700 mb-1">
        ${esc(q.question_text)}${required}
      </label>
      ${inputHtml}
    </div>
  `;
}

// ── Auto-save (debounced) ───────────────────────────────────────────────

let _saveTimer = null;

function onQuestionChange(sessionId) {
  clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    const meta = store.getSessionMeta(sessionId);
    const questions = meta ? meta.questionnaire : [];
    const answers = collectAnswers(questions);
    store.saveDraftAnswers(sessionId, answers);
    updateQuestionnaireProgress(questions, answers);
  }, 500);
}

// ── Collect answers from DOM ────────────────────────────────────────────

function collectAnswers(questions) {
  const answers = {};
  questions.forEach(q => {
    const el = document.getElementById(`q-input-${q.id}`);
    if (el) answers[q.id] = el.value;
  });
  return answers;
}

// ── Completion tracking ─────────────────────────────────────────────────

function getCompletionStatus(questions, answers) {
  const required = questions.filter(q => q.required);
  const answered = required.filter(q => (answers[q.id] || '').trim().length > 0);
  const totalAll = questions.length;
  const answeredAll = questions.filter(q => (answers[q.id] || '').trim().length > 0).length;
  return {
    requiredTotal: required.length,
    requiredAnswered: answered.length,
    pct: required.length === 0 ? 100 : Math.round((answered.length / required.length) * 100),
    totalAll,
    answeredAll,
  };
}

function getSectionCompletion(questions, answers) {
  const total = questions.length;
  const answered = questions.filter(q => (answers[q.id] || '').trim().length > 0).length;
  return { total, answered, pct: total === 0 ? 100 : Math.round((answered / total) * 100) };
}

function updateQuestionnaireProgress(questions, answers) {
  const status = getCompletionStatus(questions, answers);
  document.getElementById('questionnaire-progress').innerHTML = `
    <div class="flex items-center justify-between text-sm mb-1">
      <span class="text-gray-600">${status.requiredAnswered} of ${status.requiredTotal} required questions answered</span>
      <span class="font-medium ${status.pct === 100 ? 'text-green-600' : 'text-gray-500'}">${status.pct}%</span>
    </div>
    ${renderProgressBar(status.pct)}
  `;
}

// ── Submission ──────────────────────────────────────────────────────────

async function submitQuestionnaire(sessionId, questions) {
  const answers = collectAnswers(questions);

  // Client-side validation
  const errors = validateQuestionnaire(questions, answers);
  if (errors.length > 0) {
    showToast(errors[0], 'error');
    return;
  }

  const btn = document.getElementById('q-submit');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    const result = await api.submitQuestionnaire(sessionId, answers);

    if (result.status === 'validation_error') {
      showToast(result.errors[0] || 'Validation error', 'error');
      btn.disabled = false;
      btn.innerHTML = 'Submit &amp; Continue';
      return;
    }

    store.clearDraftAnswers(sessionId);
    showToast('Questionnaire submitted.', 'success');
    navigate(`#upload?session=${sessionId}`);
  } catch (err) {
    showToast('Submission failed: ' + err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = 'Submit &amp; Continue';
  }
}

function validateQuestionnaire(questions, answers) {
  const errors = [];
  questions.forEach(q => {
    if (q.required && !(answers[q.id] || '').trim()) {
      errors.push(`"${q.question_text.slice(0, 60)}..." is required.`);
    }
  });
  return errors;
}

// ── Accordion toggle ────────────────────────────────────────────────────

function toggleAccordion(btn) {
  const content = btn.nextElementSibling;
  const arrow = btn.querySelector('svg');
  content.classList.toggle('open');
  arrow.classList.toggle('rotate-180');
}
