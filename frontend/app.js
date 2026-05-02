'use strict';
/* ═══════════════════════════════════════════════════
   BrandScope v2 — Neon Green Terminal Frontend
   ═══════════════════════════════════════════════════ */

const API  = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';
const POLL = 1000;

let jobId         = null;
let pollTimer     = null;
let currentReport = null;
let currentRunId  = null;
let timerInterval = null;
let jobStart      = null;
let logCount      = 0;   // track how many log entries we've rendered

const PIPELINES = [
  { id:'p01', name:'Company Overview'     },
  { id:'p02', name:'Brand Identity'       },
  { id:'p03', name:'Market Position'      },
  { id:'p04', name:'Competitor Mapping'   },
  { id:'p05', name:'Brand Activity'       },
  { id:'p06', name:'Events Footprint'     },
  { id:'p07', name:'Reputation Research'  },
  { id:'p08', name:'Strategic Watchouts'  },
  { id:'p09', name:'Decision Makers'      },
  { id:'p10', name:'Contact Intelligence' },
  { id:'p11', name:'Outreach Sequences'   },
  { id:'p12', name:'Tracking Setup'       },
];

/* ── DOM helpers ── */
const $  = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function toast(msg, ms=3000){
  const el=$('toast'); el.textContent=msg; el.classList.remove('hidden');
  clearTimeout(el._t); el._t=setTimeout(()=>el.classList.add('hidden'),ms);
}

