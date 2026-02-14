/**
 * Reusable UI component builders — badges, modals, toasts, breadcrumbs.
 */

// ── Industry options (for project creation) ─────────────────────────────

const INDUSTRIES = [
  'Financial Services', 'Healthcare', 'Technology', 'Retail & E-Commerce',
  'Manufacturing', 'Telecommunications', 'Energy & Utilities',
  'Education', 'Government', 'Media & Entertainment', 'Other',
];

// ── Status badge rendering ──────────────────────────────────────────────

const STATUS_CONFIG = {
  locked:     { label: 'Locked',     bg: 'bg-gray-100',   text: 'text-gray-500',   dot: 'bg-gray-400' },
  ready:      { label: 'Ready',      bg: 'bg-blue-50',    text: 'text-blue-700',   dot: 'bg-blue-500' },
  generating: { label: 'Generating', bg: 'bg-amber-50',   text: 'text-amber-700',  dot: 'bg-amber-500 animate-pulse' },
  draft:      { label: 'Draft',      bg: 'bg-purple-50',  text: 'text-purple-700', dot: 'bg-purple-500' },
  review:     { label: 'Draft',      bg: 'bg-purple-50',  text: 'text-purple-700', dot: 'bg-purple-500' },
  approved:   { label: 'Approved',   bg: 'bg-green-50',   text: 'text-green-700',  dot: 'bg-green-500' },
  rejected:   { label: 'Rejected',   bg: 'bg-red-50',     text: 'text-red-700',    dot: 'bg-red-500' },
  failed:     { label: 'Failed',     bg: 'bg-red-50',     text: 'text-red-700',    dot: 'bg-red-500' },
  // Session-level statuses
  intake:             { label: 'Intake',       bg: 'bg-gray-50',   text: 'text-gray-600',  dot: 'bg-gray-400' },
  questionnaire_done: { label: 'Questionnaire', bg: 'bg-blue-50',  text: 'text-blue-700',  dot: 'bg-blue-500' },
  docs_uploaded:      { label: 'Docs Uploaded', bg: 'bg-blue-50',  text: 'text-blue-700',  dot: 'bg-blue-500' },
  completed:          { label: 'Completed',    bg: 'bg-green-50',  text: 'text-green-700', dot: 'bg-green-500' },
};

function renderStatusBadge(status) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.locked;
  return `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}">
    <span class="w-1.5 h-1.5 rounded-full ${cfg.dot}"></span>
    ${cfg.label}
  </span>`;
}

// ── Flow type badge ─────────────────────────────────────────────────────

function renderFlowBadge(flowType) {
  if (flowType === 'modernization') {
    return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700">Modernization</span>`;
  }
  return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700">Greenfield</span>`;
}

// ── Breadcrumb ──────────────────────────────────────────────────────────

function renderBreadcrumb(items) {
  // items: [{label, hash}, ...] — last item has no hash (current page)
  const el = document.getElementById('breadcrumb');
  if (!el) return;
  el.innerHTML = items.map((item, i) => {
    const isLast = i === items.length - 1;
    if (isLast) {
      return `<span class="text-gray-900 font-medium">${item.label}</span>`;
    }
    return `<a href="${item.hash}" class="text-blue-600 hover:text-blue-800">${item.label}</a>
            <span class="text-gray-400 mx-1">/</span>`;
  }).join('');
}

// ── Progress bar ────────────────────────────────────────────────────────

function renderProgressBar(percent, label = '') {
  const clamp = Math.max(0, Math.min(100, percent));
  return `<div class="w-full">
    ${label ? `<div class="flex justify-between text-xs text-gray-500 mb-1"><span>${label}</span><span>${clamp}%</span></div>` : ''}
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: ${clamp}%"></div>
    </div>
  </div>`;
}

// ── Toast notifications ─────────────────────────────────────────────────

function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const colors = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  };

  const toast = document.createElement('div');
  toast.className = `border px-4 py-3 rounded-lg shadow-lg mb-2 transition-opacity duration-300 ${colors[type] || colors.info}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ── Modal dialog ────────────────────────────────────────────────────────

function showModal(title, bodyHtml, { confirmLabel = 'Confirm', cancelLabel = 'Cancel', onConfirm = null, onCancel = null } = {}) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');
  if (!overlay || !content) return;

  content.innerHTML = `
    <h3 class="text-lg font-semibold text-gray-900 mb-4">${title}</h3>
    <div class="mb-6">${bodyHtml}</div>
    <div class="flex justify-end gap-3">
      <button id="modal-cancel" class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
        ${cancelLabel}
      </button>
      <button id="modal-confirm" class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
        ${confirmLabel}
      </button>
    </div>
  `;

  overlay.classList.remove('hidden');

  document.getElementById('modal-cancel').onclick = () => {
    overlay.classList.add('hidden');
    if (onCancel) onCancel();
  };

  document.getElementById('modal-confirm').onclick = () => {
    overlay.classList.add('hidden');
    if (onConfirm) onConfirm();
  };

  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      overlay.classList.add('hidden');
      if (onCancel) onCancel();
    }
  };
}

function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ── Empty state placeholder ─────────────────────────────────────────────

function renderEmptyState(icon, title, subtitle = '') {
  return `<div class="text-center py-12">
    <div class="text-4xl mb-3">${icon}</div>
    <h3 class="text-lg font-medium text-gray-900 mb-1">${title}</h3>
    ${subtitle ? `<p class="text-sm text-gray-500">${subtitle}</p>` : ''}
  </div>`;
}

// ── Card wrapper ────────────────────────────────────────────────────────

function cardHtml(content, { clickable = false, selected = false, classes = '' } = {}) {
  const base = 'bg-white rounded-lg border shadow-sm p-5';
  const hover = clickable ? 'cursor-pointer hover:shadow-md hover:border-blue-300 transition-shadow' : '';
  const sel = selected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200';
  return `<div class="${base} ${hover} ${sel} ${classes}">${content}</div>`;
}

// ── Relative time formatting ────────────────────────────────────────────

function timeAgo(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
