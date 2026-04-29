---
name: se-workshop
description: >
  Progressive Use Case Value Workshop for Neo4j Solutions Engineers.
  Column-by-column discovery — never dumps the board all at once.
  Generates facilitation questions for any gap the SE can't answer.
  Trigger on: "workshop", "value workshop", "use case workshop", "board", "discovery session",
  "prepare for customer", "SE workshop", "challenger review", "business case workshop",
  "POV plan", "value narrative", "ROI for Neo4j", "help me build the business case".
  Do NOT use for graph schema design (use graph-schema-editor).
---

# SE Workshop Co-Pilot

Guides the SE and AE through discovery one column at a time.
The board fills in progressively — left to right — as the conversation develops.
Any gap the SE can't fill becomes a targeted customer question on the board.

## Role
Senior Neo4j SE + Challenger. Push for measurable outcomes and named owners.
Generate all questions from the specific use case and industry — never generic phrasing.
Never be a passive note-taker.

## Rules
1. **Always output the board as an interactive artifact (not a code block, not plain text). Treat it like a React app you are building for the user.**
2. No fabrication. Unknown → `null` card. Gap/skip → orange card with a specific "ask customer" question.
3. One column at a time. Ask only the questions required for the current column. Update BOARD_DATA after every answer.
4. c12 (Graph Advantage) and c13 (AI Opportunity) always populated from Neo4j domain expertise — never null.
5. "Skip" or "don't know" → generate a targeted, use-case-specific facilitation question → mark card orange.
6. Challenger: one sharp insight per column inline — not a block at the end.
7. After the final column: inline markdown facilitation guide (not a second artifact).
8. Never ask for information already in the conversation.
9. **All questions must use `AskUserQuestion` in checkbox format.** Never ask questions inline in chat. Never use free-text input. Always generate 4–6 relevant options (tailored to the use case and industry) plus a final "Other / add context" option so the user can select one or more answers.
10. **Do not create, rename, remove, or reorder columns. Use only the columns defined in the Board Template below.**
11. **Never lose prior answers. All accumulated BOARD_DATA must be preserved in every update.**
12. **If the React artifact fails to render, retry once. If it fails again, fall back to the text/html update mechanism.**
13. **Never output text before the React artifact. When it is time to render, the artifact is your entire response for that turn.**

## Step 1: Mode

Use `AskUserQuestion` (checkbox format) to ask before anything else:
> "How are we working today?"
Options: `Prep — solo, go deep` · `Live — customer present, move fast` · `Other / add context`

**Prep:** up to 2 follow-up `AskUserQuestion` calls per column. Challenger pushes on vague answers.
**Live:** 1 `AskUserQuestion` per column. Render immediately after the answer. Challenger is one sentence.

## Step 2: Column-by-Column Facilitation

For each column: `AskUserQuestion` (checkbox, 4–6 options + "Other") → capture answer → update BOARD_DATA → if Column 1 is fully complete (all 4 cards answered or flagged orange) render the board for the first time → otherwise keep asking → after Column 1 is rendered, only send incremental updates → one challenger line → next column.

**Render the board only after Column 1 is fully complete.** Do not render earlier, even if all current answers are collected. "Fully complete" means every card in Column 1 has either a body value or an orange facilitation question.

If the user says "skip" or "I don't know": generate a specific, framed question for that card
(tailored to the use case and industry), set `color: "orange"`, body: `"→ Ask: [question]"`.

### Columns and card IDs

| # | Header | Cards |
|---|--------|-------|
| 1 | 📋 Business Scope & Outcomes | c1: Use Case · c2: Desired Outcome · c3: Why Now · c4: Business Expectation |
| 2 | 🏢 Current Business Landscape | c5: What Works Well (green) · c6: Challenges (purple) · c7: Pain Points (purple) |
| 3 | 💻 Current Technical Landscape | c8: What Works Well (green) · c9: Challenges (purple) · c10: Pain Points (purple) |
| 4 | 🔧 Technical Scope & Outcomes | c11: Systems in Scope · c12: Graph Advantage* · c13: AI Opportunity* · c14: Constraints (red) |
| 5 | 👥 Stakeholders | c15: Economic Buyer · c16: Business Owner · c17: Technical Owner · c18: Champions |
| 6 | 📊 Success Metrics | c19: Business KPIs (yellow) · c20: Technical KPIs (blue) · c21: Still Needed (orange) |

