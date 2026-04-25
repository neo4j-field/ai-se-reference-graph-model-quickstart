<!DOCTYPE html>
<!--
  UC Value Workshop — Interactive Board Template
  ==============================================
  Claude generates this artifact by substituting {{BOARD_DATA_JSON}} with a JSON object.
  Click a card to open the Inspector (left sidebar). Click Challenger items to edit inline.

  BOARD_DATA_JSON schema:
  {
    "meta": { "customer": "...", "useCase": "...", "date": "25 Apr 2026", "status": "Draft" },
    "columns": [
      {
        "header": "📋 Business Scope & Outcomes",
        "cards": [
          { "id": "c1", "label": "Use Case", "body": "...", "color": "neutral" },
          { "id": "c2", "label": "Desired Outcome", "body": null, "color": "neutral" }
        ]
      }
    ],
    "challenger": {
      "sections": [
        { "id": "weak",      "label": "🟥 Weak Points",                   "color": "red",    "items": ["..."] },
        { "id": "missing",   "label": "🟧 Missing — I Need These",         "color": "orange", "items": ["..."] },
        { "id": "questions", "label": "🟨 Questions to Push the Customer", "color": "yellow", "items": ["..."] },
        { "id": "framing",   "label": "🟦 Stronger Framing",               "color": "blue",   "items": ["..."] }
      ]
    }
  }

  Color values for card "color" field: neutral | green | purple | yellow | blue | orange | red
-->
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UC Value Workshop Board</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0b1121;
  color: #e2e8f0;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  font-size: 13px;
}

