<!DOCTYPE html>
<!-- When rendering: replace the entire `const BOARD_DATA = {...};` line with the filled board data. -->
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UC Value Workshop Board</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0b1121; color: #e2e8f0;
  height: 100vh; overflow: hidden;
  display: flex; flex-direction: column; font-size: 13px;
}

/* ── Toolbar ── */
#toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid #1e293b;
  background: #0f172a; flex-shrink: 0; gap: 12px;
}
.tb-left  { display: flex; align-items: center; gap: 8px; overflow: hidden; min-width: 0; }
.tb-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.logo-badge {
  display: flex; align-items: center; gap: 6px;
  background: #0b1121; border: 1px solid #1e293b; border-radius: 8px;
  padding: 5px 12px; flex-shrink: 0;
}
.logo-badge span { font-weight: 700; font-size: 13px; }
.tb-sep      { color: #334155; font-size: 12px; }
.tb-customer { color: #94a3b8; font-weight: 600; white-space: nowrap; }
.tb-usecase  { color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-date     { font-size: 11px; color: #475569; white-space: nowrap; }

.btn {
  background: #0b1121; border: 1px solid #1e293b; color: #8b949e;
  border-radius: 6px; padding: 5px 11px; font-size: 11px; font-weight: 600;
  cursor: pointer; font-family: inherit; letter-spacing: 0.4px;
  transition: border-color 0.15s, color 0.15s; white-space: nowrap;
}
.btn:hover   { border-color: #4C8BF5; color: #e2e8f0; }
.btn.on      { background: #1e2d45; border-color: #4C8BF5; color: #93c5fd; }
#copy-btn    { background: #4C8BF5; border-color: #4C8BF5; color: #fff; }
#copy-btn:hover  { background: #3b7de4; border-color: #3b7de4; color: #fff; }
#copy-btn.ok     { background: #30A46C; border-color: #30A46C; }
#copy-btn.err    { background: #E5484D; border-color: #E5484D; }

/* ── Layout ── */
#main { flex: 1; display: flex; overflow: hidden; }

/* ── Inspector sidebar ── */
#inspector {
  width: 220px; min-width: 220px; border-right: 1px solid #1e293b;
  background: #0f172a; display: flex; flex-direction: column;
  flex-shrink: 0; overflow: hidden; transition: width 0.2s, min-width 0.2s;
}
#inspector.hidden { width: 0; min-width: 0; border-right: none; }

/* ── Challenger sidebar ── */
#challenger {
  width: 36px; min-width: 36px; border-left: 1px solid #1e293b;
  background: #0f172a; display: flex; flex-direction: column;
  flex-shrink: 0; overflow: hidden; transition: width 0.2s, min-width 0.2s;
}
#challenger.open { width: 270px; min-width: 270px; }

.sidebar-hdr {
  padding: 10px 14px; border-bottom: 1px solid #1e293b;
  font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
  color: #64748b; flex-shrink: 0;
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; user-select: none;
}
.sidebar-hdr:hover { color: #94a3b8; }

/* Challenger collapsed: show only arrow */
#challenger:not(.open) .ch-title { display: none; }
#challenger:not(.open) .ch-arrow { transform: rotate(180deg); writing-mode: vertical-rl; }
#challenger:not(.open) #challenger-body { display: none; }
.ch-arrow { transition: transform 0.2s; font-style: normal; }
#challenger.open .ch-arrow { transform: none; }

.sidebar-body { flex: 1; overflow-y: auto; }

.insp-empty { padding: 16px; color: #334155; font-size: 12px; font-style: italic; line-height: 1.6; }
.insp-content, .ch-content { padding: 14px; display: flex; flex-direction: column; gap: 14px; }

.field-lbl {
  display: block; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em; color: #475569; margin-bottom: 4px;
}
.field-group { display: flex; flex-direction: column; }
.field-div { border-top: 1px solid #1e293b; padding-top: 10px; margin-top: 2px; }

.insp-ta {
  width: 100%; background: #0b1121; border: 1px solid #1e293b; border-radius: 6px;
  padding: 8px 10px; color: #e2e8f0; font-size: 12px; font-family: inherit;
  outline: none; line-height: 1.6; resize: vertical; min-height: 80px;
}
.insp-ta:focus { border-color: #4C8BF5; }

.swatch-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
.swatch {
  width: 20px; height: 20px; border-radius: 50%; cursor: pointer;
  border: 2px solid transparent; transition: border 0.15s; flex-shrink: 0;
}
.swatch.on  { border-color: #e2e8f0; }
.swatch:hover { border-color: #64748b; }

/* ── Board ── */
#board { flex: 1; overflow: auto; padding: 16px; position: relative; }
#board-inner { display: flex; gap: 12px; align-items: flex-start; min-height: 100%; }
#board-fade {
  position: absolute; top: 0; right: 0; bottom: 0; width: 40px; pointer-events: none;
  background: linear-gradient(to right, transparent, #0b1121);
  transition: opacity 0.2s;
}

/* ── Column ── */
.col { display: flex; flex-direction: column; gap: 8px; flex: 1; min-width: 155px; transition: flex 0.25s, opacity 0.2s; }
#board-inner.focus .col { flex: 0.5; min-width: 90px; opacity: 0.4; }
#board-inner.focus .col.lit { flex: 4; min-width: 260px; opacity: 1; }

.col-hdr {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: #64748b; padding-bottom: 8px; border-bottom: 1px solid #1e293b; margin-bottom: 2px;
  white-space: normal; word-break: break-word; line-height: 1.4;
  cursor: pointer; user-select: none; transition: color 0.15s;
}
.col-hdr:hover { color: #94a3b8; }
.col.lit .col-hdr { color: #e2e8f0; font-size: 11px; }

/* ── Cards ── */
.card {
  background: #0f172a; border: 1px solid #1e293b; border-left-width: 3px;
  border-radius: 8px; padding: 10px 12px; transition: border-color 0.15s;
}
.card.sel { box-shadow: 0 0 0 1px #4C8BF5; border-color: #4C8BF5 !important; }

.card-lbl {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 6px;
}

.card-body {
  font-size: 12px; color: #94a3b8; line-height: 1.7;
  min-height: 18px; word-break: break-word;
  outline: none; border-radius: 3px;
  padding: 2px 3px; margin: -2px -3px;
  cursor: text;
}
.card-body.empty { color: #334155; font-style: italic; }
.card-body:focus { outline: 1px solid rgba(76,139,245,0.5); color: #e2e8f0; background: rgba(76,139,245,0.04); }

/* ── Challenger items ── */
.ch-sec { display: flex; flex-direction: column; }
.ch-sec-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.ch-item {
  display: flex; align-items: flex-start; gap: 6px;
  padding: 5px 8px; background: #0b1121; border: 1px solid #1e293b;
  border-radius: 6px; margin-bottom: 4px;
}
.ch-dot { font-size: 11px; color: #475569; min-width: 12px; flex-shrink: 0; padding-top: 1px; }
.ch-txt {
  font-size: 12px; color: #94a3b8; flex: 1; line-height: 1.5; word-break: break-word;
  outline: none; cursor: text; border-radius: 2px; padding: 1px 2px; margin: -1px -2px;
}
.ch-txt:focus { color: #e2e8f0; outline: 1px solid rgba(76,139,245,0.4); }
.ch-empty { font-size: 11px; color: #334155; font-style: italic; padding: 4px 0; }
</style>
</head>
<body>

<div id="toolbar">
  <div class="tb-left">
    <div class="logo-badge">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4C8BF5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
      <span>UC Value Workshop</span>
    </div>
    <span class="tb-sep">|</span>
    <span id="tb-customer" class="tb-customer"></span>
    <span class="tb-sep">·</span>
    <span id="tb-usecase" class="tb-usecase"></span>
  </div>
  <div class="tb-right">
    <span id="tb-date" class="tb-date"></span>
    <button id="status-btn" class="btn"></button>
    <button id="insp-btn"   class="btn on">Inspector</button>
    <button id="mode-btn"   class="btn">Overview</button>
    <button id="ch-tb-btn"  class="btn">🔍 Challenger</button>
    <button id="copy-btn"   class="btn">Copy</button>
  </div>
</div>

<div id="main">

  <!-- Inspector -->
  <div id="inspector">
    <div class="sidebar-hdr">Inspector</div>
    <div class="sidebar-body" id="insp-body">
      <div class="insp-empty">Click a card to select it, then use the color picker to change its color. Edit content directly on the board.</div>
    </div>
  </div>

  <!-- Board -->
  <div id="board">
    <div id="board-inner"></div>
    <div id="board-fade"></div>
  </div>

  <!-- Challenger (collapsed by default) -->
  <div id="challenger">
    <div class="sidebar-hdr" id="ch-hdr">
      <span class="ch-title">🔍 Challenger</span>
      <em class="ch-arrow">›</em>
    </div>
    <div class="sidebar-body" id="challenger-body">
      <div id="ch-content" class="ch-content"></div>
    </div>
  </div>

</div>

<script>
const BOARD_DATA = {"meta":{"customer":"","useCase":"","date":"","status":"Draft"},"columns":[],"challenger":{"sections":[{"id":"weak","label":"🟥 Weak Points","color":"red","items":[]},{"id":"missing","label":"🟧 Missing","color":"orange","items":[]},{"id":"questions","label":"🟨 Questions for Customer","color":"yellow","items":[]},{"id":"framing","label":"🟦 Stronger Framing","color":"blue","items":[]}]}}; /* REPLACE_THIS_LINE */

const S = {
  meta:      { ...BOARD_DATA.meta },
  columns:   BOARD_DATA.columns.map(col => ({ ...col, cards: col.cards.map(c => ({ ...c, body: c.body || '' })) })),
  challenger: JSON.parse(JSON.stringify(BOARD_DATA.challenger)),
  selId: null,
  focusMode: false,
  focusedCol: null,
};

const COLORS = { neutral:'#475569', green:'#30A46C', purple:'#8B5CF6', yellow:'#E38627', blue:'#4C8BF5', orange:'#F97316', red:'#E5484D' };
const CH_COLORS = { red:'#f87171', orange:'#fb923c', yellow:'#fbbf24', blue:'#60a5fa' };
const STATUSES = ['Draft','In Progress','Final'];

const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

function findCard(id) {
  for (const col of S.columns) { const c = col.cards.find(c=>c.id===id); if(c) return c; }
}

// ── Board ──────────────────────────────────────────────────────────────────────
function buildBoard() {
  const inner = document.getElementById('board-inner');
  inner.innerHTML = S.columns.map((col, ci) => `
    <div class="col" id="col-${ci}" data-ci="${ci}">
      <div class="col-hdr" data-ci="${ci}">${esc(col.header)}</div>
      ${col.cards.map(card => {
        const empty = !card.body.trim();
        const ac = COLORS[card.color] || COLORS.neutral;
        return `
          <div class="card" id="card-${esc(card.id)}" data-id="${esc(card.id)}" style="border-left-color:${ac}">
            <div class="card-lbl" style="color:${ac}">${esc(card.label)}</div>
            <div class="card-body${empty?' empty':''}"
                 contenteditable="true" spellcheck="false"
                 data-id="${esc(card.id)}"
            >${empty ? '[ ? — not provided ]' : esc(card.body)}</div>
          </div>`;
      }).join('')}
    </div>`).join('');

  // Column focus (in focus mode)
  inner.querySelectorAll('.col-hdr').forEach(el => {
    el.addEventListener('click', () => {
      if (!S.focusMode) return;
      const ci = +el.dataset.ci;
      S.focusedCol = S.focusedCol === ci ? null : ci;
      inner.querySelectorAll('.col').forEach((col, i) => col.classList.toggle('lit', i === S.focusedCol));
    });
  });

  // Inline editing
  inner.querySelectorAll('.card-body').forEach(el => {
    const id = el.dataset.id;

    el.addEventListener('focus', () => {
      if (el.classList.contains('empty')) { el.textContent = ''; el.classList.remove('empty'); }
      selectCard(id);
    });

    el.addEventListener('blur', () => {
      const card = findCard(id); if (!card) return;
      card.body = el.textContent.trim();
      if (!card.body) { el.textContent = '[ ? — not provided ]'; el.classList.add('empty'); }
      syncInspTa(card);
    });

    el.addEventListener('keydown', e => { if (e.key==='Escape') { e.preventDefault(); el.blur(); }});
  });
}

// ── Selection ─────────────────────────────────────────────────────────────────
function selectCard(id) {
  if (S.selId) { const p = document.getElementById(`card-${S.selId}`); if(p) p.classList.remove('sel'); }
  S.selId = id;
  const el = document.getElementById(`card-${id}`); if(el) el.classList.add('sel');
  renderInspector();
}

// ── Inspector ─────────────────────────────────────────────────────────────────
function renderInspector() {
  const body = document.getElementById('insp-body');
  const card = S.selId ? findCard(S.selId) : null;

  if (!card) {
    body.innerHTML = `<div class="insp-empty">Click a card to select it, then use the color picker to change its color. Edit content directly on the board.</div>`;
    return;
  }

  const ac = COLORS[card.color] || COLORS.neutral;
  body.innerHTML = `
    <div class="insp-content">
      <div class="field-group">
        <span class="field-lbl">Label</span>
        <div style="font-size:12px;font-weight:600;padding:4px 0;color:${ac}">${esc(card.label)}</div>
      </div>
      <div class="field-group">
        <span class="field-lbl">Color</span>
        <div class="swatch-row">
          ${Object.entries(COLORS).map(([n,v])=>`<div class="swatch${card.color===n?' on':''}" data-c="${n}" style="background:${v}" title="${n}"></div>`).join('')}
        </div>
      </div>
      <div class="field-group field-div">
        <span class="field-lbl">Content</span>
        <textarea class="insp-ta" id="insp-ta" placeholder="[ ? — not provided ]">${esc(card.body)}</textarea>
      </div>
    </div>`;

  document.getElementById('insp-ta').addEventListener('input', function() {
    card.body = this.value;
    const bodyEl = document.getElementById(`card-${card.id}`)?.querySelector('.card-body');
    if (bodyEl && document.activeElement !== bodyEl) {
      bodyEl.textContent = card.body || '[ ? — not provided ]';
      bodyEl.classList.toggle('empty', !card.body);
    }
    const lbl = document.getElementById(`card-${card.id}`);
    if (lbl) {
      const ac2 = COLORS[card.color]||COLORS.neutral;
      lbl.style.borderLeftColor = ac2;
    }
  });

  body.querySelectorAll('.swatch').forEach(sw => {
    sw.addEventListener('click', () => {
      card.color = sw.dataset.c;
      const el = document.getElementById(`card-${card.id}`);
      if (el) {
        const ac2 = COLORS[card.color]||COLORS.neutral;
        el.style.borderLeftColor = ac2;
        el.querySelector('.card-lbl').style.color = ac2;
      }
      renderInspector();
    });
  });
}

function syncInspTa(card) {
  const ta = document.getElementById('insp-ta');
  if (ta && S.selId === card.id) ta.value = card.body;
}

// ── Challenger ────────────────────────────────────────────────────────────────
function renderChallenger() {
  const content = document.getElementById('ch-content');
  content.innerHTML = S.challenger.sections.map(sec => {
    const color = CH_COLORS[sec.color] || '#94a3b8';
    return `
      <div class="ch-sec">
        <div class="ch-sec-lbl" style="color:${color}">${esc(sec.label)}</div>
        ${!sec.items.length
          ? '<div class="ch-empty">No items.</div>'
          : sec.items.map((item, i) => `
            <div class="ch-item" data-sec="${esc(sec.id)}" data-i="${i}">
              <span class="ch-dot">—</span>
              <span class="ch-txt" contenteditable="true" spellcheck="false">${esc(item)}</span>
            </div>`).join('')}
      </div>`;
  }).join('');

  content.querySelectorAll('.ch-txt').forEach(el => {
    const row = el.closest('.ch-item');
    const sec = S.challenger.sections.find(s=>s.id===row.dataset.sec);
    const idx = +row.dataset.i;
    el.addEventListener('blur', () => { if(sec) sec.items[idx] = el.textContent.trim(); });
    el.addEventListener('keydown', e => { if(e.key==='Escape'||e.key==='Enter'){e.preventDefault();el.blur();} });
  });
}

// ── Toolbar ───────────────────────────────────────────────────────────────────
function initToolbar() {
  document.getElementById('tb-customer').textContent = S.meta.customer || '';
  document.getElementById('tb-usecase').textContent  = S.meta.useCase  || '';
  document.getElementById('tb-date').textContent     = S.meta.date     || '';

  // Status
  const statusBtn = document.getElementById('status-btn');
  statusBtn.textContent = S.meta.status;
  statusBtn.addEventListener('click', () => {
    S.meta.status = STATUSES[(STATUSES.indexOf(S.meta.status)+1) % STATUSES.length];
    statusBtn.textContent = S.meta.status;
  });

  // Inspector toggle
  document.getElementById('insp-btn').addEventListener('click', function() {
    document.getElementById('inspector').classList.toggle('hidden');
    this.classList.toggle('on');
  });

  // Challenger toggle (toolbar button)
  document.getElementById('ch-tb-btn').addEventListener('click', function() {
    document.getElementById('challenger').classList.toggle('open');
    this.classList.toggle('on');
  });

  // Challenger toggle (sidebar header)
  document.getElementById('ch-hdr').addEventListener('click', () => {
    document.getElementById('challenger').classList.toggle('open');
    document.getElementById('ch-tb-btn').classList.toggle('on', document.getElementById('challenger').classList.contains('open'));
  });

  // Focus mode toggle
  const modeBtn = document.getElementById('mode-btn');
  modeBtn.addEventListener('click', () => {
    S.focusMode = !S.focusMode;
    S.focusedCol = null;
    modeBtn.textContent = S.focusMode ? 'Focus' : 'Overview';
    modeBtn.classList.toggle('on', S.focusMode);
    const inner = document.getElementById('board-inner');
    inner.classList.toggle('focus', S.focusMode);
    inner.querySelectorAll('.col').forEach(c => c.classList.remove('lit'));
  });

  // Copy with execCommand fallback
  const copyBtn = document.getElementById('copy-btn');
  copyBtn.addEventListener('click', () => {
    const lines = [
      `UC Value Workshop — ${S.meta.customer} | ${S.meta.useCase}`,
      `${S.meta.status}  ·  ${S.meta.date}`, '',
    ];
    S.columns.forEach(col => {
      lines.push(col.header);
      col.cards.forEach(c => lines.push(`  ${c.label}: ${c.body || '[ ? ]'}`));
      lines.push('');
    });
    lines.push('── Challenger Review ──');
    S.challenger.sections.forEach(sec => {
      lines.push(sec.label);
      sec.items.forEach(item => lines.push(`  — ${item}`));
    });
    const text = lines.join('\n');

    const ok  = () => { copyBtn.textContent='✓ Copied'; copyBtn.className='btn ok'; setTimeout(()=>{copyBtn.textContent='Copy';copyBtn.className='btn';},2000); };
    const err = () => { copyBtn.textContent='Error';    copyBtn.className='btn err'; setTimeout(()=>{copyBtn.textContent='Copy';copyBtn.className='btn';},2000); };

    function fallback() {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none;';
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand('copy') ? ok() : err(); } catch { err(); }
      document.body.removeChild(ta);
    }

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(ok, fallback);
    } else {
      fallback();
    }
  });
}

// ── Scroll fade ───────────────────────────────────────────────────────────────
function initScrollFade() {
  const board = document.getElementById('board');
  const fade  = document.getElementById('board-fade');
  function update() {
    const atEnd = board.scrollLeft + board.clientWidth >= board.scrollWidth - 4;
    fade.style.opacity = atEnd ? '0' : '1';
  }
  board.addEventListener('scroll', update, { passive: true });
  update();
}

// ── Init ──────────────────────────────────────────────────────────────────────
initToolbar();
buildBoard();
renderInspector();
renderChallenger();
initScrollFade();
</script>
</body>
</html>