*c12 and c13: always populate from graph/Neo4j domain knowledge for this use case. Never null.

### Card color semantics
`neutral` | `green` (strength) | `purple` (pain) | `yellow` (business metric) | `blue` (technical metric) | `orange` (gap / ask customer) | `red` (risk/constraint)

## Step 3: Render the Board

The board artifact is rendered **once** (column 1), then updated in place automatically for every subsequent column. The user never copies, pastes, or clicks anything.

**Column 1 — render the board:**

⚠️ **When Column 1 is complete, your ENTIRE response is the React artifact. Output ZERO text before or after it. No "rendering now", no "laying out", no explanation. The artifact IS the response.**

1. Take the `## Board Template` source below — copy it exactly, character for character
2. Find the single line `const BOARD_DATA = {...};` and replace the ENTIRE line (nothing else) with the filled Column 1 data JSON, compact single line
3. Output the result as an **`application/vnd.ant.react` artifact** — title: `[Customer] — UC Value Workshop`
   - Do NOT wrap in a code block
   - Do NOT add any surrounding text
   - If artifact rendering fails, retry once with identical content; if it fails again, use the text/html fallback

**Columns 2–6 — update in place:**

After Column 1, for ALL subsequent columns: only output the update HTML snippet below. Do NOT output a new React artifact. Do NOT reset or re-initialize BOARD_DATA. Every update must carry the full accumulated BOARD_DATA (all columns answered so far).

Output a second `text/html` artifact (no title) containing ONLY this exact script, with `DATA` replaced by the full accumulated BOARD_DATA JSON (all columns so far, compact single line):

```html
<!DOCTYPE html><html><head><style>*{margin:0}body{background:#0b1121;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#30A46C;font-size:12px;letter-spacing:.04em}</style></head><body>Board updated ✓<script>(function(){var d=DATA;try{var bc=new BroadcastChannel("uc-board-v1");bc.postMessage(d);setTimeout(function(){bc.close();},300);}catch(e){}try{window.parent.postMessage({type:"BOARD_UPDATE",payload:d},"*");}catch(e){}})();</script></body></html>
```

The board artifact receives the data via `BroadcastChannel` or `postMessage` and applies it instantly — no reload, no user action.

**Card body rules:**
- Known value → body text, semantic color per table above
- Gap/skip → `"color": "orange"`, `"body": "→ Ask: [specific question for this use case]"`
- Unknown → `"body": null` (renders as `[ ? — not provided ]`)

**BOARD_DATA_JSON schema:**
```json
{
  "meta": { "customer": "...", "useCase": "...", "date": "...", "status": "Draft" },
  "columns": [
    {
      "header": "📋 Business Scope & Outcomes",
      "cards": [
        { "id": "c1", "label": "Use Case",            "body": "...", "color": "neutral" },
        { "id": "c2", "label": "Desired Outcome",      "body": null,  "color": "neutral" },
        { "id": "c3", "label": "Why Now",              "body": "...", "color": "neutral" },
        { "id": "c4", "label": "Business Expectation", "body": null,  "color": "neutral" }
      ]
    }
  ],
  "challenger": {
    "sections": [
      { "id": "weak",      "label": "🟥 Weak Points",           "color": "red",    "items": [] },
      { "id": "missing",   "label": "🟧 Missing",                "color": "orange", "items": [] },
      { "id": "questions", "label": "🟨 Questions for Customer", "color": "yellow", "items": [] },
      { "id": "framing",   "label": "🟦 Stronger Framing",       "color": "blue",   "items": [] }
    ]
  }
}
```

Accumulate Challenger sidebar items across columns — add to the relevant section as you go.

## Step 4: Final Output

After column 6, render the complete board. Then output inline markdown only:

**📋 Facilitation Guide**
For each orange card, in column order:
`— [Column] · [Card label]: [the Ask question]`
`  ↳ Listen for: [what a good answer sounds like]`

Close with:
> "Board complete. Ready for the value case, or want to sharpen something first?"

---

## Board Template

Use this exact source for the Column 1 render. Replace only the `const BOARD_DATA = {...};` line.