/* ── Toolbar ──────────────────────────────────────────────────────────────── */
#toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #1e293b;
  background: #0f172a;
  flex-shrink: 0;
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-left  { display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; }
.toolbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.logo-badge {
  display: flex; align-items: center; gap: 6px;
  background: #0b1121; border: 1px solid #1e293b; border-radius: 8px;
  padding: 6px 14px; flex-shrink: 0;
}
.logo-badge span { font-weight: 700; font-size: 14px; color: #e2e8f0; }

.toolbar-sep      { color: #334155; }
.toolbar-customer { font-size: 13px; color: #94a3b8; font-weight: 600; white-space: nowrap; }
.toolbar-usecase  { font-size: 13px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.toolbar-date     { font-size: 11px; color: #475569; }

#status-badge {
  background: #0b1121; border: 1px solid #1e293b; color: #8b949e;
  border-radius: 20px; padding: 3px 12px; font-size: 11px; font-weight: 600;
  cursor: pointer; font-family: inherit; letter-spacing: 0.5px;
  transition: border-color 0.18s, color 0.18s;
}
#status-badge:hover { border-color: #4C8BF5; color: #e2e8f0; }

#copy-btn {
  background: #4C8BF5; border: none; color: #fff; border-radius: 6px;
  cursor: pointer; font-size: 12px; padding: 7px 14px; font-weight: 600;
  transition: background 0.2s; font-family: inherit; white-space: nowrap;
}
#copy-btn:hover  { background: #3b7de4; }
#copy-btn.copied { background: #30A46C; }

/* ── Main ─────────────────────────────────────────────────────────────────── */
#main { flex: 1; display: flex; overflow: hidden; }

/* ── Sidebars ─────────────────────────────────────────────────────────────── */
.sidebar { background: #0f172a; overflow-y: auto; display: flex; flex-direction: column; flex-shrink: 0; }
#inspector  { width: 240px; min-width: 240px; border-right: 1px solid #1e293b; }
#challenger { width: 280px; min-width: 280px; border-left:  1px solid #1e293b; }

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid #1e293b;
  font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
  color: #64748b; flex-shrink: 0;
  display: flex; align-items: center; justify-content: space-between;
}

.close-btn {
  background: none; border: none; color: #475569; cursor: pointer;
  font-size: 18px; line-height: 1; padding: 0 2px; font-family: inherit;
}
.close-btn:hover { color: #e2e8f0; }

.inspector-empty {
  padding: 20px; color: #334155; font-size: 12px; font-style: italic; line-height: 1.6;
}

.inspector-content, .challenger-content {
  padding: 16px; display: flex; flex-direction: column; gap: 16px;
}

.field-label {
  display: block; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em; color: #475569; margin-bottom: 4px;
}
.field-group { display: flex; flex-direction: column; }
.field-group-divider { border-top: 1px solid #1e293b; padding-top: 12px; margin-top: 4px; }

#inspector-label-value { font-size: 12px; font-weight: 600; padding: 4px 0; }

#inspector-textarea {
  width: 100%; background: #0b1121; border: 1px solid #1e293b; border-radius: 6px;
  padding: 8px 10px; color: #e2e8f0; font-size: 12px; font-family: inherit;
  outline: none; line-height: 1.6; resize: vertical; min-height: 90px;
}
#inspector-textarea:focus { border-color: #4C8BF5; }

.color-picker { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
.color-swatch {
  width: 22px; height: 22px; border-radius: 50%; cursor: pointer;
  border: 2px solid transparent; transition: border 0.15s;
}
.color-swatch.selected { border-color: #e2e8f0; }
.color-swatch:hover    { border-color: #64748b; }

#inspector-card-id { font-size: 11px; color: #334155; font-family: 'Courier New', monospace; }

/* ── Board ────────────────────────────────────────────────────────────────── */
#board { flex: 1; overflow: auto; padding: 16px; }
#board-grid { display: grid; gap: 12px; align-content: start; }

.column { display: flex; flex-direction: column; gap: 8px; }

.col-header {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: #64748b; padding-bottom: 8px; border-bottom: 1px solid #1e293b; margin-bottom: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.card {
  background: #0b1121;
  border: 1px solid #1e293b;
  border-left-width: 3px;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.card:hover    { border-color: #2d3748; }
.card.selected { border-color: #4C8BF5; box-shadow: 0 0 0 1px #4C8BF5; }

.card-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 5px;
}
.card-body { font-size: 12px; color: #94a3b8; line-height: 1.6; min-height: 18px; word-break: break-word; }
.card-body.empty { color: #334155; font-style: italic; }

/* ── Challenger ───────────────────────────────────────────────────────────── */
.ch-section { display: flex; flex-direction: column; }

.ch-section-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 8px;
}

.ch-item {
  display: flex; align-items: flex-start; gap: 6px;
  padding: 5px 8px; background: #0b1121; border: 1px solid #1e293b;
  border-radius: 6px; cursor: pointer; transition: border-color 0.15s; margin-bottom: 4px;
}
.ch-item:hover { border-color: #2d3748; }

.ch-bullet { font-size: 11px; color: #475569; min-width: 14px; flex-shrink: 0; padding-top: 1px; }
.ch-item-text { font-size: 12px; color: #94a3b8; flex: 1; line-height: 1.5; word-break: break-word; }

.ch-edit-input {
  background: none; border: none; border-bottom: 1px solid #4C8BF5;
  outline: none; color: #e2e8f0; font-size: 12px; font-family: inherit;
  flex: 1; line-height: 1.5; padding: 1px 0;
}

.ch-empty { font-size: 11px; color: #334155; font-style: italic; padding: 4px 0; }
</style>
</head>
<body>

<div id="toolbar">
  <div class="toolbar-left">
    <div class="logo-badge">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4C8BF5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
      <span>UC Value Workshop</span>
    </div>
    <span class="toolbar-sep">|</span>
    <span id="toolbar-customer" class="toolbar-customer"></span>
    <span class="toolbar-sep" style="font-size:12px">·</span>
    <span id="toolbar-usecase" class="toolbar-usecase"></span>
  </div>
  <div class="toolbar-right">
    <span id="toolbar-date" class="toolbar-date"></span>
    <button id="status-badge" title="Click to change status"></button>
    <button id="copy-btn">Copy summary</button>
  </div>
</div>

<div id="main">
  <div id="inspector" class="sidebar">
    <div class="sidebar-header">Inspector</div>
    <div class="inspector-empty">Click a card to inspect and edit.</div>
  </div>

  <div id="board">
    <div id="board-grid"></div>
  </div>

  <div id="challenger" class="sidebar">
    <div class="sidebar-header">🔍 Challenger Review</div>
    <div id="challenger-content" class="challenger-content"></div>
  </div>
</div>

<script>
const BOARD_DATA = {{BOARD_DATA_JSON}};

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
  meta: { ...BOARD_DATA.meta },
  columns: BOARD_DATA.columns.map(col => ({
    ...col,
    cards: col.cards.map(c => ({ ...c, body: c.body || '' })),
  })),
  challenger: JSON.parse(JSON.stringify(BOARD_DATA.challenger)),
  selectedCardId: null,
};

// ── Constants ──────────────────────────────────────────────────────────────────
const CARD_COLORS = {
  neutral: '#475569', green: '#30A46C', purple: '#8B5CF6',
  yellow:  '#E38627', blue:  '#4C8BF5', orange: '#F97316', red: '#E5484D',
};
const CH_COLORS = { red: '#f87171', orange: '#fb923c', yellow: '#fbbf24', blue: '#60a5fa' };
const STATUSES  = ['Draft', 'In Progress', 'Final'];

// ── Helpers ────────────────────────────────────────────────────────────────────
function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function findCard(id) {
  for (const col of state.columns) {
    const c = col.cards.find(c => c.id === id);
    if (c) return c;
  }
  return null;
}

// ── Board ──────────────────────────────────────────────────────────────────────
function buildBoard() {
  const grid = document.getElementById('board-grid');
  grid.style.gridTemplateColumns = `repeat(${state.columns.length}, minmax(160px, 1fr))`;
  grid.style.minWidth = `${state.columns.length * 172}px`;

  grid.innerHTML = state.columns.map(col => `
    <div class="column">
      <div class="col-header">${esc(col.header)}</div>
      ${col.cards.map(card => {
        const isEmpty = !card.body.trim();
        const accent  = CARD_COLORS[card.color] || CARD_COLORS.neutral;
        return `
          <div class="card" id="card-${esc(card.id)}" data-id="${esc(card.id)}"
               style="border-left-color: ${accent}">
            <div class="card-label" style="color: ${accent}">${esc(card.label)}</div>
            <div class="card-body${isEmpty ? ' empty' : ''}">${isEmpty ? '[ ? — not provided ]' : esc(card.body)}</div>
          </div>`;
      }).join('')}
    </div>`).join('');

  grid.querySelectorAll('.card').forEach(el => {
    el.addEventListener('click', e => {
      e.stopPropagation();
      const id   = el.dataset.id;
      const prev = state.selectedCardId;
      state.selectedCardId = prev === id ? null : id;
      if (prev) setCardSelected(prev, false);
      if (state.selectedCardId) setCardSelected(state.selectedCardId, true);
      renderInspector();
    });
  });

  // Click board background to deselect
  document.getElementById('board').addEventListener('click', () => {
    if (!state.selectedCardId) return;
    const prev = state.selectedCardId;
    state.selectedCardId = null;
    setCardSelected(prev, false);
    renderInspector();
  });
}

function setCardSelected(cardId, selected) {
  const el = document.getElementById(`card-${cardId}`);
  if (el) el.classList.toggle('selected', selected);
}

function updateCardDOM(cardId) {
  const card = findCard(cardId);
  if (!card) return;
  const el = document.getElementById(`card-${cardId}`);
  if (!el) return;

  const accent  = CARD_COLORS[card.color] || CARD_COLORS.neutral;
  const isEmpty = !card.body.trim();

  el.style.borderLeftColor = accent;
  el.querySelector('.card-label').style.color = accent;

  const bodyEl    = el.querySelector('.card-body');
  bodyEl.textContent = isEmpty ? '[ ? — not provided ]' : card.body;
  bodyEl.className   = `card-body${isEmpty ? ' empty' : ''}`;
}

// ── Inspector ──────────────────────────────────────────────────────────────────
function renderInspector() {
  const inspector = document.getElementById('inspector');
  const card      = state.selectedCardId ? findCard(state.selectedCardId) : null;

  if (!card) {
    inspector.innerHTML = `
      <div class="sidebar-header">Inspector</div>
      <div class="inspector-empty">Click a card to inspect and edit.</div>`;
    return;
  }

  const accent = CARD_COLORS[card.color] || CARD_COLORS.neutral;

  inspector.innerHTML = `
    <div class="sidebar-header">
      Inspector
      <button class="close-btn" id="inspector-close">×</button>
    </div>
    <div class="inspector-content">
      <div class="field-group">
        <span class="field-label">Label</span>
        <div id="inspector-label-value" style="color: ${accent}">${esc(card.label)}</div>
      </div>
      <div class="field-group">
        <span class="field-label">Content</span>
        <textarea id="inspector-textarea" placeholder="[ ? — not provided ]">${esc(card.body)}</textarea>
      </div>
      <div class="field-group">
        <span class="field-label">Color</span>
        <div class="color-picker">
          ${Object.entries(CARD_COLORS).map(([name, value]) => `
            <div class="color-swatch${card.color === name ? ' selected' : ''}"
                 data-color="${name}" style="background: ${value}" title="${name}"></div>
          `).join('')}
        </div>
      </div>
      <div class="field-group field-group-divider">
        <span class="field-label">Card ID</span>
        <span id="inspector-card-id">${esc(card.id)}</span>
      </div>
    </div>`;

  document.getElementById('inspector-close').addEventListener('click', () => {
    const prev = state.selectedCardId;
    state.selectedCardId = null;
    setCardSelected(prev, false);
    renderInspector();
  });

  const textarea = document.getElementById('inspector-textarea');
  textarea.focus();
  textarea.addEventListener('input', () => {
    const c = findCard(state.selectedCardId);
    if (c) { c.body = textarea.value; updateCardDOM(c.id); }
  });

  inspector.querySelectorAll('.color-swatch').forEach(el => {
    el.addEventListener('click', () => {
      const c = findCard(state.selectedCardId);
      if (!c) return;
      c.color = el.dataset.color;
      updateCardDOM(c.id);
      // Update inspector accent without full re-render (keeps textarea focus)
      const newAccent = CARD_COLORS[c.color] || CARD_COLORS.neutral;
      document.getElementById('inspector-label-value').style.color = newAccent;
      inspector.querySelectorAll('.color-swatch').forEach(sw => {
        sw.classList.toggle('selected', sw.dataset.color === c.color);
      });
    });
  });
}

// ── Challenger ─────────────────────────────────────────────────────────────────
function renderChallenger() {
  const content = document.getElementById('challenger-content');

  content.innerHTML = state.challenger.sections.map(sec => {
    const color = CH_COLORS[sec.color] || '#94a3b8';
    return `
      <div class="ch-section">
        <div class="ch-section-label" style="color: ${color}">${esc(sec.label)}</div>
        ${sec.items.length === 0
          ? '<div class="ch-empty">No items.</div>'
          : sec.items.map((item, i) => `
              <div class="ch-item" data-section="${esc(sec.id)}" data-index="${i}">
                <span class="ch-bullet">—</span>
                <span class="ch-item-text">${esc(item)}</span>
              </div>`).join('')}
      </div>`;
  }).join('');

  content.querySelectorAll('.ch-item').forEach(el => {
    el.addEventListener('click', () => {
      const textSpan = el.querySelector('.ch-item-text');
      if (!textSpan) return; // already editing

      const secId = el.dataset.section;
      const idx   = parseInt(el.dataset.index);
      const sec   = state.challenger.sections.find(s => s.id === secId);
      if (!sec) return;

      const input = document.createElement('input');
      input.type      = 'text';
      input.value     = sec.items[idx];
      input.className = 'ch-edit-input';
      textSpan.replaceWith(input);
      el.style.cursor = 'default';
      input.focus();

      const save = () => { sec.items[idx] = input.value; renderChallenger(); };
      input.addEventListener('blur', save);
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === 'Escape') input.blur();
        e.stopPropagation();
      });
      input.addEventListener('click', e => e.stopPropagation());
    });
  });
}

// ── Toolbar ────────────────────────────────────────────────────────────────────
function initToolbar() {
  document.getElementById('toolbar-customer').textContent = state.meta.customer || '';
  document.getElementById('toolbar-usecase').textContent  = state.meta.useCase  || '';
  document.getElementById('toolbar-date').textContent     = state.meta.date     || '';

  const badge = document.getElementById('status-badge');
  badge.textContent = state.meta.status;
  badge.addEventListener('click', () => {
    const idx = STATUSES.indexOf(state.meta.status);
    state.meta.status = STATUSES[(idx + 1) % STATUSES.length];
    badge.textContent = state.meta.status;
  });

  const copyBtn = document.getElementById('copy-btn');
  copyBtn.addEventListener('click', () => {
    const lines = [
      `UC Value Workshop — ${state.meta.customer} | ${state.meta.useCase}`,
      `Status: ${state.meta.status}  Date: ${state.meta.date}`,
      '',
    ];
    state.columns.forEach(col => {
      lines.push(col.header);
      col.cards.forEach(c => lines.push(`  ${c.label}: ${c.body || '[ ? ]'}`));
      lines.push('');
    });
    lines.push('Challenger Review');
    state.challenger.sections.forEach(sec => {
      lines.push(`  ${sec.label}`);
      sec.items.forEach(item => lines.push(`    — ${item}`));
    });

    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      copyBtn.textContent = '✓ Copied';
      copyBtn.classList.add('copied');
      setTimeout(() => { copyBtn.textContent = 'Copy summary'; copyBtn.classList.remove('copied'); }, 2000);
    }).catch(() => {
      copyBtn.textContent = 'Error';
      setTimeout(() => { copyBtn.textContent = 'Copy summary'; }, 2000);
    });
  });
}

// ── Init ───────────────────────────────────────────────────────────────────────
initToolbar();
buildBoard();
renderInspector();
renderChallenger();
</script>
</body>
</html>