/* ── Navigation ── */
function showSection(name) {
  ['form','analysis','results','reports'].forEach(s => {
    const el = $(`sec-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  ['analyse','reports'].forEach(b => {
    const el = $(`nav-${b}`);
    if (el) el.classList.toggle('active', b === (name === 'form' ? 'analyse' : name));
  });
  if (name === 'reports') loadReports();
}
window.showSection = showSection;

/* ── Tab switching ── */
document.addEventListener('click', e => {
  if (!e.target.classList.contains('tab')) return;
  const id = e.target.dataset.tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  $(`panel-${id}`)?.classList.add('active');
});

/* ── Form submit ── */
$('inputForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = $('submitBtn');
  btn.disabled = true;
  btn.innerHTML = '⏳ Starting…';
  const payload = {
    company_name: $('company_name').value.trim(),
    company_url:  $('company_url').value.trim(),
    category:     $('category').value.trim(),
  };
  try {
    const res  = await fetch(`${API}/analyse`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    startAnalysis(data.job_id, payload.company_name);
  } catch(err) {
    toast(`⚠ ${err.message}`, 5000);
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-run-icon">▶</span> Run Full Analysis';
  }
});

/* ══════════════════════════════════════════════════
   ANALYSIS VIEW
══════════════════════════════════════════════════ */
function startAnalysis(jid, companyName) {
  jobId    = jid;
  jobStart = Date.now();
  logCount = 0;

  showSection('analysis');
  buildPipelineGrid();
  startElapsedTimer();

  // Clear terminal
  $('termLog').innerHTML = '';
  addTermLine('system','info', `▸ Initialising analysis for "${esc(companyName)}"…`);
  addTermLine('system','info', `▸ Job ID: ${jid}`);

  pollTimer = setInterval(doPoll, POLL);
}

function startElapsedTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const s = Math.floor((Date.now() - jobStart) / 1000);
    const m = Math.floor(s / 60); const ss = String(s % 60).padStart(2,'0');
    const el = $('tbTime') || $('elapsedTimer');
    if (el) el.textContent = `${m}:${ss}`;
  }, 500);
}

function buildPipelineGrid() {
  $('pipelineGrid').innerHTML = PIPELINES.map(p => `
    <div class="pipe-item" id="pipe-${p.id}">
      <div class="pipe-icon">○</div>
      <div>
        <div class="pipe-name">${p.name}</div>
        <div class="pipe-finding" id="pipe-${p.id}-finding">waiting...</div>
      </div>
    </div>`).join('');
}

async function doPoll() {
  try {
    const res  = await fetch(`${API}/status/${jobId}`);
    const data = await res.json();
    updateAnalysisView(data);

    if (data.status === 'complete' || data.status === 'failed') {
      clearInterval(pollTimer);
      clearInterval(timerInterval);
      pollTimer = null;

      if (data.status === 'complete') {
        addTermLine('system','complete', `✓ Analysis complete — ${data.elapsed?.toFixed(1) || '?'}s · 12/12 pipelines`);
        PIPELINES.forEach(p => setPipeState(p.id, 'done', ''));
        $('ppBar').style.width = '100%';
        $('ppPct').textContent = '100%';
        setTimeout(() => {
          if (data.run_id) loadReport(data.run_id);
        }, 700);
      } else {
        addTermLine('system','error', `✗ Analysis failed — ${data.error || 'unknown error'}`);
        toast('Analysis failed — check debug endpoint', 6000);
        const btn = $('submitBtn');
        if (btn) { btn.disabled=false; btn.innerHTML='<span class="btn-run-icon">▶</span> Run Full Analysis'; }
      }
    }
  } catch(err) { /* silent retry */ }
}

function updateAnalysisView(data) {
  const done    = data.pipelines_done    || [];
  const running = data.running_pipelines || [];
  const summaries = data.pipeline_summaries || {};
  const logEntries = data.pipeline_log || [];
  const pct = Math.min(95, Math.round((done.length / 12) * 100));

  $('ppBar').style.width = `${pct}%`;
  $('ppPct').textContent = `${pct}%`;
  $('ppStats').textContent = `${done.length}/12 done · ${running.length} running`;

  // Sync terminal from log entries (only new ones)
  if (logEntries.length > logCount) {
    logEntries.slice(logCount).forEach(entry => {
      const prefix = { start:'▸', done:'✓', error:'✗', info:'ℹ', complete:'★' }[entry.type] || '·';
      const label  = entry.pipeline !== 'system'
        ? `[${PIPELINES.find(p=>entry.pipeline?.startsWith(p.id)+'_' || entry.pipeline===p.id)?.name || entry.pipeline.slice(0,3).toUpperCase()}] `
        : '';
      addTermLine(entry.pipeline, entry.type, `${prefix} ${label}${entry.message}`);
    });
    logCount = logEntries.length;
  }

  // Update pipeline cards
  PIPELINES.forEach(p => {
    const fullKey = done.find(d => d.startsWith(p.id+'_') || d === p.id);
    const isRun   = running.some(r => r.startsWith(p.id+'_') || r === p.id);
    const sum     = summaries[fullKey] || {};

    if (fullKey && sum.status === 'error') {
      setPipeState(p.id, 'error', sum.finding || 'Error');
    } else if (fullKey) {
      const finding = sum.finding || '';
      // Strip the elapsed part for display clarity
      setPipeState(p.id, 'done', finding.replace(/\s*\[[\d.]+s\]$/, ''));
    } else if (isRun) {
      setPipeState(p.id, 'running', 'scanning...');
    }
  });
}

function setPipeState(shortId, state, finding) {
  const el   = $(`pipe-${shortId}`);
  const find = $(`pipe-${shortId}-finding`);
  if (!el) return;
  el.className = `pipe-item pipe-item--${state}`;
  const icons = { running:'⟳', done:'✓', error:'✗' };
  el.querySelector('.pipe-icon').textContent = icons[state] || '○';
  if (find && finding) find.textContent = finding;
}

function addTermLine(pipeline, type, msg) {
  const log = $('termLog');
  if (!log) return;
  const s   = Math.floor((Date.now() - (jobStart||Date.now())) / 1000);
  const ts  = `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;
  const div = document.createElement('div');
  div.className = `term-line type-${type}`;
  div.innerHTML = `<span class="term-ts">${ts}</span><span class="term-msg">${esc(msg)}</span>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

/* ══════════════════════════════════════════════════
   LOAD & RENDER REPORT
══════════════════════════════════════════════════ */
async function loadReport(runId) {
  try {
    const res  = await fetch(`${API}/report/${runId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentReport = data;
    currentRunId  = runId;
    renderReport(data);
    showSection('results');
    const btn = $('submitBtn');
    if (btn) { btn.disabled=false; btn.innerHTML='<span class="btn-run-icon">▶</span> Run Full Analysis'; }
  } catch(err) {
    toast(`Could not load report: ${err.message}`, 5000);
  }
}
window.loadReport = loadReport;

function renderReport(data) {
  const pipes = data.pipelines || {};
  const pout  = key => (pipes[key] || {}).output || {};

  const p01 = pout('p01_company_overview');
  const p02 = pout('p02_brand_identity');
  const p03 = pout('p03_market_position');
  const p04 = pout('p04_competitor_mapping');
  const p05 = pout('p05_brand_activity');
  const p06 = pout('p06_experiential_footprint');
  const p07 = pout('p07_reputation_research');
  const p08 = pout('p08_strategic_watchouts');
  const p09 = pout('p09_decision_makers');
  const p10 = pout('p10_contact_intelligence');
  const p11 = pout('p11_outreach');
  const p12 = pout('p12_tracking');

  // Header
  $('rhCompany').textContent = data.company_name || '—';
  const elapsed = data.total_elapsed ? `${data.total_elapsed.toFixed(1)}s` : '';
  $('rhMeta').textContent = `${data.run_id || ''} · ${data.category || ''} ${elapsed ? '· '+elapsed : ''}`;

  const icp = p01.icp_fit_score ?? 0;
  $('rhScore').textContent = icp || '—';
  $('rhScoreBar').style.width = `${icp}%`;
  $('rhScoreBar').style.background = icp >= 70 ? 'var(--green)' : icp >= 40 ? 'var(--amber)' : 'var(--red)';

  // Verdict banner
  const v  = p08.overall_verdict || '';
  const vb = $('verdictBanner');
  if (v) {
    vb.className = `verdict-banner show ${v}`;
    vb.textContent = `${v === 'GREEN' ? '▲' : v === 'AMBER' ? '⚠' : '✗'} Strategic Watchout: ${v} — ${p08.timing_recommendation || ''} · ${p08.verdict_reasoning || ''}`;
  }

  // Render all cards
  renderCompanyCard(p01);
  renderMarketCard(p03);
  renderReputationCard(p07);
  renderWatchoutsCard(p08);
  renderTimingCard(p08);
  renderColorsCard(p02);
  renderVoiceCard(p02);
  renderCompetitorsCard(p04);
  renderPositionCard(p03);
  renderActivityCard(p05);
  renderEventsCard(p06);
  renderPeopleCard(p09, p10);
  renderOutreachCard(p11);
  renderTrackingCard(p12);
}

/* ── HELPERS ── */
const frow = (k,v,cls='') => v!=null&&v!==''&&v!==undefined
  ? `<div class="frow"><span class="fkey">${esc(k)}</span><span class="fval ${cls}">${esc(v)}</span></div>` : '';

const badge = (txt, cls='') => txt ? `<span class="badge ${cls}">${esc(txt)}</span>` : '';

function verdictClass(v) {
  if (!v) return '';
  if (['HIGH','POSITIVE','STRONG','GOOD','GREEN'].includes(String(v).toUpperCase())) return 'g';
  if (['LOW','NEGATIVE','POOR','RED'].includes(String(v).toUpperCase())) return 'r';
  if (['MEDIUM','MIXED','NEUTRAL','AMBER','MODERATE'].includes(String(v).toUpperCase())) return 'a';
  return '';
}

/* ── CARD RENDERERS ── */
function renderCompanyCard(d) {
  $('card-company').innerHTML = `
    <div class="card-head"><span class="card-title">Company Overview</span>
      ${d.icp_fit_score ? `<span class="badge bg">ICP ${d.icp_fit_score}/100</span>` : ''}
    </div>
    <div class="card-body">
      ${frow('Business Model', d.business_model)}
      ${frow('Industry', d.industry_vertical)}
      ${frow('Founded', d.founding_year)}
      ${frow('Employees', d.employee_count || d.employee_count_range)}
      ${frow('Funding', d.funding_status || d.funding_stage)}
      ${frow('Revenue Range', d.revenue_range)}
      ${frow('HQ', d.hq_city ? `${d.hq_city}, ${d.geography||''}` : d.geography)}
      ${frow('Readiness', d.experiential_readiness, verdictClass(d.experiential_readiness))}
      ${frow('Recommended Service', d.recommended_service)}
      ${d.company_narrative ? `<div class="card-note">${esc(d.company_narrative)}</div>` : ''}
    </div>`;
}

function renderMarketCard(d) {
  $('card-market').innerHTML = `
    <div class="card-head"><span class="card-title">Market Snapshot</span></div>
    <div class="card-body">
      ${frow('Share of Voice', d.share_of_voice_level, verdictClass(d.share_of_voice_level))}
      ${frow('Sentiment', d.brand_sentiment, verdictClass(d.brand_sentiment))}
      ${frow('Perception Gap', d.perception_gap_score ? `${d.perception_gap_score}/5` : null)}
      ${frow('Sentiment Shift', d.recent_sentiment_shift)}
      ${d.pitch_implication ? `<div class="insight-blue insight" style="margin-top:12px">💡 ${esc(d.pitch_implication)}</div>` : ''}
    </div>`;
}

function renderReputationCard(d) {
  $('card-reputation').innerHTML = `
    <div class="card-head"><span class="card-title">Reputation</span>
      ${d.reputation_label ? `<span class="badge ${verdictClass(d.reputation_label)==='g'?'bg':verdictClass(d.reputation_label)==='r'?'br':'ba'}">${d.reputation_label}</span>` : ''}
    </div>
    <div class="card-body">
      ${frow('Score', d.overall_reputation_score ? `${d.overall_reputation_score}/100` : null)}
      ${frow('NPS Signal', d.nps_signal)}
      ${frow('Community', d.brand_community_strength)}
      ${frow('Reddit', d.reddit_sentiment)}
      ${(d.reddit_key_themes||[]).length ? `<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:4px">${d.reddit_key_themes.slice(0,5).map(t=>`<span class="badge">${esc(t)}</span>`).join('')}</div>` : ''}
      ${d.reputation_opportunity ? `<div class="insight" style="margin-top:12px">🎯 ${esc(d.reputation_opportunity)}</div>` : ''}
    </div>`;
}

function renderWatchoutsCard(d) {
  const v = d.overall_verdict||'';
  const cls = v==='GREEN'?'bg':v==='RED'?'br':'ba';
  $('card-watchouts').innerHTML = `
    <div class="card-head"><span class="card-title">Strategic Watchouts</span>
      ${v ? `<span class="badge ${cls}">${v}</span>` : ''}
    </div>
    <div class="card-body">
      ${frow('Timing', d.timing_recommendation)}
      ${frow('Tone Adjustment', d.pitch_tone_adjustment)}
      ${(d.financial_distress_signals||[]).length ? `<div class="insight-red insight" style="margin-top:10px">⚠ ${esc(d.financial_distress_signals[0])}</div>` : ''}
      ${(d.leadership_changes||[]).length ? `<div class="insight" style="margin-top:8px">🔄 ${esc(d.leadership_changes[0].change)} — ${esc(d.leadership_changes[0].implication||'')}</div>` : ''}
      ${d.verdict_reasoning ? `<div class="card-note">${esc(d.verdict_reasoning)}</div>` : ''}
    </div>`;
}

function renderTimingCard(d) {
  $('card-timing').innerHTML = `
    <div class="card-head"><span class="card-title">Pitch Timing Intelligence</span></div>
    <div class="card-body">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          ${frow('Verdict', d.overall_verdict)}
          ${frow('Recommendation', d.timing_recommendation)}
          ${frow('Tone', d.pitch_tone_adjustment)}
        </div>
        <div>
          ${(d.leadership_changes||[]).map(lc=>`
            <div style="padding:8px;background:var(--bg3);border-radius:4px;margin-bottom:6px;font-size:12px">
              <div style="color:var(--green2);font-family:var(--mono);font-size:10px">${esc(lc.role)} ${esc(lc.date||'')}</div>
              <div style="margin-top:4px">${esc(lc.change)}</div>
              <div style="color:var(--text3);font-size:11px;margin-top:3px">${esc(lc.implication||'')}</div>
            </div>`).join('')}
        </div>
      </div>
    </div>`;
}

function renderColorsCard(d) {
  const colors  = d.primary_colors || d.extracted_colors || [];
  const swatches = colors.slice(0,12).map(c=>`<div class="swatch" style="background:${esc(c)}" title="${esc(c)}"></div>`).join('');
  $('card-colors').innerHTML = `
    <div class="card-head"><span class="card-title">Brand Colours</span></div>
    <div class="card-body">
      ${swatches ? `<div class="swatch-row">${swatches}</div>` : '<span style="color:var(--text3)">No colours extracted</span>'}
      <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px">
        ${colors.slice(0,6).map(c=>`<span class="badge" style="font-family:var(--mono);font-size:9px">${esc(c)}</span>`).join('')}
      </div>
      ${frow('Brand Tone', d.brand_tone)}
      ${frow('Visual Style', d.visual_style)}
      ${frow('Brand Maturity', d.brand_maturity)}
      ${d.experiential_design_angle ? `<div class="insight" style="margin-top:12px">🎨 ${esc(d.experiential_design_angle)}</div>` : ''}
    </div>`;
}

function renderVoiceCard(d) {
  const kw = d.brand_voice_keywords || [];
  const fonts = d.primary_fonts || d.extracted_fonts || [];
  $('card-voice').innerHTML = `
    <div class="card-head"><span class="card-title">Brand Voice & Typography</span></div>
    <div class="card-body">
      ${frow('Primary Font', fonts[0]||null)}
      ${frow('Secondary Font', fonts[1]||null)}
      ${frow('Tagline', d.tagline)}
      ${frow('Logo Style', d.logo_style)}
      ${kw.length ? `<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:5px">${kw.map(k=>`<span class="badge bg">${esc(k)}</span>`).join('')}</div>` : ''}
      ${(d.missing_brand_elements||[]).length ? `<div class="insight-amber insight" style="margin-top:12px">📌 Missing: ${esc(d.missing_brand_elements.join(' · '))}</div>` : ''}
    </div>`;
}

function renderCompetitorsCard(d) {
  const comps = d.competitors || [];
  const rows  = comps.slice(0,5).map(c=>`
    <tr>
      <td>${esc(c.name||'—')}</td>
      <td>${esc(c.brand_positioning||'—')}</td>
      <td>${esc(c.events_activity||'—')}</td>
      <td style="color:var(--text3);font-size:11px">${esc(c.experiential_gap||'—')}</td>
      <td>${badge(c.threat_level_to_brand, c.threat_level_to_brand==='HIGH'?'br':c.threat_level_to_brand==='LOW'?'bg':'ba')}</td>
    </tr>`).join('');
  $('card-competitors').innerHTML = `
    <div class="card-head"><span class="card-title">Competitor Mapping</span>
      ${d.competitive_urgency==='YES' ? `<span class="badge br">⚡ Competitor active</span>` : ''}
    </div>
    <div class="card-body">
      ${rows ? `<div style="overflow-x:auto"><table class="comp-table">
        <thead><tr><th>Brand</th><th>Positioning</th><th>Events</th><th>Their Gap</th><th>Threat</th></tr></thead>
        <tbody>${rows}</tbody></table></div>` : '<span style="color:var(--text3)">No competitors identified</span>'}
      ${d.experiential_white_space ? `<div class="insight" style="margin-top:14px">🎯 White space: ${esc(d.experiential_white_space)}</div>` : ''}
    </div>`;
}

function renderPositionCard(d) {
  $('card-position').innerHTML = `
    <div class="card-head"><span class="card-title">Market Position</span></div>
    <div class="card-body">
      ${frow('Share of Voice', d.share_of_voice_level, verdictClass(d.share_of_voice_level))}
      ${frow('Sentiment', d.brand_sentiment, verdictClass(d.brand_sentiment))}
      ${frow('Category Leader Claim', d.category_leadership_claim ? 'Yes' : 'No')}
      ${frow('Claim Verified', d.leadership_claim_verified ? 'Yes' : 'No')}
      ${frow('Perception Gap', d.perception_gap_score ? `${d.perception_gap_score}/5` : null)}
      ${(d.sentiment_signals||[]).length ? `<div class="card-note">${d.sentiment_signals.slice(0,2).map(s=>`"${esc(s)}"`).join('<br>')}</div>` : ''}
      ${d.market_position_summary ? `<div class="card-note">${esc(d.market_position_summary)}</div>` : ''}
    </div>`;
}

function renderActivityCard(d) {
  const campaigns = d.recent_campaigns || [];
  $('card-activity').innerHTML = `
    <div class="card-head"><span class="card-title">Brand Activity</span>
      ${d.budget_signal ? `<span class="badge ${d.budget_signal==='HIGH'?'bg':d.budget_signal==='LOW'?'br':'ba'}">${d.budget_signal} budget</span>` : ''}
    </div>
    <div class="card-body">
      ${frow('Content Cadence', d.social_content_cadence)}
      ${frow('PR Activity', d.pr_activity_level)}
      ${frow('Seasonal Pattern', d.seasonal_pattern)}
      ${frow('Opportunity Window', d.upcoming_opportunity_window)}
      ${frow('Last Campaign', d.last_major_campaign)}
      ${campaigns.length ? `<div style="margin-top:12px;display:flex;flex-direction:column;gap:6px">
        ${campaigns.slice(0,3).map(c=>`<div style="padding:8px 10px;background:var(--bg3);border-radius:4px;font-size:12px">
          <span style="color:var(--green2);font-weight:600">${esc(c.name||'?')}</span>
          <span style="color:var(--text3);margin:0 6px">·</span>
          <span class="badge">${esc(c.channel||'?')}</span>
          <span style="color:var(--text3);margin-left:6px;font-size:11px">${esc(c.date||'')}</span>
          ${c.description ? `<div style="color:var(--text2);margin-top:4px;font-size:11px">${esc(c.description)}</div>` : ''}
        </div>`).join('')}
      </div>` : ''}
      ${d.activity_summary ? `<div class="card-note">${esc(d.activity_summary)}</div>` : ''}
    </div>`;
}

function renderEventsCard(d) {
  const events = d.events_timeline || [];
  const score  = d.experiential_maturity_score;
  const pct    = score ? (score/5)*100 : 0;

  const eventCards = events.slice(0,8).map(ev=>`
    <div class="event-card">
      <div class="event-head">
        <span class="event-name">${esc(ev.event_name||ev.name||'Untitled')}</span>
        <span class="event-date">${esc(ev.date||ev.year||'')}</span>
      </div>
      <div class="event-badges">
        ${badge(ev.format,'bb')}
        ${badge(ev.scale)}
        ${ev.location?badge('📍 '+ev.location):''}
        ${badge(ev.brand_role,'bg')}
        ${badge(ev.production_quality,'ba')}
      </div>
      ${ev.source&&ev.source!=='inferred from brand scale / training knowledge'?`<div style="margin-top:6px;font-size:11px;color:var(--text3)">Source: ${esc(ev.source.slice(0,100))}</div>`:''}
    </div>`).join('');

  $('card-events').innerHTML = `
    <div class="card-head">
      <span class="card-title">Experiential Footprint</span>
      ${score ? `<span style="font-family:var(--mono);font-size:22px;font-weight:700;color:var(--green);text-shadow:var(--glow-sm)">${score}<span style="font-size:12px;color:var(--text3)">/5</span></span>` : ''}
    </div>
    <div class="card-body">
      <div style="margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--text3);margin-bottom:4px">
          <span>MATURITY SCORE</span><span>${score||'?'}/5</span>
        </div>
        <div class="score-bar-wrap" style="height:6px"><div class="score-bar" style="width:${pct}%"></div></div>
        <div style="font-size:11px;color:var(--text3);margin-top:4px">${esc(d.maturity_score_reasoning||'')}</div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px">
        ${frow('Frequency', d.events_frequency)}
        ${frow('Last Event', d.last_event_months_ago!=null ? `${d.last_event_months_ago} months ago` : null)}
        ${(d.geography_of_events||[]).length ? `<div class="frow" style="width:100%"><span class="fkey">Geography</span><span class="fval">${esc(d.geography_of_events.join(' · '))}</span></div>` : ''}
      </div>
      ${events.length ? eventCards : '<div style="color:var(--text3);padding:20px 0;text-align:center;font-family:var(--mono);font-size:12px">No confirmed events in search data — using model knowledge</div>'}
      ${(d.formats_used||[]).length ? `<div style="margin-top:12px"><div style="font-family:var(--mono);font-size:9px;color:var(--text3);letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Formats Used</div><div style="display:flex;flex-wrap:wrap;gap:4px">${d.formats_used.map(f=>badge(f,'bg')).join('')}</div></div>` : ''}
      ${(d.formats_missing||[]).length ? `<div class="insight-amber insight" style="margin-top:12px">📌 Missing formats: ${esc(d.formats_missing.join(' · '))}</div>` : ''}
      ${d.pitch_angle ? `<div class="insight" style="margin-top:10px">🎯 ${esc(d.pitch_angle)}</div>` : ''}
      ${d.opening_line_for_pitch ? `<div style="margin-top:10px;padding:12px 14px;background:rgba(0,255,65,.05);border:1px solid var(--gborder);border-radius:6px;font-size:12px;font-style:italic;color:var(--text2)">"${esc(d.opening_line_for_pitch)}"</div>` : ''}
    </div>`;
}

function renderPeopleCard(p09, p10) {
  const people   = p09.buying_committee || [];
  const contacts = p10.contacts || [];
  const cmap     = {};
  contacts.forEach(c => { if(c.name) cmap[c.name] = c; });

  const cards = people.map(p => {
    const ct    = cmap[p.name] || {};
    const email = ct.email || '—';
    const conf  = ct.email_confidence ? `${ct.email_confidence}%` : '';
    const score = p.decision_relevance_score || 0;
    return `
    <div class="person-card">
      <div class="person-name">${esc(p.name||'—')}</div>
      <div class="person-title">${esc(p.title||'—')} ${p.role_type?`<span class="badge" style="margin-left:4px">${esc(p.role_type)}</span>`:''}</div>
      <div class="person-score"><div class="person-score-fill" style="width:${score*20}%"></div></div>
      <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-bottom:8px">Decision relevance ${score}/5</div>
      <div class="person-meta">
        ${p.outreach_priority==='PRIMARY'?badge('PRIMARY','bg'):p.outreach_priority==='SECONDARY'?badge('SECONDARY','ba'):''}
        ${p.linkedin_activity?badge('LinkedIn: '+p.linkedin_activity):''}
        ${email!=='—'?badge('✉ '+email+(conf?' ('+conf+')':''),'bb'):''}
        ${ct.recommended_channel?badge(ct.recommended_channel):''}
      </div>
      ${p.personalisation_hook?`<div class="person-hook">💡 ${esc(p.personalisation_hook)}</div>`:''}
    </div>`;
  }).join('');

  $('card-people').innerHTML = `
    <div class="card-head"><span class="card-title">Decision Makers & Contact Intelligence</span>
      ${p09.primary_contact?`<span class="badge bg">Primary: ${esc(p09.primary_contact)}</span>`:''}
    </div>
    <div class="card-body">
      ${cards || '<div style="color:var(--text3);padding:16px 0;font-family:var(--mono);font-size:12px">No decision makers found — try broader Google searches</div>'}
      ${p10.email_pattern?`<div style="margin-top:14px;padding:10px 14px;background:var(--bg3);border-radius:6px;font-family:var(--mono);font-size:11px;color:var(--text3)">Email pattern: <span style="color:var(--green2)">${esc(p10.email_pattern)}@${esc(p10.domain||'?')}</span> · ${p10.verified_emails||0} verified · ${p10.inferred_emails||0} inferred</div>`:''}
      ${p10.data_disclaimer?`<div style="margin-top:8px;font-size:11px;color:var(--text3)">⚠ ${esc(p10.data_disclaimer)}</div>`:''}
    </div>`;
}

function renderOutreachCard(d) {
  const seq     = d.outreach_sequence || {};
  const primary = d.primary_contact || {};
  const touches = Object.entries(seq);

  if (!touches.length) {
    $('card-outreach').innerHTML = `<div class="card-head"><span class="card-title">Outreach Sequence</span></div><div class="card-body"><div style="color:var(--text3)">No sequence generated</div></div>`;
    return;
  }

  const compUsed = (d.competitor_intel_used||[]).filter(c=>c.name).map(c=>c.name);
  const vars     = d.personalisation_variables_used || {};

  const touchHtml = touches.map(([key, t]) => {
    const isLI = (t.channel||'').toLowerCase() === 'linkedin';
    return `
    <div class="touch-card ${isLI?'ch-linkedin':''}">
      <div class="touch-head">
        <span class="touch-ch">${esc(t.channel||key)}</span>
        <span class="touch-day">Day ${t.send_day||'—'}</span>
      </div>
      ${t.subject_line?`<div class="touch-subj">📧 ${esc(t.subject_line)}</div>`:''}
      <div class="touch-body">${esc(t.message||'—')}</div>
    </div>`;
  }).join('');

  $('card-outreach').innerHTML = `
    <div class="card-head">
      <span class="card-title">Personalised 4-Touch Outreach</span>
      ${primary.name?`<span class="badge bp">→ ${esc(primary.name)}</span>`:''}
    </div>
    <div class="card-body">
      ${primary.name||primary.email||primary.linkedin ? `
      <div style="padding:10px 14px;background:var(--bg3);border-radius:6px;margin-bottom:16px;font-size:12px;display:flex;flex-wrap:wrap;gap:12px">
        ${primary.name?`<span style="font-weight:600">${esc(primary.name)}</span>`:''}
        ${primary.title?`<span style="color:var(--text3)">${esc(primary.title)}</span>`:''}
        ${primary.email?badge('✉ '+primary.email,'bb'):''}
        ${primary.linkedin?`<a href="${esc(primary.linkedin)}" target="_blank" class="badge bb" style="text-decoration:none">LinkedIn ↗</a>`:''}
      </div>` : ''}
      ${compUsed.length?`<div style="margin-bottom:14px;font-family:var(--mono);font-size:11px;color:var(--text3)">Competitors referenced: ${compUsed.map(c=>`<span class="badge ba" style="margin-right:3px">${esc(c)}</span>`).join('')}</div>`:''}
      ${touchHtml}
      ${vars.signal||vars.gap ? `<div style="margin-top:14px;padding:10px 14px;background:var(--bg3);border-radius:6px;font-family:var(--mono);font-size:10px;color:var(--text3)">
        ${vars.signal?`<div>Signal used: <span style="color:var(--text2)">${esc(vars.signal)}</span></div>`:''}
        ${vars.gap?`<div>Gap angle: <span style="color:var(--text2)">${esc(vars.gap)}</span></div>`:''}
        ${vars.watchout?`<div>Watchout: <span class="badge ${vars.watchout==='GREEN'?'bg':vars.watchout==='RED'?'br':'ba'}" style="margin-left:4px">${esc(vars.watchout)}</span></div>`:''}
      </div>` : ''}
    </div>`;
}

function renderTrackingCard(d) {
  const records = d.tracking_records || [];
  const rows = records.map(r => {
    const dash = r.dashboard_entry || {};
    return `
    <div class="track-row">
      <div>
        <div class="track-name">${esc(r.contact_name||'—')}</div>
        <div class="track-id">${esc(r.tracking_id||'')}</div>
        ${r.contact_email?`<div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-top:2px">${esc(r.contact_email)}</div>`:''}
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        ${badge(dash.status||'NOT_SENT')}
        ${badge(dash.next_action||'Send Touch 1','bg')}
      </div>
      <div class="track-score">${dash.engagement_score??0}</div>
    </div>`;
  }).join('');

  $('card-tracking').innerHTML = `
    <div class="card-head"><span class="card-title">Engagement Tracking</span></div>
    <div class="card-body">
      ${rows || '<div style="color:var(--text3);font-family:var(--mono);font-size:12px">No tracking records yet</div>'}
      <div style="margin-top:16px;padding:12px 14px;background:var(--bg3);border-radius:6px;font-family:var(--mono);font-size:10px;color:var(--text3);line-height:1.9">
        <div>Scoring: open +1 · click +5 · reply +10 · meeting +20</div>
        <div style="margin-top:4px">HOT ≥20 · WARM ≥10 · ENGAGED ≥3 · OPENED ≥1</div>
        <div style="margin-top:4px">Pixel URL: ${esc(d.tracking_base_url||'—')}/open/{id}</div>
      </div>
    </div>`;
}

/* ══════════════════════════════════════════════════
   PDF EXPORT
══════════════════════════════════════════════════ */
function openExportPDF() {
  if (!currentReport) { toast('No report loaded'); return; }
  const html = buildPDFHTML(currentReport);
  const win  = window.open('', '_blank');
  if (!win) { toast('Allow popups to export PDF'); return; }
  win.document.write(html);
  win.document.close();
  win.onload = () => setTimeout(() => win.print(), 600);
}
window.openExportPDF = openExportPDF;

function buildPDFHTML(data) {
  const pipes = data.pipelines || {};
  const pout  = key => (pipes[key] || {}).output || {};
  const p01=pout('p01_company_overview'), p02=pout('p02_brand_identity'),
        p03=pout('p03_market_position'),  p04=pout('p04_competitor_mapping'),
        p05=pout('p05_brand_activity'),   p06=pout('p06_experiential_footprint'),
        p07=pout('p07_reputation_research'), p08=pout('p08_strategic_watchouts'),
        p09=pout('p09_decision_makers'),  p10=pout('p10_contact_intelligence'),
        p11=pout('p11_outreach');

  const e = esc;
  const icp = p01.icp_fit_score || 0;
  const icpColour = icp>=70?'#00cc34':icp>=40?'#ffaa00':'#ff3b3b';

  function svgGauge(pct, colour, size=80) {
    const r=28, cx=size/2, cy=size/2+8, circ=Math.PI*r;
    const offset = circ*(1-pct/100);
    return `<svg width="${size}" height="${size*0.7}" viewBox="0 0 ${size} ${size*0.7}">
      <path d="M${cx-r},${cy} A${r},${r},0,0,1,${cx+r},${cy}" fill="none" stroke="#1e1e1e" stroke-width="6"/>
      <path d="M${cx-r},${cy} A${r},${r},0,0,1,${cx+r},${cy}" fill="none" stroke="${colour}" stroke-width="6"
        stroke-dasharray="${circ}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
      <text x="${cx}" y="${cy-2}" text-anchor="middle" fill="${colour}" font-size="16" font-weight="700" font-family="monospace">${pct}</text>
    </svg>`;
  }

  function hBar(val, max, colour='#00cc34') {
    const pct = Math.round((val/max)*100);
    return `<div style="height:6px;background:#1e1e1e;border-radius:3px;overflow:hidden;margin:4px 0">
      <div style="height:100%;width:${pct}%;background:${colour};border-radius:3px"></div></div>`;
  }

  function section(title, content) {
    return `<div style="margin-bottom:28px;page-break-inside:avoid">
      <div style="font-family:monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#00cc34;border-bottom:1px solid #1e1e1e;padding-bottom:6px;margin-bottom:14px">${e(title)}</div>
      ${content}</div>`;
  }

  function row2(a, b) {
    return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:10px">${a}${b}</div>`;
  }

  function kvlist(items) {
    return items.filter(([,v])=>v!=null&&v!=='').map(([k,v])=>`
      <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e1e1e;font-size:12px">
        <span style="color:#555;font-family:monospace;font-size:10px;text-transform:uppercase">${e(k)}</span>
        <span style="color:#e8e8e8;text-align:right;max-width:60%">${e(v)}</span>
      </div>`).join('');
  }

  const colors = p02.primary_colors || p02.extracted_colors || [];
  const colSwatches = colors.slice(0,8).map(c=>`<div style="width:32px;height:32px;border-radius:4px;background:${e(c)};display:inline-block;margin-right:4px;border:1px solid rgba(255,255,255,.1)" title="${e(c)}"></div>`).join('');

  const compRows = (p04.competitors||[]).slice(0,5).map(c=>`
    <tr>
      <td style="font-weight:600;color:#00cc34;font-family:monospace;font-size:11px;padding:7px 8px;border-bottom:1px solid #1e1e1e">${e(c.name||'')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1e1e1e;font-size:11px;color:#999">${e(c.brand_positioning||'—')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1e1e1e;font-size:11px">${e(c.events_activity||'—')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1e1e1e;font-size:11px;color:#555">${e(c.experiential_gap||'—')}</td>
    </tr>`).join('');

  const eventRows = (p06.events_timeline||[]).slice(0,8).map(ev=>`
    <div style="padding:10px 12px;background:#0e0e0e;border:1px solid #1e1e1e;border-left:3px solid #008f24;border-radius:4px;margin-bottom:8px;page-break-inside:avoid">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px">
        <span style="font-weight:600;font-size:13px">${e(ev.event_name||ev.name||'?')}</span>
        <span style="font-family:monospace;font-size:10px;color:#555">${e(ev.date||ev.year||'')}</span>
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap">
        ${ev.format?`<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid #00aaff33;color:#00aaff;border-radius:3px">${e(ev.format)}</span>`:''}
        ${ev.brand_role?`<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid #00ff4133;color:#00cc34;border-radius:3px">${e(ev.brand_role)}</span>`:''}
        ${ev.location?`<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid #2a2a2a;color:#999;border-radius:3px">📍 ${e(ev.location)}</span>`:''}
      </div>
    </div>`).join('');

  const peopleCards = (p09.buying_committee||[]).slice(0,4).map(p=>{
    const ct = (p10.contacts||[]).find(c=>c.name===p.name) || {};
    return `
    <div style="padding:12px;background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;margin-bottom:8px;page-break-inside:avoid">
      <div style="font-weight:700;font-size:14px;margin-bottom:2px">${e(p.name||'—')}</div>
      <div style="font-family:monospace;font-size:11px;color:#999;margin-bottom:8px">${e(p.title||'—')}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
        ${p.outreach_priority==='PRIMARY'?`<span style="font-family:monospace;font-size:9px;padding:2px 7px;background:#00ff4114;border:1px solid #00ff4140;color:#00cc34;border-radius:3px">PRIMARY</span>`:''}
        ${ct.email?`<span style="font-family:monospace;font-size:9px;padding:2px 7px;background:#00aaff10;border:1px solid #00aaff30;color:#00aaff;border-radius:3px">✉ ${e(ct.email)}</span>`:''}
        ${p.decision_relevance_score?`<span style="font-family:monospace;font-size:9px;padding:2px 7px;border:1px solid #2a2a2a;color:#555;border-radius:3px">Score ${p.decision_relevance_score}/5</span>`:''}
      </div>
      ${p.personalisation_hook?`<div style="font-size:11px;color:#555;font-style:italic">${e(p.personalisation_hook)}</div>`:''}
    </div>`;
  }).join('');

  const touchCards = Object.entries(p11.outreach_sequence||{}).map(([key,t])=>{
    const isLI = (t.channel||'').toLowerCase()==='linkedin';
    return `
    <div style="padding:14px;background:#0e0e0e;border:1px solid #1e1e1e;border-left:3px solid ${isLI?'#00aaff':'#008f24'};border-radius:4px;margin-bottom:10px;page-break-inside:avoid">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <span style="font-family:monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:${isLI?'#00aaff':'#00cc34'}">${e(t.channel||key)}</span>
        <span style="font-family:monospace;font-size:10px;color:#555">Day ${t.send_day||'—'}</span>
      </div>
      ${t.subject_line?`<div style="font-weight:600;font-size:13px;margin-bottom:8px">📧 ${e(t.subject_line)}</div>`:''}
      <div style="font-size:12px;color:#999;line-height:1.75;white-space:pre-line">${e(t.message||'—')}</div>
    </div>`;
  }).join('');

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<title>BrandScope Report — ${e(data.company_name)}</title>
<style>
  @page { size: A4; margin: 18mm 20mm; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#000; color:#e8e8e8; font-family:'Inter',system-ui,sans-serif; font-size:13px; line-height:1.6; }
  .page-break { page-break-before: always; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style></head><body style="padding:0">

<!-- COVER PAGE -->
<div style="min-height:100vh;display:flex;flex-direction:column;justify-content:space-between;padding:48px 40px;background:#000;border-bottom:2px solid #00ff41">
  <div>
    <div style="font-family:monospace;font-size:11px;letter-spacing:.2em;color:#00cc34;text-transform:uppercase;margin-bottom:8px">◈ BrandScope · StepOneXP Intelligence</div>
    <h1 style="font-size:42px;font-weight:700;color:#fff;letter-spacing:-.02em;margin-bottom:6px">${e(data.company_name)}</h1>
    <div style="font-family:monospace;font-size:13px;color:#555;margin-bottom:32px">${e(data.category||'')}</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;max-width:600px">
      <div style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;padding:14px;text-align:center">
        ${svgGauge(icp, icpColour, 80)}
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#555;text-transform:uppercase;margin-top:4px">ICP Score</div>
      </div>
      <div style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;padding:14px;text-align:center">
        <div style="font-size:28px;font-weight:700;font-family:monospace;color:${p08.overall_verdict==='GREEN'?'#00cc34':p08.overall_verdict==='RED'?'#ff3b3b':'#ffaa00'};margin-bottom:4px">${e(p08.overall_verdict||'—')}</div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#555;text-transform:uppercase">Watchout</div>
      </div>
      <div style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;padding:14px;text-align:center">
        <div style="font-size:24px;font-weight:700;font-family:monospace;color:#00cc34;margin-bottom:4px">${e(p06.experiential_maturity_score||'—')}<span style="font-size:13px;color:#555">/5</span></div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#555;text-transform:uppercase">Events Score</div>
      </div>
      <div style="background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;padding:14px;text-align:center">
        <div style="font-size:24px;font-weight:700;font-family:monospace;color:#00cc34;margin-bottom:4px">${p09.total_contacts_found||0}</div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#555;text-transform:uppercase">Contacts</div>
      </div>
    </div>
  </div>
  <div style="font-family:monospace;font-size:10px;color:#333;letter-spacing:.06em">
    ${e(data.run_id||'')} · Generated ${new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})} · Total runtime: ${data.total_elapsed?.toFixed(1)||'?'}s
  </div>
</div>

<!-- PAGE 2: COMPANY + BRAND -->
<div class="page-break" style="padding:40px">

  ${section('Company Overview', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>${kvlist([
        ['Business Model', p01.business_model],
        ['Industry', p01.industry_vertical],
        ['Founded', p01.founding_year],
        ['Employees', p01.employee_count_range],
        ['Funding', p01.funding_status],
        ['Revenue', p01.revenue_range],
        ['HQ', p01.hq_city ? p01.hq_city+', '+(p01.geography||'') : p01.geography],
        ['Readiness', p01.experiential_readiness],
        ['Recommended Service', p01.recommended_service],
      ])}</div>
      <div>
        <div style="font-size:12px;color:#999;line-height:1.7;padding:14px;background:#0e0e0e;border-radius:6px;border:1px solid #1e1e1e">${e(p01.company_narrative||'No narrative available.')}</div>
        ${(p01.key_facts||[]).length ? `<div style="margin-top:10px">${p01.key_facts.slice(0,3).map(f=>`<div style="font-size:11px;padding:5px 8px;background:#0e0e0e;border-left:2px solid #00cc34;margin-bottom:4px;color:#999">${e(f)}</div>`).join('')}</div>` : ''}
      </div>
    </div>`
  )}

  ${section('Brand Identity', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        ${colSwatches ? `<div style="margin-bottom:12px">${colSwatches}</div>` : ''}
        ${kvlist([
          ['Primary Font', (p02.primary_fonts||p02.extracted_fonts||[])[0]],
          ['Brand Tone', p02.brand_tone],
          ['Visual Style', p02.visual_style],
          ['Brand Maturity', p02.brand_maturity],
          ['Tagline', p02.tagline],
        ])}
      </div>
      <div>
        ${(p02.brand_voice_keywords||[]).length ? `<div style="margin-bottom:10px"><div style="font-family:monospace;font-size:9px;color:#555;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Voice Keywords</div><div style="display:flex;flex-wrap:wrap;gap:4px">${p02.brand_voice_keywords.map(k=>`<span style="font-family:monospace;font-size:10px;padding:2px 7px;background:#00ff4114;border:1px solid #00ff4140;color:#00cc34;border-radius:3px">${e(k)}</span>`).join('')}</div></div>` : ''}
        ${p02.experiential_design_angle?`<div style="font-size:12px;color:#999;line-height:1.65;padding:12px;background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;margin-top:8px">🎨 ${e(p02.experiential_design_angle)}</div>`:''}
      </div>
    </div>`
  )}
</div>

<!-- PAGE 3: MARKET + COMPETITORS -->
<div class="page-break" style="padding:40px">

  ${section('Market Position & Reputation', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        <div style="font-family:monospace;font-size:9px;color:#555;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">Market Position</div>
        ${kvlist([
          ['Share of Voice', p03.share_of_voice_level],
          ['Sentiment', p03.brand_sentiment],
          ['Perception Gap', p03.perception_gap_score ? p03.perception_gap_score+'/5' : null],
          ['Sentiment Shift', p03.recent_sentiment_shift],
        ])}
        ${p03.market_position_summary?`<div style="margin-top:10px;font-size:11px;color:#555;line-height:1.65">${e(p03.market_position_summary)}</div>`:''}
      </div>
      <div>
        <div style="font-family:monospace;font-size:9px;color:#555;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">Reputation</div>
        ${kvlist([
          ['Score', p07.overall_reputation_score ? p07.overall_reputation_score+'/100' : null],
          ['Label', p07.reputation_label],
          ['NPS Signal', p07.nps_signal],
          ['Community', p07.brand_community_strength],
          ['Reddit', p07.reddit_sentiment],
        ])}
        ${p07.reputation_opportunity?`<div style="margin-top:10px;font-size:11px;color:#00cc34;padding:8px 10px;background:#00ff4110;border:1px solid #00ff4130;border-radius:4px">🎯 ${e(p07.reputation_opportunity)}</div>`:''}
      </div>
    </div>`
  )}

  ${section('Competitor Mapping', `
    ${compRows ? `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">
      <thead><tr>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#555;padding:6px 8px;text-align:left;border-bottom:1px solid #1e1e1e">Brand</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#555;padding:6px 8px;text-align:left;border-bottom:1px solid #1e1e1e">Positioning</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#555;padding:6px 8px;text-align:left;border-bottom:1px solid #1e1e1e">Events</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#555;padding:6px 8px;text-align:left;border-bottom:1px solid #1e1e1e">Their Gap</th>
      </tr></thead>
      <tbody>${compRows}</tbody>
    </table></div>` : '<div style="color:#555;font-family:monospace;font-size:12px">No competitor data</div>'}
    ${p04.experiential_white_space?`<div style="margin-top:12px;font-size:12px;color:#00cc34;padding:10px 12px;background:#00ff4110;border:1px solid #00ff4130;border-radius:4px">🎯 White space: ${e(p04.experiential_white_space)}</div>`:''}
  `)}
</div>

<!-- PAGE 4: EVENTS -->
<div class="page-break" style="padding:40px">
  ${section('Experiential Footprint', `
    <div style="display:grid;grid-template-columns:160px 1fr;gap:24px;margin-bottom:20px">
      <div style="text-align:center;padding:16px;background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px">
        <div style="font-size:42px;font-weight:700;font-family:monospace;color:#00cc34">${p06.experiential_maturity_score||'?'}</div>
        <div style="font-size:10px;font-family:monospace;color:#555;text-transform:uppercase;letter-spacing:.1em">/5 Maturity</div>
        ${hBar((p06.experiential_maturity_score||0),5,'#00cc34')}
      </div>
      <div>
        ${kvlist([
          ['Events Found', (p06.events_timeline||[]).length],
          ['Frequency', p06.events_frequency],
          ['Last Event', p06.last_event_months_ago!=null ? p06.last_event_months_ago+' months ago' : null],
          ['Geography', (p06.geography_of_events||[]).join(' · ')||null],
        ])}
        ${p06.pitch_angle?`<div style="margin-top:10px;font-size:12px;color:#00cc34;padding:8px 10px;background:#00ff4110;border:1px solid #00ff4130;border-radius:4px">🎯 ${e(p06.pitch_angle)}</div>`:''}
      </div>
    </div>
    ${eventRows || '<div style="color:#555;font-family:monospace;font-size:12px;padding:16px 0">No confirmed events found in research data</div>'}
    ${(p06.formats_missing||[]).length?`<div style="margin-top:12px;padding:10px 12px;background:#ffaa0010;border:1px solid #ffaa0030;border-radius:4px;font-size:11px;color:#ffaa00">📌 Missing formats: ${e(p06.formats_missing.join(' · '))}</div>`:''}`
  )}
</div>

<!-- PAGE 5: PEOPLE + OUTREACH -->
<div class="page-break" style="padding:40px">

  ${section('Decision Makers & Contact Intelligence', `
    ${peopleCards || '<div style="color:#555;font-family:monospace;font-size:12px">No decision makers found</div>'}
    ${p10.email_pattern?`<div style="margin-top:12px;padding:10px 12px;background:#0e0e0e;border:1px solid #1e1e1e;border-radius:4px;font-family:monospace;font-size:11px;color:#555">Email pattern: <span style="color:#00cc34">${e(p10.email_pattern)}@${e(p10.domain||'?')}</span> · ${p10.verified_emails||0} verified · ${p10.inferred_emails||0} inferred</div>`:''}`
  )}

  ${section('4-Touch Outreach Sequence', `
    ${p11.primary_contact?.name ? `<div style="padding:10px 14px;background:#0e0e0e;border:1px solid #1e1e1e;border-radius:6px;margin-bottom:14px;font-size:13px;display:flex;flex-wrap:wrap;gap:12px;align-items:center">
      <span style="font-weight:700">${e(p11.primary_contact.name)}</span>
      ${p11.primary_contact.title?`<span style="color:#555">${e(p11.primary_contact.title)}</span>`:''}
      ${p11.primary_contact.email?`<span style="font-family:monospace;font-size:11px;color:#00aaff">✉ ${e(p11.primary_contact.email)}</span>`:''}
    </div>` : ''}
    ${touchCards}`
  )}
</div>

<!-- PAGE 6: STRATEGIC NOTES -->
<div class="page-break" style="padding:40px">
  ${section('Strategic Watchouts & Timing', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        ${kvlist([
          ['Verdict', p08.overall_verdict],
          ['Timing', p08.timing_recommendation],
          ['Tone Adjustment', p08.pitch_tone_adjustment],
          ['Marketing Freeze', p08.marketing_freeze_detected?'Yes':'No'],
        ])}
        ${p08.verdict_reasoning?`<div style="margin-top:12px;font-size:12px;color:#999;line-height:1.65">${e(p08.verdict_reasoning)}</div>`:''}
      </div>
      <div>
        ${(p08.financial_distress_signals||[]).length?`<div style="margin-bottom:12px"><div style="font-family:monospace;font-size:9px;color:#ff3b3b;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Financial Signals</div>${p08.financial_distress_signals.slice(0,2).map(s=>`<div style="font-size:11px;color:#999;padding:5px 8px;border-left:2px solid #ff3b3b;margin-bottom:4px">${e(s)}</div>`).join('')}</div>`:''}
        ${(p08.leadership_changes||[]).length?`<div><div style="font-family:monospace;font-size:9px;color:#00cc34;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Leadership Changes</div>${p08.leadership_changes.map(lc=>`<div style="font-size:11px;color:#999;padding:5px 8px;border-left:2px solid #00cc34;margin-bottom:4px"><span style="color:#00cc34">${e(lc.role)}</span>: ${e(lc.change)} — ${e(lc.implication||'')}</div>`).join('')}</div>`:''}
      </div>
    </div>`
  )}

  ${section('Brand Activity (Last 24 Months)', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>${kvlist([
        ['Content Cadence', p05.social_content_cadence],
        ['PR Activity', p05.pr_activity_level],
        ['Budget Signal', p05.budget_signal],
        ['Seasonal Pattern', p05.seasonal_pattern],
        ['Last Campaign', p05.last_major_campaign],
        ['Next Window', p05.upcoming_opportunity_window],
      ])}</div>
      <div>${(p05.recent_campaigns||[]).slice(0,3).map(c=>`<div style="font-size:11px;padding:7px 10px;background:#0e0e0e;border-radius:4px;margin-bottom:5px"><span style="color:#00cc34;font-weight:600">${e(c.name||'?')}</span> <span style="color:#555">${e(c.date||'')} · ${e(c.channel||'')}</span>${c.description?`<div style="color:#555;margin-top:3px;font-size:10px">${e(c.description)}</div>`:''}</div>`).join('')}</div>
    </div>`
  )}

  <!-- Footer -->
  <div style="margin-top:40px;padding-top:20px;border-top:1px solid #1e1e1e;font-family:monospace;font-size:10px;color:#333;display:flex;justify-content:space-between">
    <span>BrandScope by StepOneXP · Automated Brand Intelligence</span>
    <span>${e(data.run_id||'')} · ${data.total_elapsed?.toFixed(1)||'?'}s · 12 pipelines</span>
  </div>
</div>

</body></html>`;
}

/* ══════════════════════════════════════════════════
   REPORTS
══════════════════════════════════════════════════ */
async function loadReports() {
  const grid = $('reportsGrid');
  grid.textContent = 'Loading...';
  try {
    const res  = await fetch(`${API}/reports`);
    const data = await res.json();
    if (!data.reports?.length) {
      grid.innerHTML = '<div style="color:var(--text3);grid-column:1/-1;font-family:var(--mono);font-size:12px">No past reports found.</div>';
      return;
    }
    grid.innerHTML = data.reports.map(r => `
      <div class="report-card" onclick="loadReport('${esc(r.run_id||'')}').then(()=>showSection('results'))">
        <div class="report-company">${esc(r.company||r.run_id||'—')}</div>
        <div class="report-meta">
          <span>${esc(r.run_id||'')}</span>
          ${r.elapsed ? `<span>${r.elapsed.toFixed(1)}s · 12 pipelines</span>` : ''}
          <span>${r.completed_at ? new Date(r.completed_at).toLocaleDateString() : ''}</span>
        </div>
        <div class="report-status"><span class="badge ${r.status==='success'?'bg':r.status==='partial'?'ba':'br'}">${esc(r.status||'?')}</span></div>
      </div>`).join('');
  } catch {
    grid.innerHTML = '<div style="color:var(--red);font-family:var(--mono);font-size:12px">Could not load reports — is the API running?</div>';
  }
}