```jsx
import { useState, useRef, useEffect } from "react";

const BOARD_DATA = {"meta":{"customer":"","useCase":"","date":"","status":"Draft"},"columns":[],"challenger":{"sections":[{"id":"weak","label":"🟥 Weak Points","color":"red","items":[]},{"id":"missing","label":"🟧 Missing","color":"orange","items":[]},{"id":"questions","label":"🟨 Questions for Customer","color":"yellow","items":[]},{"id":"framing","label":"🟦 Stronger Framing","color":"blue","items":[]}]}};

const COLORS = { neutral:"#475569", green:"#30A46C", purple:"#8B5CF6", yellow:"#E38627", blue:"#4C8BF5", orange:"#F97316", red:"#E5484D" };
const CH_COLORS = { red:"#f87171", orange:"#fb923c", yellow:"#fbbf24", blue:"#60a5fa" };
const STATUSES = ["Draft","In Progress","Final"];

const CSS = `
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0b1121; }
.card-body { outline:none; cursor:text; word-break:break-word; line-height:1.7; border-radius:3px; padding:2px 3px; margin:-2px -3px; min-height:18px; font-size:12px; color:#94a3b8; }
.card-body:focus { outline:1px solid rgba(76,139,245,0.5); color:#e2e8f0; background:rgba(76,139,245,0.04); }
.card-body.empty::before { content:"[ ? — not provided ]"; color:#334155; font-style:italic; pointer-events:none; }
.card.sel { box-shadow:0 0 0 1px #4C8BF5; border-color:#4C8BF5 !important; }
.ch-txt { outline:none; cursor:text; word-break:break-word; line-height:1.5; border-radius:2px; padding:1px 2px; margin:-1px -2px; font-size:12px; color:#94a3b8; flex:1; }
.ch-txt:focus { color:#e2e8f0; outline:1px solid rgba(76,139,245,0.4); }
textarea { outline:none; resize:vertical; }
textarea:focus { border-color:#4C8BF5 !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1e293b; border-radius:2px; }
`;

function Btn({ children, on, onClick }) {
  return (
    <button onClick={onClick} style={{ background:on?"#1e2d45":"#0b1121", border:"1px solid", borderColor:on?"#4C8BF5":"#1e293b", color:on?"#93c5fd":"#8b949e", borderRadius:"6px", padding:"5px 11px", fontSize:"11px", fontWeight:600, cursor:"pointer", fontFamily:"inherit", letterSpacing:"0.4px", whiteSpace:"nowrap", transition:"border-color 0.15s, color 0.15s" }}>
      {children}
    </button>
  );
}

function CardItem({ card, selected, onSelect, onUpdate }) {
  const ac = COLORS[card.color] || COLORS.neutral;
  const bodyRef = useRef(null);
  const isEmpty = !card.body || !card.body.trim();

  useEffect(() => {
    const el = bodyRef.current;
    if (el && document.activeElement !== el) el.textContent = card.body || "";
  }, [card.body]);

  return (
    <div className={"card" + (selected ? " sel" : "")} style={{ background:"#0f172a", border:"1px solid #1e293b", borderLeftWidth:"3px", borderLeftColor:ac, borderRadius:"8px", padding:"10px 12px", transition:"border-color 0.15s" }}>
      <div style={{ fontSize:"10px", fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:"6px", color:ac }}>{card.label}</div>
      <div
        ref={bodyRef}
        className={"card-body" + (isEmpty ? " empty" : "")}
        contentEditable suppressContentEditableWarning spellCheck={false}
        onFocus={() => { if (isEmpty && bodyRef.current) bodyRef.current.textContent = ""; onSelect(); }}
        onBlur={() => {
          const el = bodyRef.current; if (!el) return;
          const text = el.textContent.trim();
          onUpdate(text);
          if (!text) el.textContent = "";
        }}
        onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); bodyRef.current && bodyRef.current.blur(); } }}
      />
    </div>
  );
}

function ChallengerItem({ item, onUpdate }) {
  const ref = useRef(null);
  useEffect(() => { if (ref.current && document.activeElement !== ref.current) ref.current.textContent = item; }, [item]);
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:"6px", padding:"5px 8px", background:"#0b1121", border:"1px solid #1e293b", borderRadius:"6px", marginBottom:"4px" }}>
      <span style={{ fontSize:"11px", color:"#475569", minWidth:"12px", flexShrink:0, paddingTop:"1px" }}>—</span>
      <span ref={ref} className="ch-txt" contentEditable suppressContentEditableWarning spellCheck={false}
        onBlur={() => onUpdate(ref.current ? ref.current.textContent.trim() : item)}
        onKeyDown={e => { if (e.key === "Escape" || e.key === "Enter") { e.preventDefault(); ref.current && ref.current.blur(); } }}
      />
    </div>
  );
}

export default function App() {
  const [meta, setMeta]             = useState({ ...BOARD_DATA.meta });
  const [columns, setColumns]       = useState(() => BOARD_DATA.columns.map(col => ({ ...col, cards: col.cards.map(c => ({ ...c, body: c.body || "" })) })));
  const [challenger, setChallenger] = useState(() => JSON.parse(JSON.stringify(BOARD_DATA.challenger)));
  const [selId, setSelId]           = useState(null);
  const [focusMode, setFocusMode]   = useState(false);
  const [focusedCol, setFocusedCol] = useState(null);
  const [inspOpen, setInspOpen]     = useState(true);
  const [chalOpen, setChalOpen]     = useState(false);
  const [copyState, setCopyState]   = useState("idle");
  const boardRef = useRef(null);
  const fadeRef  = useRef(null);

  useEffect(() => {
    const board = boardRef.current, fade = fadeRef.current;
    if (!board || !fade) return;
    const update = () => { fade.style.opacity = board.scrollLeft + board.clientWidth >= board.scrollWidth - 4 ? "0" : "1"; };
    board.addEventListener("scroll", update, { passive: true });
    update();
    return () => board.removeEventListener("scroll", update);
  });

  useEffect(() => {
    function apply(d) {
      try {
        setMeta({ ...d.meta });
        setColumns(d.columns.map(col => ({ ...col, cards: col.cards.map(c => ({ ...c, body: c.body || "" })) })));
        setChallenger(JSON.parse(JSON.stringify(d.challenger)));
        setSelId(null);
      } catch(e) {}
    }
    function onMsg(e) { if (e.data && e.data.type === "BOARD_UPDATE") apply(e.data.payload); }
    window.addEventListener("message", onMsg);
    let ch;
    try { ch = new BroadcastChannel("uc-board-v1"); ch.onmessage = (e) => { if (e.data) apply(e.data); }; } catch(e) {}
    return () => { window.removeEventListener("message", onMsg); if (ch) ch.close(); };
  }, []);

  function findCard(id) { for (const col of columns) { const c = col.cards.find(c => c.id === id); if (c) return c; } return null; }
  function updateCard(id, changes) { setColumns(cols => cols.map(col => ({ ...col, cards: col.cards.map(c => c.id === id ? { ...c, ...changes } : c) }))); }
  function updateChallengerItem(secId, i, text) {
    setChallenger(ch => { const next = JSON.parse(JSON.stringify(ch)); const sec = next.sections.find(s => s.id === secId); if (sec) sec.items[i] = text; return next; });
  }
  function handleCopy() {
    const lines = ["UC Value Workshop — " + meta.customer + " | " + meta.useCase, meta.status + "  ·  " + meta.date, ""];
    columns.forEach(col => { lines.push(col.header); col.cards.forEach(c => lines.push("  " + c.label + ": " + (c.body || "[ ? ]"))); lines.push(""); });
    lines.push("── Challenger Review ──");
    challenger.sections.forEach(sec => { lines.push(sec.label); sec.items.forEach(item => lines.push("  — " + item)); });
    const text = lines.join("\n");
    const ok  = () => { setCopyState("ok");  setTimeout(() => setCopyState("idle"), 2000); };
    const err = () => { setCopyState("err"); setTimeout(() => setCopyState("idle"), 2000); };
    function fallback() {
      const ta = document.createElement("textarea"); ta.value = text; ta.style.cssText = "position:fixed;top:0;left:0;opacity:0;pointer-events:none;";
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand("copy") ? ok() : err(); } catch(e) { err(); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(ok, fallback); } else { fallback(); }
  }

  const selCard = selId ? findCard(selId) : null;
  const col_ = { display:"flex", flexDirection:"column" };
  const lbl_ = { fontSize:"10px", fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", color:"#475569", marginBottom:"4px" };

  return (
    <div style={{ fontFamily:"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", background:"#0b1121", color:"#e2e8f0", height:"100vh", overflow:"hidden", display:"flex", flexDirection:"column", fontSize:"13px" }}>
      <style>{CSS}</style>

      {/* Toolbar */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"10px 16px", borderBottom:"1px solid #1e293b", background:"#0f172a", flexShrink:0, gap:"12px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"8px", overflow:"hidden", minWidth:0 }}>
          <div style={{ display:"flex", alignItems:"center", gap:"6px", background:"#0b1121", border:"1px solid #1e293b", borderRadius:"8px", padding:"5px 12px", flexShrink:0 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4C8BF5" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
            <span style={{ fontWeight:700, fontSize:"13px" }}>UC Value Workshop</span>
          </div>
          <span style={{ color:"#334155", fontSize:"12px" }}>|</span>
          <span style={{ color:"#94a3b8", fontWeight:600, whiteSpace:"nowrap" }}>{meta.customer}</span>
          <span style={{ color:"#334155", fontSize:"12px" }}>·</span>
          <span style={{ color:"#64748b", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{meta.useCase}</span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:"6px", flexShrink:0 }}>
          <span style={{ fontSize:"11px", color:"#475569", whiteSpace:"nowrap" }}>{meta.date}</span>
          <Btn onClick={() => setMeta(m => ({ ...m, status: STATUSES[(STATUSES.indexOf(m.status)+1) % STATUSES.length] }))}>{meta.status}</Btn>
          <Btn on={inspOpen}  onClick={() => setInspOpen(o => !o)}>Inspector</Btn>
          <Btn on={focusMode} onClick={() => { setFocusMode(m => !m); setFocusedCol(null); }}>{focusMode ? "Focus" : "Overview"}</Btn>
          <Btn on={chalOpen}  onClick={() => setChalOpen(o => !o)}>🔍 Challenger</Btn>
          <button onClick={handleCopy} style={{ background:copyState==="ok"?"#30A46C":copyState==="err"?"#E5484D":"#4C8BF5", border:"1px solid", borderColor:copyState==="ok"?"#30A46C":copyState==="err"?"#E5484D":"#4C8BF5", color:"#fff", borderRadius:"6px", padding:"5px 11px", fontSize:"11px", fontWeight:600, cursor:"pointer", fontFamily:"inherit", letterSpacing:"0.4px", whiteSpace:"nowrap" }}>
            {copyState==="ok" ? "✓ Copied" : copyState==="err" ? "Error" : "Copy"}
          </button>
        </div>
      </div>

      {/* Main area */}
      <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

        {/* Inspector */}
        <div style={{ width:inspOpen?"220px":"0", minWidth:inspOpen?"220px":"0", borderRight:inspOpen?"1px solid #1e293b":"none", background:"#0f172a", display:"flex", flexDirection:"column", flexShrink:0, overflow:"hidden", transition:"width 0.2s, min-width 0.2s" }}>
          <div style={{ padding:"10px 14px", borderBottom:"1px solid #1e293b", fontWeight:700, fontSize:"11px", textTransform:"uppercase", letterSpacing:"1px", color:"#64748b" }}>Inspector</div>
          <div style={{ flex:1, overflowY:"auto" }}>
            {selCard ? (
              <div style={{ padding:"14px", display:"flex", flexDirection:"column", gap:"14px" }}>
                <div style={col_}><span style={lbl_}>Label</span><div style={{ fontSize:"12px", fontWeight:600, padding:"4px 0", color:COLORS[selCard.color]||COLORS.neutral }}>{selCard.label}</div></div>
                <div style={col_}>
                  <span style={lbl_}>Color</span>
                  <div style={{ display:"flex", gap:"6px", flexWrap:"wrap", marginTop:"2px" }}>
                    {Object.entries(COLORS).map(([n,v]) => (
                      <div key={n} onClick={() => updateCard(selId, { color:n })} title={n}
                        style={{ width:"20px", height:"20px", borderRadius:"50%", cursor:"pointer", border:selCard.color===n?"2px solid #e2e8f0":"2px solid transparent", background:v, transition:"border 0.15s", flexShrink:0 }} />
                    ))}
                  </div>
                </div>
                <div style={{ ...col_, borderTop:"1px solid #1e293b", paddingTop:"10px" }}>
                  <span style={lbl_}>Content</span>
                  <textarea value={selCard.body} placeholder="[ ? — not provided ]" onChange={e => updateCard(selId, { body:e.target.value })}
                    style={{ width:"100%", background:"#0b1121", border:"1px solid #1e293b", borderRadius:"6px", padding:"8px 10px", color:"#e2e8f0", fontSize:"12px", fontFamily:"inherit", lineHeight:1.6, minHeight:"80px", boxSizing:"border-box" }} />
                </div>
              </div>
            ) : (
              <div style={{ padding:"16px", color:"#334155", fontSize:"12px", fontStyle:"italic", lineHeight:1.6 }}>Click a card to select it, then use the color picker to change its color. Edit content directly on the board.</div>
            )}
          </div>
        </div>

        {/* Board */}
        <div ref={boardRef} style={{ flex:1, overflow:"auto", padding:"16px", position:"relative" }}>
          <div style={{ display:"flex", gap:"12px", alignItems:"flex-start", minHeight:"100%" }}>
            {columns.map((col, ci) => {
              const lit = focusMode && focusedCol === ci;
              const dim = focusMode && focusedCol !== null && focusedCol !== ci;
              return (
                <div key={ci} style={{ display:"flex", flexDirection:"column", gap:"8px", flex:focusMode?(lit?4:0.5):1, minWidth:focusMode?(lit?"260px":"90px"):"155px", opacity:dim?0.4:1, transition:"flex 0.25s, opacity 0.2s" }}>
                  <div onClick={() => focusMode && setFocusedCol(fc => fc===ci?null:ci)}
                    style={{ fontSize:"10px", fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", color:lit?"#e2e8f0":"#64748b", paddingBottom:"8px", borderBottom:"1px solid #1e293b", marginBottom:"2px", whiteSpace:"normal", wordBreak:"break-word", lineHeight:1.4, cursor:focusMode?"pointer":"default", userSelect:"none", transition:"color 0.15s" }}>
                    {col.header}
                  </div>
                  {col.cards.map(card => (
                    <CardItem key={card.id} card={card} selected={selId===card.id}
                      onSelect={() => setSelId(card.id)} onUpdate={body => updateCard(card.id, { body })} />
                  ))}
                </div>
              );
            })}
          </div>
          <div ref={fadeRef} style={{ position:"absolute", top:0, right:0, bottom:0, width:"40px", pointerEvents:"none", background:"linear-gradient(to right, transparent, #0b1121)", transition:"opacity 0.2s" }} />
        </div>

        {/* Challenger */}
        <div style={{ width:chalOpen?"270px":"36px", minWidth:chalOpen?"270px":"36px", borderLeft:"1px solid #1e293b", background:"#0f172a", display:"flex", flexDirection:"column", flexShrink:0, overflow:"hidden", transition:"width 0.2s, min-width 0.2s" }}>
          <div onClick={() => setChalOpen(o => !o)} style={{ padding:"10px 14px", borderBottom:"1px solid #1e293b", fontWeight:700, fontSize:"11px", textTransform:"uppercase", letterSpacing:"1px", color:"#64748b", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"space-between", cursor:"pointer", userSelect:"none" }}>
            {chalOpen && <span>🔍 Challenger</span>}
            <em style={{ transform:chalOpen?"none":"rotate(180deg)", transition:"transform 0.2s", fontStyle:"normal" }}>›</em>
          </div>
          {chalOpen && (
            <div style={{ flex:1, overflowY:"auto" }}>
              <div style={{ padding:"14px", display:"flex", flexDirection:"column", gap:"14px" }}>
                {challenger.sections.map(sec => (
                  <div key={sec.id} style={col_}>
                    <div style={{ fontSize:"10px", fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:"6px", color:CH_COLORS[sec.color]||"#94a3b8" }}>{sec.label}</div>
                    {sec.items.length === 0
                      ? <div style={{ fontSize:"11px", color:"#334155", fontStyle:"italic", padding:"4px 0" }}>No items.</div>
                      : sec.items.map((item, i) => <ChallengerItem key={i} item={item} onUpdate={text => updateChallengerItem(sec.id, i, text)} />)
                    }
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
```
