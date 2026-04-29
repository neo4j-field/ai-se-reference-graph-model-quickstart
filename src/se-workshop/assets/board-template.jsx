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
