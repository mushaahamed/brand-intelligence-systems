'use strict';
/* ═══════════════════════════════════════════════════════
   BrandScope v2 — Intelligence Frontend
   Harmonic-inspired · Dark Navy · Multi-person Outreach
   ═══════════════════════════════════════════════════════ */

const API  = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';
const POLL = 1000;

let jobId         = null;
let pollTimer     = null;
let currentReport = null;
let currentRunId  = null;
let timerInterval = null;
let jobStart      = null;
let logCount      = 0;
let activeContact = 0;
let currentSeqs   = [];  // current contact sequences for outreach tab

const PIPELINES = [
  { id:'p01', label:'P01', name:'Company Overview'     },
  { id:'p02', label:'P02', name:'Brand Identity'       },
  { id:'p03', label:'P03', name:'Market Position'      },
  { id:'p04', label:'P04', name:'Competitor Mapping'   },
  { id:'p05', label:'P05', name:'Brand Activity'       },
  { id:'p06', label:'P06', name:'Events Footprint'     },
  { id:'p07', label:'P07', name:'Reputation Research'  },
  { id:'p08', label:'P08', name:'Strategic Watchouts'  },
  { id:'p09', label:'P09', name:'Decision Makers'      },
  { id:'p10', label:'P10', name:'Contact Intelligence' },
  { id:'p11', label:'P11', name:'Outreach Sequences'   },
  { id:'p12', label:'P12', name:'Tracking Setup'       },
];

/* ── DOM helpers ── */
const $  = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function toast(msg, ms = 3000) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), ms);
}

function initials(name) {
  if (!name) return '?';
  return name.split(/\s+/).slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}

/* ── KV helper (new CSS class names) ── */
function kv(key, val, cls = '') {
  if (val == null || val === '' || val === undefined) return '';
  return `<div class="kv"><span class="kk">${esc(key)}</span><span class="kv-val ${cls}">${esc(val)}</span></div>`;
}

function badge(txt, cls = '') {
  if (!txt) return '';
  return `<span class="badge ${cls}">${esc(txt)}</span>`;
}

function verdictCls(v) {
  if (!v) return '';
  const up = String(v).toUpperCase();
  if (['HIGH','POSITIVE','STRONG','GOOD','GREEN'].includes(up)) return 'g';
  if (['LOW','NEGATIVE','POOR','RED'].includes(up)) return 'r';
  if (['MEDIUM','MIXED','NEUTRAL','AMBER','MODERATE'].includes(up)) return 'a';
  return '';
}

/* ════════════════════════════════════════════════════════
   NAVIGATION
════════════════════════════════════════════════════════ */
function showSection(name) {
  ['form','analysis','results','reports'].forEach(s => {
    const el = $(`sec-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  $('nav-analyse')?.classList.toggle('active', name === 'form');
  $('nav-reports')?.classList.toggle('active', name === 'reports');
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
  btn.innerHTML = '<span>Starting…</span>';

  const payload = {
    company_name: $('company_name').value.trim(),
    company_url:  $('company_url').value.trim(),
    category:     $('category').value.trim(),
  };

  try {
    const res = await fetch(`${API}/analyse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    startAnalysis(data.job_id, payload.company_name);
  } catch (err) {
    toast(`⚠ ${err.message}`, 5000);
    btn.disabled = false;
    btn.innerHTML = '<span>Run Analysis</span><svg class="btn-arrow" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }
});

/* ════════════════════════════════════════════════════════
   ANALYSIS — AI THINKING VIEW
════════════════════════════════════════════════════════ */
function startAnalysis(jid, companyName) {
  jobId    = jid;
  jobStart = Date.now();
  logCount = 0;
  activeContact = 0;

  showSection('analysis');
  buildPipelineGrid();
  startElapsedTimer();

  const log = $('termLog');
  if (log) log.innerHTML = '';
  addStreamEntry('system', 'info', `Initialising analysis for "${companyName}"`);
  addStreamEntry('system', 'info', `Job ID: ${jid} · 12 intelligence pipelines queued`);

  $('analysisTitle').textContent  = `Analysing ${companyName}`;
  $('analysisSubtitle').textContent = 'Connecting to intelligence pipelines…';

  pollTimer = setInterval(doPoll, POLL);
}

function startElapsedTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const s  = Math.floor((Date.now() - jobStart) / 1000);
    const m  = Math.floor(s / 60);
    const ss = String(s % 60).padStart(2, '0');
    const el = $('elapsedTimer');
    if (el) el.textContent = `${m}:${ss}`;
  }, 500);
}

function buildPipelineGrid() {
  const grid = $('pipelineGrid');
  if (!grid) return;
  grid.innerHTML = PIPELINES.map(p => `
    <div class="pi" id="pi-${p.id}">
      <span class="pi-num">${p.label}</span>
      <div class="pi-body">
        <div class="pi-name">${p.name}</div>
        <div class="pi-status" id="pi-${p.id}-status">waiting</div>
      </div>
      <span class="pi-icon" id="pi-${p.id}-icon">○</span>
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
        addStreamEntry('system', 'complete', `Analysis complete · ${data.elapsed?.toFixed(1) || '?'}s · all 12 pipelines`);
        PIPELINES.forEach(p => setPipeState(p.id, 'done', ''));
        $('ppBar').style.width  = '100%';
        $('ppPct').textContent  = '100%';
        $('ppStats').textContent = '12 / 12 pipelines complete';
        $('analysisPhase').textContent     = 'Complete';
        $('analysisSubtitle').textContent  = 'All pipelines finished — loading results…';
        setTimeout(() => { if (data.run_id) loadReport(data.run_id); }, 700);
      } else {
        addStreamEntry('system', 'error', `Analysis failed — ${data.error || 'unknown error'}`);
        toast('Analysis failed', 5000);
        resetSubmitBtn();
      }
    }
  } catch { /* silent retry */ }
}

function updateAnalysisView(data) {
  const done      = data.pipelines_done     || [];
  const running   = data.running_pipelines  || [];
  const summaries = data.pipeline_summaries || {};
  const logEntries = data.pipeline_log      || [];
  const pct = Math.min(95, Math.round((done.length / 12) * 100));

  $('ppBar').style.width  = `${pct}%`;
  $('ppPct').textContent  = `${pct}%`;
  $('ppStats').textContent = `${done.length} / 12 pipelines complete`;

  // Phase indicator
  const phase = done.length < 9 ? 'Phase 1 — Parallel Research' : 'Phase 2 — Sequential Synthesis';
  $('analysisPhase').textContent = phase;

  // Render new log entries
  if (logEntries.length > logCount) {
    logEntries.slice(logCount).forEach(entry => {
      const pipeName = PIPELINES.find(p =>
        entry.pipeline?.startsWith(p.id + '_') || entry.pipeline === p.id
      )?.label || (entry.pipeline === 'system' ? 'SYS' : entry.pipeline?.slice(0,3).toUpperCase() || '?');
      addStreamEntry(pipeName, entry.type, entry.message);
    });
    logCount = logEntries.length;
  }

  // Update pipeline cards
  PIPELINES.forEach(p => {
    const fullKey = done.find(d => d.startsWith(p.id + '_') || d === p.id);
    const isRun   = running.some(r => r.startsWith(p.id + '_') || r === p.id);
    const sum     = summaries[fullKey] || {};

    if (fullKey && sum.status === 'error') {
      setPipeState(p.id, 'error', sum.finding || 'Pipeline error');
    } else if (fullKey) {
      const finding = (sum.finding || '').replace(/\s*\[[\d.]+s\]$/, '');
      setPipeState(p.id, 'done', finding || 'Complete');
    } else if (isRun) {
      setPipeState(p.id, 'running', 'scanning…');
    }
  });
}

function setPipeState(shortId, state, finding) {
  const el     = $(`pi-${shortId}`);
  const status = $(`pi-${shortId}-status`);
  const icon   = $(`pi-${shortId}-icon`);
  if (!el) return;

  el.className = `pi${state ? ' pi--' + state : ''}`;
  const icons = { running: '⟳', done: '✓', error: '✗' };
  if (icon)   icon.textContent = icons[state] || '○';
  if (status && finding) status.textContent = finding;
}

function addStreamEntry(pipeline, type, msg) {
  const log = $('termLog');
  if (!log) return;

  // Filter raw Python/backend errors — show clean message instead
  const isBackendNoise = /cannot import|ModuleNotFoundError|Traceback|File "\/|\.py\"|raise |Exception|KeyError|AttributeError|ImportError/i.test(msg);
  if (isBackendNoise) {
    if (type === 'error') msg = 'Pipeline encountered an issue — retrying…';
    else return; // skip noise entirely
  }

  const s   = Math.floor((Date.now() - (jobStart || Date.now())) / 1000);
  const ts  = `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  const div = document.createElement('div');
  div.className = `sl t-${type || 'info'}`;
  div.innerHTML = `<span class="sl-ts">${ts}</span><span class="sl-badge">${esc(pipeline || 'SYS')}</span><span class="sl-msg">${esc(msg)}</span>`;
  log.appendChild(div);
  if (log.children.length > 300) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}

function resetSubmitBtn() {
  const btn = $('submitBtn');
  if (!btn) return;
  btn.disabled = false;
  btn.innerHTML = '<span>Run Analysis</span><svg class="btn-arrow" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
}

/* ════════════════════════════════════════════════════════
   LOAD & RENDER REPORT
════════════════════════════════════════════════════════ */
async function loadReport(runId) {
  try {
    const res = await fetch(`${API}/report/${runId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentReport = data;
    currentRunId  = runId;
    showSection('results');   // show section first so all elements are live in DOM
    renderReport(data);
    resetSubmitBtn();
  } catch (err) {
    console.error('loadReport error:', err);
    toast(`Could not load report: ${err.message}`, 5000);
  }
}
window.loadReport = loadReport;

function renderReport(data) {
  if (!data) { console.error('renderReport: data is null'); return; }

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

  /* ── Results header ── */
  const rhCompany = $('rhCompany');
  if (rhCompany) rhCompany.textContent = data.company_name || '—';

  const elapsed = data.total_elapsed != null
    ? ` · ${Number(data.total_elapsed).toFixed(1)}s` : '';
  const rhMeta = $('rhMeta');
  if (rhMeta) rhMeta.textContent = `${data.run_id || ''} · ${data.category || ''}${elapsed}`;

  const v   = p08.overall_verdict || '';
  const vEl = $('rhVerdict');
  if (v && vEl) { vEl.className = `rh-verdict ${v}`; vEl.textContent = v; }

  /* ── All cards — each isolated so one failure never blocks the others ── */
  const _safe = (fn, label) => {
    try { fn(); }
    catch (e) { console.warn(`renderReport: ${label} failed —`, e.message); }
  };

  _safe(() => renderCompanyCard(p01),          'company');
  _safe(() => renderWatchoutsCard(p08),         'watchouts');
  _safe(() => renderReputationCard(p07),        'reputation');
  _safe(() => renderTimingCard(p08),            'timing');
  _safe(() => renderColorsCard(p02),            'colors');
  _safe(() => renderVoiceCard(p02),             'voice');
  _safe(() => renderCompetitorsCard(p04),       'competitors');
  _safe(() => renderPositionCard(p03),          'position');
  _safe(() => renderActivityCard(p05),          'activity');
  _safe(() => renderEventsCard(p06),            'events');
  _safe(() => renderPeopleCard(p09, p10),       'people');
  _safe(() => renderOutreachSection(p11, p09),  'outreach');
  _safe(() => renderTrackingCard(p12),          'tracking');
}

/* ════════════════════════════════════════════════════════
   CARD RENDERERS
════════════════════════════════════════════════════════ */

/* ICP Score Card */
function renderIcpCard(d, p06) {
  const score     = d.icp_fit_score ?? 0;
  const colorHex  = score >= 70 ? '#10B981' : score >= 40 ? '#F59E0B' : '#EF4444';
  const label     = score >= 70 ? 'HIGH FIT' : score >= 40 ? 'MEDIUM FIT' : 'LOW FIT';
  const readiness = d.experiential_readiness || '';
  const readCls   = verdictCls(readiness) === 'g' ? 'green' : verdictCls(readiness) === 'r' ? 'red' : 'amber';

  // Full-circle ring gauge
  const r = 38, cx = 52, cy = 52;
  const circ  = 2 * Math.PI * r;
  const fill  = circ * (score / 100);
  const gap   = circ - fill;

  // Service fit from P06
  const svc        = (p06 || {}).agency_service_fit || {};
  const svcService = svc.primary_service || '';
  const svcOpp     = svc.opportunity_size || '';

  $('card-icp-score').innerHTML = `
    <div class="card-head"><span class="card-title">ICP Fit</span></div>
    <div class="icp-card-body">
      <div class="icp-ring-wrap">
        <svg width="104" height="104" viewBox="0 0 104 104">
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--bg-3)" stroke-width="7"/>
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${colorHex}" stroke-width="7"
            stroke-linecap="round" stroke-dasharray="${fill.toFixed(1)} ${gap.toFixed(1)}"
            transform="rotate(-90 ${cx} ${cy})"/>
        </svg>
        <div class="icp-ring-center">
          <span class="icp-score-big" style="color:${colorHex}">${score}</span>
          <span class="icp-score-sub">/100</span>
        </div>
      </div>
      <div class="icp-score-label" style="color:${colorHex}">${label}</div>
      ${readiness ? `<div class="badge ${readCls}" style="margin-top:6px">${esc(readiness)}</div>` : ''}
      ${d.recommended_service ? `<div class="icp-service-hint">${esc(d.recommended_service)}</div>` : ''}
      ${svcService ? `
      <div style="margin-top:10px;padding:8px 10px;background:rgba(79,70,229,0.12);border:1px solid rgba(99,102,241,0.3);border-radius:6px;text-align:center">
        <div style="font-family:var(--mono);font-size:8px;color:#818CF8;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px">Service Fit</div>
        <div style="font-size:11px;font-weight:600;color:#C7D2FE;line-height:1.3">${esc(svcService)}</div>
        ${svcOpp ? `<div style="margin-top:4px;font-size:9px;color:#A5B4FC">${esc(svcOpp.split('(')[0].trim())}</div>` : ''}
      </div>` : ''}
    </div>`;
}

/* Company Overview */
function renderCompanyCard(d) {
  const el = $('card-company'); if (!el) return;
  const readiness = d.experiential_readiness || '';
  const readCls   = verdictCls(readiness) === 'g' ? 'green' : verdictCls(readiness) === 'r' ? 'red' : 'amber';
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Company Overview</span>
      ${readiness ? `<span class="badge ${readCls}">${esc(readiness)} Readiness</span>` : ''}
    </div>
    <div class="card-body">
      ${kv('Business Model', d.business_model)}
      ${kv('Industry', d.industry_vertical)}
      ${kv('Founded', d.founding_year)}
      ${kv('Employees', d.employee_count || d.employee_count_range)}
      ${kv('Funding', d.funding_status || d.funding_stage)}
      ${kv('Revenue', d.revenue_range)}
      ${kv('HQ', d.hq_city ? `${d.hq_city}, ${d.geography || ''}` : d.geography)}
      ${d.recommended_service ? `<div class="insight" style="margin-top:10px">🎯 ${esc(d.recommended_service)}</div>` : ''}
      ${d.company_narrative ? `<div class="card-note">${esc(d.company_narrative)}</div>` : ''}
    </div>`;
}

/* Strategic Watchouts */
function renderWatchoutsCard(d) {
  const el = $('card-watchouts'); if (!el) return;
  const v   = d.overall_verdict || '';
  const cls = v === 'GREEN' ? 'green' : v === 'RED' ? 'red' : 'amber';
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Strategic Watchouts</span>
      ${v ? `<span class="badge ${cls}">${v}</span>` : ''}
    </div>
    <div class="card-body">
      ${kv('Timing', d.timing_recommendation)}
      ${kv('Tone', d.pitch_tone_adjustment)}
      ${(d.financial_distress_signals || []).length ? `<div class="insight red" style="margin-top:10px">⚠ ${esc(d.financial_distress_signals[0])}</div>` : ''}
      ${(d.leadership_changes || []).length ? `<div class="insight" style="margin-top:8px">🔄 ${esc(d.leadership_changes[0].change)} — ${esc(d.leadership_changes[0].implication || '')}</div>` : ''}
      ${d.verdict_reasoning ? `<div class="card-note">${esc(d.verdict_reasoning)}</div>` : ''}
    </div>`;
}

/* Reputation */
function renderReputationCard(d) {
  const el = $('card-reputation'); if (!el) return;
  const lc  = verdictCls(d.reputation_label);
  const lcl = lc === 'g' ? 'green' : lc === 'r' ? 'red' : lc === 'a' ? 'amber' : '';
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Reputation</span>
      ${d.reputation_label ? `<span class="badge ${lcl}">${esc(d.reputation_label)}</span>` : ''}
    </div>
    <div class="card-body">
      ${kv('Score', d.overall_reputation_score ? `${d.overall_reputation_score}/100` : null)}
      ${kv('NPS Signal', d.nps_signal)}
      ${kv('Community', d.brand_community_strength)}
      ${kv('Reddit', d.reddit_sentiment)}
      ${(d.reddit_key_themes || []).length ? `<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:4px">${d.reddit_key_themes.slice(0,5).map(t => badge(t)).join('')}</div>` : ''}
      ${d.reputation_opportunity ? `<div class="insight green" style="margin-top:12px">🎯 ${esc(d.reputation_opportunity)}</div>` : ''}
    </div>`;
}

/* Pitch Timing */
function renderTimingCard(d) {
  const el = $('card-timing'); if (!el) return;
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Pitch Timing Intelligence</span></div>
    <div class="card-body">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div>
          ${kv('Verdict', d.overall_verdict, verdictCls(d.overall_verdict))}
          ${kv('Recommendation', d.timing_recommendation)}
          ${kv('Tone Adjustment', d.pitch_tone_adjustment)}
          ${kv('Marketing Freeze', d.marketing_freeze_detected ? 'Detected' : null, 'r')}
        </div>
        <div>
          ${(d.leadership_changes || []).map(lc => `
            <div style="padding:10px 12px;background:var(--bg-2);border:1px solid var(--border);border-left:3px solid var(--green);border-radius:var(--radius-sm);margin-bottom:8px;font-size:12px">
              <div style="color:var(--green);font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.05em">${esc(lc.role)} ${esc(lc.date || '')}</div>
              <div style="margin-top:4px;color:var(--text)">${esc(lc.change)}</div>
              <div style="color:var(--text-3);font-size:11px;margin-top:3px">${esc(lc.implication || '')}</div>
            </div>`).join('')}
        </div>
      </div>
    </div>`;
}

/* Brand Colours */
function renderColorsCard(d) {
  const el = $('card-colors'); if (!el) return;
  const colors   = d.primary_colors || d.extracted_colors || [];
  const swatches = colors.slice(0, 12).map(c =>
    `<div class="swatch" style="background:${esc(c)}" title="${esc(c)}"></div>`).join('');
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Brand Colours</span></div>
    <div class="card-body">
      ${swatches ? `<div class="swatch-row">${swatches}</div>` : ''}
      <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">
        ${colors.slice(0, 6).map(c => `<span class="badge" style="font-family:var(--mono);font-size:9px">${esc(c)}</span>`).join('')}
      </div>
      ${kv('Brand Tone', d.brand_tone)}
      ${kv('Visual Style', d.visual_style)}
      ${kv('Brand Maturity', d.brand_maturity)}
      ${d.experiential_design_angle ? `<div class="insight" style="margin-top:12px">🎨 ${esc(d.experiential_design_angle)}</div>` : ''}
    </div>`;
}

/* Brand Voice */
function renderVoiceCard(d) {
  const el = $('card-voice'); if (!el) return;
  const kw    = d.brand_voice_keywords || [];
  const fonts = d.primary_fonts || d.extracted_fonts || [];
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Brand Voice & Typography</span></div>
    <div class="card-body">
      ${kv('Primary Font', fonts[0] || null)}
      ${kv('Secondary Font', fonts[1] || null)}
      ${kv('Tagline', d.tagline)}
      ${kv('Logo Style', d.logo_style)}
      ${kw.length ? `<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:5px">${kw.map(k => badge(k, 'indigo')).join('')}</div>` : ''}
      ${(d.missing_brand_elements || []).length ? `<div class="insight amber" style="margin-top:12px">📌 Missing: ${esc(d.missing_brand_elements.join(' · '))}</div>` : ''}
    </div>`;
}

/* Competitors */
function renderCompetitorsCard(d) {
  const el = $('card-competitors'); if (!el) return;
  const comps = d.competitors || [];
  const rows  = comps.slice(0, 5).map(c => `
    <tr>
      <td>${esc(c.name || '—')}</td>
      <td>${esc(c.brand_positioning || '—')}</td>
      <td>${esc(c.events_activity || '—')}</td>
      <td style="color:var(--text-3);font-size:11px">${esc(c.experiential_gap || '—')}</td>
      <td>${badge(c.threat_level_to_brand, c.threat_level_to_brand === 'HIGH' ? 'red' : c.threat_level_to_brand === 'LOW' ? 'green' : 'amber')}</td>
    </tr>`).join('');
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Competitor Mapping</span>
      ${d.competitive_urgency === 'YES' ? `<span class="badge red">⚡ Competitor active</span>` : ''}
    </div>
    <div class="card-body">
      ${rows ? `<div style="overflow-x:auto"><table class="comp-table">
        <thead><tr><th>Brand</th><th>Positioning</th><th>Events</th><th>Their Gap</th><th>Threat</th></tr></thead>
        <tbody>${rows}</tbody></table></div>` : '<span style="color:var(--text-3)">No competitors identified</span>'}
      ${d.experiential_white_space ? `<div class="insight" style="margin-top:14px">🎯 White space: ${esc(d.experiential_white_space)}</div>` : ''}
    </div>`;
}

/* Market Position */
function renderPositionCard(d) {
  const el = $('card-position'); if (!el) return;
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Market Position</span></div>
    <div class="card-body">
      ${kv('Share of Voice', d.share_of_voice_level, verdictCls(d.share_of_voice_level))}
      ${kv('Sentiment', d.brand_sentiment, verdictCls(d.brand_sentiment))}
      ${kv('Perception Gap', d.perception_gap_score ? `${d.perception_gap_score}/5` : null)}
      ${kv('Sentiment Shift', d.recent_sentiment_shift)}
      ${d.pitch_implication ? `<div class="insight" style="margin-top:12px">💡 ${esc(d.pitch_implication)}</div>` : ''}
      ${d.market_position_summary ? `<div class="card-note">${esc(d.market_position_summary)}</div>` : ''}
    </div>`;
}

/* Brand Activity */
function renderActivityCard(d) {
  const el = $('card-activity'); if (!el) return;
  const campaigns = d.recent_campaigns || [];
  el.innerHTML = `
    <div class="card-head"><span class="card-title">Brand Activity</span>
      ${d.budget_signal ? `<span class="badge ${d.budget_signal === 'HIGH' ? 'green' : d.budget_signal === 'LOW' ? 'red' : 'amber'}">${esc(d.budget_signal)} budget</span>` : ''}
    </div>
    <div class="card-body">
      ${kv('Content Cadence', d.social_content_cadence)}
      ${kv('PR Activity', d.pr_activity_level)}
      ${kv('Seasonal Pattern', d.seasonal_pattern)}
      ${kv('Next Window', d.upcoming_opportunity_window)}
      ${kv('Last Campaign', d.last_major_campaign)}
      ${campaigns.length ? `<div style="margin-top:14px;display:flex;flex-direction:column;gap:8px">
        ${campaigns.slice(0, 3).map(c => `
          <div style="padding:10px 12px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-sm)">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <span style="font-weight:600;font-size:13px;color:var(--text)">${esc(c.name || '?')}</span>
              ${badge(c.channel || '?')}
              <span style="font-size:11px;color:var(--text-3)">${esc(c.date || '')}</span>
            </div>
            ${c.description ? `<div style="font-size:12px;color:var(--text-3)">${esc(c.description)}</div>` : ''}
          </div>`).join('')}
      </div>` : ''}
      ${d.activity_summary ? `<div class="card-note">${esc(d.activity_summary)}</div>` : ''}
    </div>`;
}

/* Events */
function renderEventsCard(d) {
  const el = $('card-events'); if (!el) return;
  const events = d.events_timeline || [];
  const score  = d.experiential_maturity_score;
  const pct    = score ? (score / 5) * 100 : 0;
  const sColor = score >= 4 ? 'green' : score >= 2 ? '' : 'amber';
  const svc    = d.agency_service_fit || {};

  /* ── Agency Service Fit banner ── */
  const oppColors = {
    'LARGE': { bg: '#D1FAE5', border: '#6EE7B7', text: '#065F46' },
    'MEDIUM': { bg: '#FEF3C7', border: '#FCD34D', text: '#92400E' },
    'SMALL': { bg: '#F3F4F6', border: '#D1D5DB', text: '#374151' },
  };
  const oppKey    = (svc.opportunity_size || '').split(' ')[0].toUpperCase();
  const oppStyle  = oppColors[oppKey] || oppColors['MEDIUM'];

  /* Proof reference colour (indigo) */
  const serviceFitBlock = svc.primary_service ? `
    <div style="margin-bottom:20px;border-radius:10px;overflow:hidden;border:1px solid #C7D2FE">
      <div style="background:#4F46E5;padding:10px 16px;display:flex;align-items:center;gap:10px">
        <span style="font-size:16px">🎯</span>
        <span style="font-family:var(--mono);font-size:10px;letter-spacing:.12em;color:#C7D2FE;text-transform:uppercase;font-weight:700">Agency Service Fit</span>
      </div>
      <div style="background:#EEF2FF;padding:14px 16px;display:grid;gap:10px">
        <div style="display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap">
          <div style="flex:1;min-width:180px">
            <div style="font-family:var(--mono);font-size:9px;color:#6366F1;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Primary Service</div>
            <div style="font-size:14px;font-weight:700;color:#1E1B4B">${esc(svc.primary_service)}</div>
          </div>
          ${svc.opportunity_size ? `
          <div style="background:${oppStyle.bg};border:1px solid ${oppStyle.border};border-radius:6px;padding:6px 12px;align-self:flex-start">
            <div style="font-family:var(--mono);font-size:9px;color:${oppStyle.text};letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px">Opportunity</div>
            <div style="font-size:13px;font-weight:700;color:${oppStyle.text}">${esc(svc.opportunity_size)}</div>
          </div>` : ''}
        </div>
        ${svc.pitch_reference ? `
        <div style="background:#fff;border-radius:6px;border:1px solid #C7D2FE;padding:10px 12px">
          <div style="font-family:var(--mono);font-size:9px;color:#6366F1;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Reference in Outreach</div>
          <div style="font-size:12px;color:#1E1B4B">📌 ${esc(svc.pitch_reference)}</div>
        </div>` : ''}
        ${svc.first_event_possible ? `
        <div style="background:#fff;border-radius:6px;border:1px solid #C7D2FE;padding:10px 12px">
          <div style="font-family:var(--mono);font-size:9px;color:#6366F1;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">First Win Possible</div>
          <div style="font-size:12px;color:#1E1B4B">🚀 ${esc(svc.first_event_possible)}</div>
        </div>` : ''}
      </div>
    </div>` : '';

  const eventCards = events.slice(0, 8).map(ev => `
    <div class="event-card">
      <div class="event-head">
        <span class="event-name">${esc(ev.event_name || ev.name || 'Untitled')}</span>
        <span class="event-date">${esc(ev.date || ev.year || '')}</span>
      </div>
      <div class="event-badges">
        ${badge(ev.format, 'blue')}
        ${badge(ev.scale)}
        ${ev.location ? badge('📍 ' + ev.location) : ''}
        ${badge(ev.brand_role, 'green')}
        ${badge(ev.production_quality, 'amber')}
      </div>
      ${ev.source && ev.source !== 'inferred from brand scale / training knowledge'
        ? `<div style="margin-top:6px;font-size:11px;color:var(--text-3)">${esc(ev.source.slice(0,100))}</div>` : ''}
    </div>`).join('');

  el.innerHTML = `
    <div class="card-head">
      <span class="card-title">Experiential Footprint</span>
      ${score ? `<span style="font-family:var(--mono);font-size:22px;font-weight:700;color:var(--green)">${score}<span style="font-size:12px;color:var(--text-3)">/5</span></span>` : ''}
    </div>
    <div class="card-body">
      ${serviceFitBlock}
      <div style="margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--text-3);margin-bottom:5px">
          <span>MATURITY SCORE</span><span>${score || '?'}/5</span>
        </div>
        <div class="score-bar-outer"><div class="score-bar-inner ${sColor}" style="width:${pct}%"></div></div>
        ${d.maturity_score_reasoning ? `<div style="font-size:11px;color:var(--text-3);margin-top:4px">${esc(d.maturity_score_reasoning)}</div>` : ''}
      </div>
      <div style="margin-bottom:14px">
        ${kv('Frequency', d.events_frequency)}
        ${kv('Last Event', d.last_event_months_ago != null ? `${d.last_event_months_ago} months ago` : null)}
        ${(d.geography_of_events || []).length ? kv('Geography', d.geography_of_events.join(' · ')) : ''}
      </div>
      ${events.length ? eventCards : '<div style="color:var(--text-3);padding:20px 0;text-align:center;font-family:var(--mono);font-size:12px">No confirmed events in research data</div>'}
      ${(d.formats_used || []).length ? `<div style="margin-top:14px"><div style="font-family:var(--mono);font-size:10px;color:var(--text-3);letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Formats Used</div><div style="display:flex;flex-wrap:wrap;gap:4px">${d.formats_used.map(f => badge(f, 'green')).join('')}</div></div>` : ''}
      ${(d.formats_missing || []).length ? `<div class="insight amber" style="margin-top:12px">📌 Missing formats: ${esc(d.formats_missing.join(' · '))}</div>` : ''}
      ${d.pitch_angle ? `<div class="insight" style="margin-top:10px">🎯 ${esc(d.pitch_angle)}</div>` : ''}
      ${d.opening_line_for_pitch ? `<div style="margin-top:12px;padding:12px 14px;background:var(--indigo-dim);border:1px solid var(--indigo-border);border-radius:var(--radius-sm);font-size:13px;font-style:italic;color:#818CF8">"${esc(d.opening_line_for_pitch)}"</div>` : ''}
    </div>`;
}

/* People */
function renderPeopleCard(p09, p10) {
  const el = $('card-people'); if (!el) return;
  const people   = p09.buying_committee || [];
  const contacts = p10.contacts || [];
  const cmap     = {};
  contacts.forEach(c => { if (c.name) cmap[c.name] = c; });

  const cards = people.map(p => {
    const ct    = cmap[p.name] || {};
    const email = ct.email || '';
    const conf  = ct.email_confidence ? `${ct.email_confidence}%` : '';
    const score = p.decision_relevance_score || 0;
    const ini   = initials(p.name);
    return `
    <div class="person-card">
      <div class="person-avatar">${ini}</div>
      <div class="person-name">${esc(p.name || '—')}</div>
      <div class="person-title">${esc(p.title || '—')}</div>
      <div class="person-score-label">Decision Relevance ${score}/5</div>
      <div class="person-score-bar"><div class="person-score-fill" style="width:${score * 20}%"></div></div>
      <div class="person-meta" style="margin-top:8px">
        ${p.outreach_priority === 'PRIMARY' ? badge('PRIMARY', 'green') : p.outreach_priority === 'SECONDARY' ? badge('SECONDARY', 'amber') : ''}
        ${p.role_type ? badge(p.role_type) : ''}
        ${p.linkedin_activity ? badge('LinkedIn: ' + p.linkedin_activity) : ''}
        ${email ? badge('✉ ' + email + (conf ? ' (' + conf + ')' : ''), 'blue') : ''}
        ${ct.recommended_channel ? badge(ct.recommended_channel) : ''}
      </div>
      ${p.personalisation_hook ? `<div class="person-hook">💡 ${esc(p.personalisation_hook)}</div>` : ''}
    </div>`;
  }).join('');

  el.innerHTML = `
    <div class="card-head"><span class="card-title">Decision Makers & Contact Intelligence</span>
      ${people.length ? `<span class="badge indigo">${people.length} stakeholder${people.length !== 1 ? 's' : ''}</span>` : ''}
    </div>
    <div class="card-body">
      <div class="people-grid">
        ${cards || '<div style="color:var(--text-3);padding:16px 0;font-family:var(--mono);font-size:12px">No decision makers found</div>'}
      </div>
      ${p10.email_pattern ? `<div class="email-pattern-bar">
        Email pattern: <strong style="color:var(--indigo)">${esc(p10.email_pattern)}</strong>
        <span>· ${p10.verified_emails || 0} verified</span>
        <span>· ${p10.inferred_emails || 0} inferred</span>
      </div>` : ''}
      ${p10.data_disclaimer ? `<div style="margin-top:8px;font-size:11px;color:var(--text-3)">⚠ ${esc(p10.data_disclaimer)}</div>` : ''}
    </div>`;
}

/* ════════════════════════════════════════════════════════
   OUTREACH — MULTI-PERSON
════════════════════════════════════════════════════════ */
function renderOutreachSection(d, p09) {
  const section = $('outreach-section');
  if (!section) return;

  // Collect sequences: new multi-contact format or legacy single
  let sequences = (d.contacts_sequences || []).filter(s => s.contact && s.sequence);
  if (!sequences.length && d.outreach_sequence) {
    const primary = d.primary_contact || {};
    // Try to enrich from p09
    const p09Contact = (p09.buying_committee || []).find(c => c.name === primary.name) || {};
    sequences = [{
      contact: {
        ...primary,
        personalisation_hook: p09Contact.personalisation_hook || '',
        role_type: p09Contact.role_type || '',
        outreach_priority: p09Contact.outreach_priority || 'PRIMARY',
        decision_relevance_score: p09Contact.decision_relevance_score || 0,
      },
      sequence: d.outreach_sequence,
      personalisation_vars: d.personalisation_variables_used || {},
    }];
  }

  if (!sequences.length) {
    section.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-3);font-family:var(--mono);font-size:13px">No outreach sequences generated</div>`;
    return;
  }

  currentSeqs   = sequences;
  activeContact = 0;

  const compUsed = (d.competitor_intel_used || []).filter(c => c.name).map(c => c.name);

  /* Contact tabs */
  const tabsHtml = sequences.map((s, i) => {
    const c   = s.contact || {};
    const ini = initials(c.name || '?');
    const pri = c.outreach_priority === 'PRIMARY';
    return `
    <button class="oct ${i === 0 ? 'active' : ''}" onclick="selectContact(${i})">
      <div class="oct-avatar">${ini}</div>
      <div class="oct-info">
        <div class="oct-name">${esc(c.name || '—')}</div>
        <div class="oct-title">${esc((c.title || '').slice(0, 28))}${(c.title || '').length > 28 ? '…' : ''}</div>
      </div>
      ${pri ? `<span class="oct-badge">PRIMARY</span>` : ''}
    </button>`;
  }).join('');

  section.innerHTML = `
    <div class="outreach-contacts-header">
      <span class="outreach-contacts-label">${sequences.length} Personalised Sequence${sequences.length !== 1 ? 's' : ''}</span>
      <div class="outreach-contact-tabs" id="outreach-contact-tabs">${tabsHtml}</div>
    </div>
    <div id="outreach-sequence-view"></div>`;

  renderContactSequence(0, sequences, compUsed);
}

function renderContactSequence(idx, sequences, compUsed) {
  const view = $('outreach-sequence-view');
  if (!view) return;
  const item = sequences[idx];
  if (!item) return;

  const c    = item.contact   || {};
  const seq  = item.sequence  || {};
  const vars = item.personalisation_vars || {};

  const touches = Object.entries(seq)
    .filter(([, t]) => t && typeof t === 'object')
    .sort(([a], [b]) => {
      const na = parseInt(a.replace(/\D/g, '')) || 0;
      const nb = parseInt(b.replace(/\D/g, '')) || 0;
      return na - nb;
    });

  const touchesHtml = touches.map(([key, t]) => {
    const isLI   = (t.channel || '').toLowerCase() === 'linkedin';
    const chCls  = isLI ? 'linkedin' : 'email';
    const msgSafe = (t.message || '').replace(/\\/g,'\\\\').replace(/`/g,"'").replace(/\$/g,'\\$');
    const emailHref = c.email && !isLI
      ? `mailto:${encodeURIComponent(c.email || '')}?subject=${encodeURIComponent(t.subject_line || '')}&body=${encodeURIComponent(t.message || '')}`
      : '';
    return `
    <div class="touch-card">
      <div class="touch-header">
        <span class="touch-day-badge">Day ${t.send_day || '—'}</span>
        <span class="touch-channel-badge ${chCls}">${esc(t.channel || key)}</span>
        ${t.subject_line ? `<span class="touch-subj">${esc(t.subject_line)}</span>` : ''}
      </div>
      <div class="touch-body">${esc(t.message || '—')}</div>
      <div style="padding:8px 18px 12px;display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--border)">
        ${emailHref ? `<a class="email-btn" href="${emailHref}">✉ Open in Email</a>` : ''}
        ${c.linkedin && isLI ? `<a class="email-btn" href="${esc(c.linkedin)}" target="_blank">in Open LinkedIn</a>` : ''}
        <button class="copy-btn" onclick="copyMsg(this,\`${msgSafe}\`)">Copy</button>
      </div>
    </div>`;
  }).join('');

  const sidebarHtml = `
    <div class="outreach-sidebar">
      <div class="outreach-intel-card">
        <div class="outreach-intel-header">Contact Profile</div>
        <div class="outreach-intel-body">
          <div class="intel-row">
            <span class="intel-label">Name</span>
            <span class="intel-value highlight">${esc(c.name || '—')}</span>
          </div>
          <div class="intel-row">
            <span class="intel-label">Title</span>
            <span class="intel-value">${esc(c.title || '—')}</span>
          </div>
          ${c.email ? `<div class="intel-row"><span class="intel-label">Email</span><span class="intel-value highlight">${esc(c.email)}</span></div>` : ''}
          ${c.linkedin ? `<div class="intel-row"><span class="intel-label">LinkedIn</span><a href="${esc(c.linkedin)}" target="_blank" class="intel-value" style="color:var(--blue)">View ↗</a></div>` : ''}
          ${c.decision_relevance_score ? `<div class="intel-row"><span class="intel-label">Relevance</span><span class="intel-value">${c.decision_relevance_score}/5</span></div>` : ''}
        </div>
      </div>
      ${vars.signal || vars.pain_point ? `
      <div class="outreach-intel-card">
        <div class="outreach-intel-header">Personalisation Variables</div>
        <div class="outreach-intel-body">
          ${vars.signal ? `<div class="intel-row"><span class="intel-label">Signal Used</span><span class="intel-value">${esc(vars.signal)}</span></div>` : ''}
          ${vars.pain_point ? `<div class="intel-row"><span class="intel-label">Pain Point</span><span class="intel-value highlight">${esc(vars.pain_point)}</span></div>` : ''}
          ${vars.competitor_used ? `<div class="intel-row"><span class="intel-label">Competitor</span><span class="intel-value">${esc(vars.competitor_used)}</span></div>` : ''}
          ${vars.watchout ? `<div class="intel-row"><span class="intel-label">Watchout</span><span class="intel-value">${esc(vars.watchout)}</span></div>` : ''}
        </div>
      </div>` : ''}
      ${c.personalisation_hook ? `
      <div class="outreach-intel-card">
        <div class="outreach-intel-header">Hook</div>
        <div class="outreach-intel-body">
          <div style="font-size:12px;color:var(--text-2);line-height:1.6;font-style:italic">"${esc(c.personalisation_hook)}"</div>
        </div>
      </div>` : ''}
      ${compUsed.length ? `
      <div class="outreach-intel-card">
        <div class="outreach-intel-header">Competitor Intel Used</div>
        <div class="outreach-intel-body">
          <div class="comp-tags">${compUsed.map(c => badge(c, 'amber')).join('')}</div>
        </div>
      </div>` : ''}
    </div>`;

  view.innerHTML = `
    <div class="outreach-body">
      <div class="outreach-sequence">${touchesHtml || '<div style="color:var(--text-3);padding:20px 0">No touches generated</div>'}</div>
      ${sidebarHtml}
    </div>`;
}

window.selectContact = function(idx) {
  activeContact = idx;
  const compUsed = (currentReport?.pipelines?.p11_outreach?.output?.competitor_intel_used || [])
    .filter(c => c.name).map(c => c.name);

  document.querySelectorAll('.oct').forEach((el, i) => el.classList.toggle('active', i === idx));
  renderContactSequence(idx, currentSeqs, compUsed);
};

/* Tracking — Excel-like table with status management */
function renderTrackingCard(d) {
  const el = $('card-tracking'); if (!el) return;
  const pipes = currentReport?.pipelines || {};
  const p11   = (pipes.p11_outreach || {}).output || {};
  const p09   = (pipes.p09_decision_makers || {}).output || {};
  const p10   = (pipes.p10_contact_intelligence || {}).output || {};

  // Collect all contacts from sequences or people list
  let contacts = [];
  const seqs = (p11.contacts_sequences || []).filter(s => s.contact);
  if (seqs.length) {
    seqs.forEach(s => {
      const c   = s.contact || {};
      const seq = s.sequence || {};
      const t1  = seq.touch_1 || Object.values(seq)[0] || {};
      contacts.push({ name: c.name || '—', title: c.title || '—', email: c.email || '',
        linkedin: c.linkedin || '', priority: c.outreach_priority || '',
        touch1_subject: t1.subject_line || '', touch1_body: t1.message || '' });
    });
  } else {
    const cmap = {};
    (p10.contacts || []).forEach(c => { if (c.name) cmap[c.name] = c; });
    (p09.buying_committee || []).forEach(p => {
      const ct = cmap[p.name] || {};
      const t1 = Object.values(p11.outreach_sequence || {})[0] || {};
      contacts.push({ name: p.name || '—', title: p.title || '—', email: ct.email || '',
        linkedin: ct.linkedin || '', priority: p.outreach_priority || '',
        touch1_subject: t1.subject_line || '', touch1_body: t1.message || '' });
    });
  }
  if (!contacts.length && (d.tracking_records || []).length) {
    (d.tracking_records || []).forEach(r => {
      contacts.push({ name: r.contact_name || '—', title: '', email: r.contact_email || '',
        linkedin: '', priority: '', touch1_subject: '', touch1_body: '' });
    });
  }

  const storageKey = `track_${currentRunId}`;
  let statuses = {};
  try { statuses = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch {}

  window._trackContacts = contacts;

  const rows = contacts.map((c, i) => {
    const st  = statuses[c.name] || 'new';
    const sub = encodeURIComponent(c.touch1_subject || `Following up — ${c.name}`);
    const bod = encodeURIComponent(c.touch1_body || '');
    const emailHref = c.email ? `mailto:${encodeURIComponent(c.email)}?subject=${sub}&body=${bod}` : '';
    return `
    <tr>
      <td>
        <div class="td-name">${esc(c.name)}</div>
        <div class="td-title">${esc(c.title)}</div>
      </td>
      <td>${badge(c.priority || '—', c.priority === 'PRIMARY' ? 'green' : c.priority ? 'amber' : '')}</td>
      <td class="td-email">${c.email ? esc(c.email) : '<span style="color:var(--text-4)">—</span>'}</td>
      <td>
        <select class="status-select s-${st}" onchange="updateTrackStatus('${esc(c.name).replace(/'/g,"\\'")}',this)">
          <option value="new"       ${st==='new'       ? 'selected':''}>🔵 New</option>
          <option value="pending"   ${st==='pending'   ? 'selected':''}>🟡 Pending</option>
          <option value="completed" ${st==='completed' ? 'selected':''}>🟢 Completed</option>
        </select>
      </td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${emailHref ? `<a class="email-btn" href="${emailHref}">✉ Email</a>` : ''}
          ${c.linkedin ? `<a class="email-btn" href="${esc(c.linkedin)}" target="_blank">in LinkedIn</a>` : ''}
          ${c.touch1_body ? `<button class="copy-btn" onclick="copyTouchMsg(this,${i})">Copy Msg</button>` : ''}
        </div>
      </td>
    </tr>`;
  }).join('');

  const nNew  = contacts.filter(c => !statuses[c.name] || statuses[c.name] === 'new').length;
  const nPend = contacts.filter(c => statuses[c.name] === 'pending').length;
  const nDone = contacts.filter(c => statuses[c.name] === 'completed').length;

  el.innerHTML = `
    <div class="card-head">
      <span class="card-title">Outreach Tracker</span>
      <button class="btn-ghost" onclick="exportTrackCSV()" style="font-size:12px;padding:5px 10px">↓ CSV</button>
    </div>
    <div class="card-body" style="padding:0">
      <div style="display:flex;gap:20px;padding:12px 20px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:11px;color:var(--text-3)">
        <span>${contacts.length} contacts</span>
        <span style="color:var(--blue)">● ${nNew} new</span>
        <span style="color:var(--amber)">● ${nPend} pending</span>
        <span style="color:var(--green)">● ${nDone} completed</span>
      </div>
      <div style="overflow-x:auto">
        <table class="track-table">
          <thead><tr><th>Contact</th><th>Priority</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5" style="color:var(--text-3);text-align:center;padding:24px">No contacts found — run an analysis first</td></tr>'}</tbody>
        </table>
      </div>
      <div style="padding:10px 20px;font-family:var(--mono);font-size:10px;color:var(--text-4);border-top:1px solid var(--border)">Statuses saved in browser · Export CSV to share or import to spreadsheet</div>
    </div>`;
}

window.updateTrackStatus = function(name, sel) {
  const storageKey = `track_${currentRunId}`;
  let s = {}; try { s = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch {}
  s[name] = sel.value;
  localStorage.setItem(storageKey, JSON.stringify(s));
  sel.className = `status-select s-${sel.value}`;
};

window.copyTouchMsg = function(btn, idx) {
  const c = window._trackContacts?.[idx];
  if (!c?.touch1_body) return;
  navigator.clipboard?.writeText(c.touch1_body).then(() => {
    btn.classList.add('copied'); btn.textContent = '✓ Copied';
    setTimeout(() => { btn.classList.remove('copied'); btn.textContent = 'Copy Msg'; }, 2000);
  }).catch(() => toast('Could not access clipboard'));
};

window.exportTrackCSV = function() {
  const contacts = window._trackContacts;
  if (!contacts?.length) { toast('No data to export'); return; }
  const storageKey = `track_${currentRunId}`;
  let statuses = {}; try { statuses = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch {}
  const rows = [['Name','Title','Priority','Email','LinkedIn','Status']];
  contacts.forEach(c => rows.push([c.name, c.title, c.priority, c.email, c.linkedin, statuses[c.name] || 'new']));
  const csv  = rows.map(r => r.map(v => `"${String(v||'').replace(/"/g,'""')}"`).join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = `outreach-${currentRunId || 'export'}.csv`;
  document.body.appendChild(a); a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 500);
};

/* ════════════════════════════════════════════════════════
   PDF EXPORT — Blob URL approach (works everywhere)
════════════════════════════════════════════════════════ */
function exportPDF() {
  if (!currentReport) { toast('No report loaded'); return; }
  toast('Generating PDF…');
  const html = buildPDFHTML(currentReport);
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const win  = window.open(url, '_blank');
  if (win) {
    win.addEventListener('load', () => { setTimeout(() => win.print(), 600); });
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } else {
    // Popup blocked → auto-download the HTML file instead
    const a = document.createElement('a');
    a.href = url;
    a.download = `brandscope-${(currentReport.company_name || 'report').replace(/\s+/g, '-').toLowerCase()}.html`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 1000);
    toast('Downloaded as HTML — open it then Ctrl+P to save as PDF', 6000);
  }
}
window.exportPDF = exportPDF;

function buildPDFHTML(data) {
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

  const e   = esc;
  const icp = p01.icp_fit_score || 0;
  const icpCol = icp >= 70 ? '#059669' : icp >= 40 ? '#D97706' : '#DC2626';
  const verdictCol = v => v === 'GREEN' ? '#059669' : v === 'RED' ? '#DC2626' : '#D97706';

  /* ── Full-circle ring gauge (consistent with web UI) ── */
  function ringGauge(score, colour, size = 90) {
    const r = 32, cx = size / 2, cy = size / 2;
    const circ = 2 * Math.PI * r;
    const fill = circ * (score / 100);
    const gap  = circ - fill;
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#E5E7EB" stroke-width="6"/>
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${colour}" stroke-width="6"
        stroke-linecap="round"
        stroke-dasharray="${fill.toFixed(1)} ${gap.toFixed(1)}"
        transform="rotate(-90 ${cx} ${cy})"/>
      <text x="${cx}" y="${cy + 6}" text-anchor="middle" fill="${colour}" font-size="18" font-weight="700" font-family="Inter,sans-serif">${score}</text>
    </svg>`;
  }

  /* ── Section header ── */
  function section(title, content) {
    return `<div style="margin-bottom:32px;page-break-inside:avoid">
      <div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#6B7280;
                  border-bottom:2px solid #111827;padding-bottom:7px;margin-bottom:16px">${e(title)}</div>
      ${content}
    </div>`;
  }

  /* ── Key-value row ── */
  function kv(k, v, colOverride) {
    if (v == null || v === '') return '';
    const vc = colOverride || '#111827';
    return `<div style="display:flex;justify-content:space-between;align-items:baseline;
                        padding:6px 0;border-bottom:1px solid #F3F4F6;font-size:12px">
      <span style="color:#6B7280;font-size:10.5px;flex-shrink:0;margin-right:12px">${e(k)}</span>
      <span style="color:${vc};text-align:right;font-weight:500">${e(String(v))}</span>
    </div>`;
  }

  /* ── Pill / badge ── */
  function pill(text, bg, border, col) {
    return `<span style="display:inline-block;font-size:9.5px;padding:2px 8px;background:${bg};
                          border:1px solid ${border};color:${col};border-radius:100px;white-space:nowrap">${e(text)}</span>`;
  }

  /* ── Highlight box ── */
  function highlight(text, accent) {
    return `<div style="margin-top:10px;font-size:11.5px;line-height:1.65;
                        padding:10px 13px;background:${accent}10;
                        border-left:3px solid ${accent};border-radius:0 4px 4px 0">${e(text)}</div>`;
  }

  /* ── Brand color swatches ── */
  const colors = p02.primary_colors || p02.extracted_colors || [];
  const swatches = colors.slice(0, 8).map(c =>
    `<div style="width:26px;height:26px;border-radius:50%;background:${e(c)};
                 display:inline-block;margin-right:5px;border:2px solid #fff;
                 box-shadow:0 0 0 1px #E5E7EB" title="${e(c)}"></div>`).join('');

  /* ── Competitor table rows ── */
  const compRows = (p04.competitors || []).slice(0, 5).map((c, i) => `
    <tr style="background:${i % 2 === 0 ? '#fff' : '#F9FAFB'}">
      <td style="font-weight:600;font-size:11.5px;padding:8px 10px;border-bottom:1px solid #E5E7EB;color:#111827">${e(c.name || '')}</td>
      <td style="padding:8px 10px;border-bottom:1px solid #E5E7EB;font-size:11px;color:#374151;max-width:160px">${e(c.brand_positioning || '—')}</td>
      <td style="padding:8px 10px;border-bottom:1px solid #E5E7EB;font-size:11px;text-align:center">
        ${c.events_activity === 'YES' ? pill('YES','#ECFDF5','#A7F3D0','#065F46') : c.events_activity === 'NO' ? pill('NO','#FEF2F2','#FECACA','#991B1B') : pill(c.events_activity||'—','#F9FAFB','#E5E7EB','#6B7280')}
      </td>
      <td style="padding:8px 10px;border-bottom:1px solid #E5E7EB;font-size:11px;color:#6B7280;max-width:160px">${e(c.experiential_gap || '—')}</td>
    </tr>`).join('');

  /* ── Events timeline ── */
  const eventCards = (p06.events_timeline || []).slice(0, 8).map(ev => `
    <div style="display:flex;gap:12px;padding:11px 0;border-bottom:1px solid #F3F4F6;page-break-inside:avoid">
      <div style="flex-shrink:0;font-size:10px;color:#9CA3AF;width:52px;padding-top:1px">${e(ev.date || ev.year || '—')}</div>
      <div style="flex:1">
        <div style="font-weight:600;font-size:12.5px;color:#111827;margin-bottom:4px">${e(ev.event_name || ev.name || '?')}</div>
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          ${ev.format ? pill(ev.format,'#EFF6FF','#BFDBFE','#1D4ED8') : ''}
          ${ev.brand_role ? pill(ev.brand_role,'#ECFDF5','#A7F3D0','#065F46') : ''}
          ${ev.location ? `<span style="font-size:10px;color:#9CA3AF">📍 ${e(ev.location)}</span>` : ''}
        </div>
      </div>
    </div>`).join('');

  /* ── People cards ── */
  const peopleCards = (p09.buying_committee || []).slice(0, 4).map(p => {
    const ct = (p10.contacts || []).find(c => c.name === p.name) || {};
    return `
    <div style="padding:14px 16px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
                margin-bottom:10px;page-break-inside:avoid">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
        <div>
          <div style="font-weight:700;font-size:14px;color:#111827">${e(p.name || '—')}</div>
          <div style="font-size:11.5px;color:#6B7280;margin-top:1px">${e(p.title || '—')}</div>
        </div>
        <div style="display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end">
          ${p.outreach_priority === 'PRIMARY' ? pill('PRIMARY','#ECFDF5','#A7F3D0','#065F46') : pill('SECONDARY','#F9FAFB','#E5E7EB','#6B7280')}
        </div>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
        ${ct.email ? `<span style="font-size:10.5px;color:#2563EB">✉ ${e(ct.email)}</span>` : ''}
        ${p.linkedin_url ? `<span style="font-size:10.5px;color:#2563EB">🔗 LinkedIn</span>` : ''}
      </div>
      ${p.personalisation_hook ? `<div style="font-size:11px;color:#6B7280;font-style:italic;padding-top:5px;border-top:1px solid #E5E7EB">${e(p.personalisation_hook)}</div>` : ''}
    </div>`;
  }).join('');

  /* ── Outreach sequences ── */
  let sequences = (p11.contacts_sequences || []).filter(s => s.contact && s.sequence);
  if (!sequences.length && p11.outreach_sequence) {
    sequences = [{ contact: p11.primary_contact || {}, sequence: p11.outreach_sequence }];
  }

  const channelStyle = isLI => isLI
    ? { bg:'#EFF6FF', border:'#BFDBFE', col:'#1D4ED8', accent:'#2563EB' }
    : { bg:'#F0FDF4', border:'#BBF7D0', col:'#065F46', accent:'#059669' };

  const outreachSections = sequences.slice(0, 4).map((item, idx) => {
    const c   = item.contact  || {};
    const seq = item.sequence || {};
    const touches = Object.entries(seq)
      .filter(([, t]) => t && typeof t === 'object')
      .sort(([a], [b]) => (parseInt(a.replace(/\D/g,''))||0) - (parseInt(b.replace(/\D/g,''))||0));

    const touchCards = touches.map(([key, t]) => {
      const isLI = (t.channel || '').toLowerCase() === 'linkedin';
      const s    = channelStyle(isLI);
      return `
      <div style="padding:13px 15px;background:${s.bg};border:1px solid ${s.border};
                  border-radius:6px;margin-bottom:10px;page-break-inside:avoid">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-size:9.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:${s.col}">${e(t.channel || key)}</span>
          <span style="font-size:10px;color:#6B7280;font-weight:500">Day ${t.send_day || '—'}</span>
        </div>
        ${t.subject_line ? `<div style="font-weight:700;font-size:12.5px;color:#111827;margin-bottom:8px">${e(t.subject_line)}</div>` : ''}
        <div style="font-size:12px;color:#374151;line-height:1.75;white-space:pre-line">${e(t.message || '—')}</div>
      </div>`;
    }).join('');

    return `
    <div style="margin-bottom:32px;page-break-before:${idx > 0 ? 'always' : 'auto'}">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #111827">
        <div style="background:#111827;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:100px">${idx + 1} of ${sequences.length}</div>
        <div>
          <span style="font-weight:700;font-size:14px;color:#111827">${e(c.name || '—')}</span>
          ${c.title ? `<span style="color:#6B7280;font-size:12px;margin-left:8px">${e(c.title)}</span>` : ''}
        </div>
        ${c.outreach_priority === 'PRIMARY' ? pill('PRIMARY','#ECFDF5','#A7F3D0','#065F46') : ''}
      </div>
      ${touchCards}
    </div>`;
  }).join('');

  /* ── Stat box (cover page metrics) ── */
  function statBox(label, value, col) {
    return `<div style="text-align:center;padding:20px 16px;background:#fff;border:1px solid #E5E7EB;border-radius:10px">
      <div style="font-size:26px;font-weight:800;color:${col};font-variant-numeric:tabular-nums;margin-bottom:4px">${e(String(value))}</div>
      <div style="font-size:9px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#9CA3AF">${e(label)}</div>
    </div>`;
  }

  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>BrandScope — ${e(data.company_name)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  @page { size: A4; margin: 14mm 18mm; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#fff; color:#111827; font-family:'Inter',system-ui,sans-serif; font-size:13px; line-height:1.6; }
  .pb { page-break-before: always; }
  @media print {
    body { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    .no-break { page-break-inside:avoid; }
  }
</style></head><body>

<!-- ═══ COVER PAGE ═══ -->
<div style="min-height:100vh;display:flex;flex-direction:column;padding:52px 44px;background:#fff">

  <!-- Header bar -->
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding-bottom:18px;border-bottom:3px solid #111827;margin-bottom:48px">
    <div style="font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#111827">
      BrandScope · Intelligence Report
    </div>
    <div style="font-size:10px;color:#9CA3AF">
      ${new Date().toLocaleDateString('en-GB', {day:'numeric', month:'long', year:'numeric'})}
    </div>
  </div>

  <!-- Company + category -->
  <div style="flex:1">
    <div style="font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
                color:#6B7280;margin-bottom:10px">${e(data.category || '')}</div>
    <h1 style="font-size:52px;font-weight:800;color:#111827;letter-spacing:-.04em;
               line-height:1.05;margin-bottom:28px">${e(data.company_name)}</h1>

    <!-- ICP ring + key metrics -->
    <div style="display:flex;align-items:center;gap:32px;margin-bottom:48px">
      <div style="text-align:center">
        ${ringGauge(icp, icpCol, 100)}
        <div style="font-size:9px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#9CA3AF;margin-top:4px">ICP Score</div>
        <div style="font-size:9.5px;font-weight:600;color:${icpCol};margin-top:2px">${icp >= 70 ? 'HIGH FIT' : icp >= 40 ? 'MEDIUM FIT' : 'LOW FIT'}</div>
      </div>
      <div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        ${statBox('Watchout', p08.overall_verdict || '—', verdictCol(p08.overall_verdict))}
        ${statBox('Event Maturity', (p06.experiential_maturity_score || '—') + ' / 5', '#2563EB')}
        ${statBox('Contacts Found', p09.total_contacts_found || (p09.buying_committee || []).length || 0, '#7C3AED')}
      </div>
    </div>

    <!-- Quick insights strip -->
    <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;padding:18px 22px">
      <div style="font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#6B7280;margin-bottom:10px">Intelligence Summary</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;font-size:12px">
        ${p01.business_model ? `<div><span style="color:#9CA3AF">Model: </span><span style="font-weight:600">${e(p01.business_model)}</span></div>` : ''}
        ${p01.funding_status ? `<div><span style="color:#9CA3AF">Funding: </span><span style="font-weight:600">${e(p01.funding_status)}</span></div>` : ''}
        ${p03.brand_sentiment ? `<div><span style="color:#9CA3AF">Sentiment: </span><span style="font-weight:600">${e(p03.brand_sentiment)}</span></div>` : ''}
        ${p07.reputation_label ? `<div><span style="color:#9CA3AF">Reputation: </span><span style="font-weight:600">${e(p07.reputation_label)}</span></div>` : ''}
        ${p08.timing_recommendation ? `<div><span style="color:#9CA3AF">Timing: </span><span style="font-weight:600">${e(p08.timing_recommendation)}</span></div>` : ''}
        ${p01.experiential_readiness ? `<div><span style="color:#9CA3AF">Readiness: </span><span style="font-weight:600">${e(p01.experiential_readiness)}</span></div>` : ''}
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div style="margin-top:40px;padding-top:16px;border-top:1px solid #E5E7EB;
              display:flex;justify-content:space-between;font-size:9.5px;color:#9CA3AF">
    <span>Built by StepOneXP · Brand Intelligence System</span>
    <span>${e(data.run_id || '')} · ${data.total_elapsed?.toFixed(1) || '?'}s · 12 pipelines</span>
  </div>
</div>

<!-- ═══ PAGE 2: Company Overview + Brand Identity ═══ -->
<div class="pb" style="padding:40px 44px">

  ${section('Company Overview', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
      <div>
        ${kv('Business Model', p01.business_model)}
        ${kv('Industry', p01.industry_vertical)}
        ${kv('Founded', p01.founding_year)}
        ${kv('Employees', p01.employee_count_range)}
        ${kv('Funding Status', p01.funding_status)}
        ${kv('Revenue Range', p01.revenue_range)}
        ${kv('Headquarters', p01.hq_city ? p01.hq_city + (p01.geography ? ', ' + p01.geography : '') : p01.geography)}
        ${kv('Experiential Readiness', p01.experiential_readiness, p01.experiential_readiness === 'HIGH' ? '#059669' : p01.experiential_readiness === 'LOW' ? '#DC2626' : '#D97706')}
        ${kv('Recommended Service', p01.recommended_service)}
      </div>
      <div>
        <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:15px;
                    font-size:12px;color:#374151;line-height:1.75;margin-bottom:12px">
          ${e(p01.company_narrative || 'No narrative available.')}
        </div>
        ${(p01.key_facts || []).length ? `
        <div>
          ${p01.key_facts.slice(0, 4).map(f => `
            <div style="font-size:11.5px;color:#374151;padding:5px 0 5px 12px;
                        border-left:2px solid #E5E7EB;margin-bottom:4px">${e(f)}</div>`).join('')}
        </div>` : ''}
      </div>
    </div>
  `)}

  ${section('Brand Identity', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
      <div>
        ${swatches ? `<div style="margin-bottom:14px">
          <div style="font-size:9.5px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;font-weight:600">Brand Palette</div>
          ${swatches}
        </div>` : ''}
        ${kv('Primary Font', (p02.primary_fonts || p02.extracted_fonts || [])[0])}
        ${kv('Brand Tone', p02.brand_tone)}
        ${kv('Visual Style', p02.visual_style)}
        ${kv('Brand Maturity', p02.brand_maturity)}
        ${p02.tagline ? kv('Tagline', p02.tagline) : ''}
      </div>
      <div>
        ${(p02.brand_voice_keywords || []).length ? `
        <div style="margin-bottom:14px">
          <div style="font-size:9.5px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.1em;font-weight:600;margin-bottom:8px">Voice Keywords</div>
          <div style="display:flex;flex-wrap:wrap;gap:5px">
            ${p02.brand_voice_keywords.map(k => pill(k,'#F0FDF4','#BBF7D0','#065F46')).join('')}
          </div>
        </div>` : ''}
        ${p02.experiential_design_angle ? highlight('Design angle for experiential: ' + p02.experiential_design_angle, '#7C3AED') : ''}
      </div>
    </div>
  `)}
</div>

<!-- ═══ PAGE 3: Market Position + Competitors ═══ -->
<div class="pb" style="padding:40px 44px">

  ${section('Market Position & Reputation', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
      <div>
        <div style="font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#6B7280;margin-bottom:10px">Market Position</div>
        ${kv('Share of Voice', p03.share_of_voice_level)}
        ${kv('Sentiment', p03.brand_sentiment, p03.brand_sentiment === 'POSITIVE' ? '#059669' : p03.brand_sentiment === 'NEGATIVE' ? '#DC2626' : '#374151')}
        ${kv('Perception Gap', p03.perception_gap_score ? p03.perception_gap_score + ' / 5' : null)}
        ${kv('Recent Shift', p03.recent_sentiment_shift)}
        ${p03.market_position_summary ? `<div style="margin-top:10px;font-size:11.5px;color:#374151;line-height:1.65">${e(p03.market_position_summary)}</div>` : ''}
        ${p03.pitch_implication ? highlight(p03.pitch_implication, '#2563EB') : ''}
      </div>
      <div>
        <div style="font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#6B7280;margin-bottom:10px">Reputation</div>
        ${kv('Score', p07.overall_reputation_score ? p07.overall_reputation_score + ' / 100' : null)}
        ${kv('Label', p07.reputation_label, p07.reputation_label === 'STRONG' || p07.reputation_label === 'GOOD' ? '#059669' : p07.reputation_label === 'POOR' ? '#DC2626' : '#374151')}
        ${kv('NPS Signal', p07.nps_signal)}
        ${kv('Community', p07.brand_community_strength)}
        ${p07.recent_controversy ? `<div style="margin-top:8px;font-size:11.5px;padding:8px 10px;background:#FEF2F2;border-left:3px solid #DC2626;border-radius:0 4px 4px 0;color:#7F1D1D">⚠ ${e(p07.recent_controversy)}</div>` : ''}
        ${p07.reputation_opportunity ? highlight(p07.reputation_opportunity, '#059669') : ''}
      </div>
    </div>
  `)}

  ${section('Competitor Mapping', `
    ${compRows ? `<table style="width:100%;border-collapse:collapse;border:1px solid #E5E7EB;border-radius:8px;overflow:hidden">
      <thead><tr style="background:#F9FAFB">
        <th style="font-size:9.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:8px 10px;text-align:left;border-bottom:2px solid #E5E7EB">Brand</th>
        <th style="font-size:9.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:8px 10px;text-align:left;border-bottom:2px solid #E5E7EB">Positioning</th>
        <th style="font-size:9.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:8px 10px;text-align:center;border-bottom:2px solid #E5E7EB">Events</th>
        <th style="font-size:9.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:8px 10px;text-align:left;border-bottom:2px solid #E5E7EB">Their Gap</th>
      </tr></thead>
      <tbody>${compRows}</tbody>
    </table>` : '<div style="color:#9CA3AF;font-size:12px">No competitor data available.</div>'}
    ${p04.experiential_white_space ? highlight('White space opportunity: ' + p04.experiential_white_space, '#059669') : ''}
    ${p04.recommended_pitch_angle ? highlight('Recommended angle: ' + p04.recommended_pitch_angle, '#7C3AED') : ''}
  `)}
</div>

<!-- ═══ PAGE 4: Experiential Footprint ═══ -->
<div class="pb" style="padding:40px 44px">

  ${section('Experiential & Events Footprint', `
    <div style="display:grid;grid-template-columns:130px 1fr;gap:24px;margin-bottom:24px">
      <div style="text-align:center;padding:18px 12px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px">
        <div style="font-size:44px;font-weight:800;color:#2563EB;line-height:1">${p06.experiential_maturity_score || '?'}</div>
        <div style="font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#9CA3AF;margin-top:4px">/ 5 Maturity</div>
        ${p06.confidence_level ? `<div style="margin-top:8px">${pill(p06.confidence_level,'#EFF6FF','#BFDBFE','#1D4ED8')}</div>` : ''}
      </div>
      <div>
        ${kv('Events in Timeline', (p06.events_timeline || []).length || null)}
        ${kv('Frequency', p06.events_frequency)}
        ${kv('Last Event', p06.last_event_months_ago != null ? p06.last_event_months_ago + ' months ago' : null)}
        ${kv('Geography', (p06.geography_of_events || []).slice(0,4).join(', ') || null)}
        ${p06.maturity_score_reasoning ? `<div style="margin-top:8px;font-size:11.5px;color:#6B7280;line-height:1.6">${e(p06.maturity_score_reasoning)}</div>` : ''}
        ${p06.pitch_angle ? highlight(p06.pitch_angle, '#059669') : ''}
      </div>
    </div>

    ${(() => {
      const svc = p06.agency_service_fit || {};
      if (!svc.primary_service) return '';
      const oppBg = { LARGE: '#D1FAE5', MEDIUM: '#FEF3C7', SMALL: '#F3F4F6' };
      const oppTx = { LARGE: '#065F46', MEDIUM: '#92400E', SMALL: '#374151' };
      const oppBd = { LARGE: '#6EE7B7', MEDIUM: '#FCD34D', SMALL: '#D1D5DB' };
      const ok = (svc.opportunity_size || '').split(' ')[0].toUpperCase();
      return `
      <div style="margin-bottom:18px;border-radius:8px;overflow:hidden;border:1px solid #C7D2FE">
        <div style="background:#4F46E5;padding:9px 14px;display:flex;align-items:center;gap:8px">
          <span style="font-size:13px">🎯</span>
          <span style="font-size:9px;font-weight:700;letter-spacing:.12em;color:#C7D2FE;text-transform:uppercase">Agency Service Fit</span>
        </div>
        <div style="background:#EEF2FF;padding:12px 14px;display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start">
          <div>
            <div style="font-size:9px;font-weight:600;letter-spacing:.1em;color:#6366F1;text-transform:uppercase;margin-bottom:3px">Primary Service</div>
            <div style="font-size:13px;font-weight:700;color:#1E1B4B;margin-bottom:8px">${e(svc.primary_service)}</div>
            ${svc.pitch_reference ? `<div style="font-size:10.5px;color:#374151;margin-bottom:4px">📌 <strong>Reference:</strong> ${e(svc.pitch_reference)}</div>` : ''}
            ${svc.first_event_possible ? `<div style="font-size:10.5px;color:#374151">🚀 <strong>First win:</strong> ${e(svc.first_event_possible)}</div>` : ''}
          </div>
          ${ok && oppBg[ok] ? `
          <div style="background:${oppBg[ok]};border:1px solid ${oppBd[ok]};border-radius:6px;padding:8px 12px;text-align:center;min-width:80px">
            <div style="font-size:8px;font-weight:700;letter-spacing:.1em;color:${oppTx[ok]};text-transform:uppercase;margin-bottom:2px">Opportunity</div>
            <div style="font-size:12px;font-weight:700;color:${oppTx[ok]}">${e(ok)}</div>
          </div>` : ''}
        </div>
      </div>`;
    })()}

    ${eventCards ? `<div style="margin-bottom:16px">${eventCards}</div>` : '<div style="color:#9CA3AF;font-size:12px;padding:16px 0">No confirmed events found in research period.</div>'}

    ${(p06.formats_missing || []).length ? `
    <div style="padding:11px 14px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:6px;font-size:11.5px;color:#92400E">
      <span style="font-weight:600">Missing formats: </span>${e(p06.formats_missing.join(' · '))}
    </div>` : ''}
  `)}
</div>

<!-- ═══ PAGE 5: Decision Makers + Watchouts ═══ -->
<div class="pb" style="padding:40px 44px">

  ${section('Decision Makers & Contact Intelligence', `
    ${peopleCards || '<div style="color:#9CA3AF;font-size:12px">No decision makers identified.</div>'}
    ${p10.email_pattern ? `
    <div style="margin-top:14px;padding:10px 14px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;font-size:11.5px;color:#6B7280">
      <span style="font-weight:600;color:#374151">Email pattern: </span>
      <span style="font-family:monospace;color:#2563EB">${e(p10.email_pattern)}</span>
      <span style="margin-left:12px">${p10.verified_emails || 0} verified · ${p10.inferred_emails || 0} pattern-inferred</span>
    </div>` : ''}
    ${p09.committee_gap && p09.committee_gap !== 'None' ? `<div style="margin-top:8px;font-size:11.5px;color:#D97706;padding:8px 12px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:4px">⚑ Gap in committee: ${e(p09.committee_gap)}</div>` : ''}
  `)}

  ${section('Strategic Watchouts', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
      <div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
          <div style="font-size:22px;font-weight:800;color:${verdictCol(p08.overall_verdict)}">${e(p08.overall_verdict || '—')}</div>
          <div style="font-size:11px;color:#6B7280">${e(p08.verdict_reasoning || '')}</div>
        </div>
        ${kv('Timing', p08.timing_recommendation, '#2563EB')}
        ${p08.pitch_tone_adjustment ? kv('Tone Guidance', p08.pitch_tone_adjustment) : ''}
        ${p08.timing_reasoning ? `<div style="margin-top:8px;font-size:11.5px;color:#6B7280;line-height:1.6">${e(p08.timing_reasoning)}</div>` : ''}
      </div>
      <div>
        ${(p08.financial_distress_signals || []).length ? `
        <div style="margin-bottom:12px">
          <div style="font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#DC2626;margin-bottom:6px">Financial Signals</div>
          ${p08.financial_distress_signals.slice(0, 2).map(s => `<div style="font-size:11px;color:#374151;padding:5px 8px;border-left:2px solid #DC2626;margin-bottom:4px">${e(s)}</div>`).join('')}
        </div>` : ''}
        ${(p08.leadership_changes || []).length ? `
        <div>
          <div style="font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#059669;margin-bottom:6px">Leadership Changes</div>
          ${p08.leadership_changes.slice(0, 2).map(lc => `<div style="font-size:11px;color:#374151;padding:5px 8px;border-left:2px solid #059669;margin-bottom:4px"><span style="font-weight:600">${e(lc.role)}: </span>${e(lc.change)}</div>`).join('')}
        </div>` : ''}
      </div>
    </div>
  `)}
</div>

<!-- ═══ OUTREACH SEQUENCES ═══ -->
${outreachSections ? `<div class="pb" style="padding:40px 44px">
  <div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#6B7280;
              border-bottom:2px solid #111827;padding-bottom:7px;margin-bottom:24px">
    4-Touch Outreach Sequences — ${sequences.length} Contact${sequences.length !== 1 ? 's' : ''}
  </div>
  ${outreachSections}
</div>` : ''}

<!-- ═══ DOCUMENT FOOTER ═══ -->
<div style="padding:18px 44px;border-top:1px solid #E5E7EB;
            display:flex;justify-content:space-between;align-items:center;font-size:9.5px;color:#9CA3AF">
  <span>BrandScope · Brand Intelligence System · StepOneXP</span>
  <span>${e(data.run_id || '')} · ${data.total_elapsed?.toFixed(1) || '?'}s · 12 pipelines · ${new Date().getFullYear()}</span>
</div>

</body></html>`;
}

/* Copy outreach message to clipboard */
window.copyMsg = function(btn, text) {
  navigator.clipboard?.writeText(text).then(() => {
    btn.classList.add('copied'); btn.textContent = '✓ Copied';
    setTimeout(() => { btn.classList.remove('copied'); btn.textContent = 'Copy'; }, 2000);
  }).catch(() => {
    // Fallback: select + copy
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.classList.add('copied'); btn.textContent = '✓ Copied';
    setTimeout(() => { btn.classList.remove('copied'); btn.textContent = 'Copy'; }, 2000);
  });
};

/* ════════════════════════════════════════════════════════
   REPORTS
════════════════════════════════════════════════════════ */
async function loadReports() {
  const grid = $('reportsGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="reports-loading">Loading…</div>';
  try {
    const res  = await fetch(`${API}/reports`);
    const data = await res.json();
    if (!data.reports?.length) {
      grid.innerHTML = '<div class="reports-loading">No past reports found.</div>';
      return;
    }
    grid.innerHTML = data.reports.map(r => `
      <div class="report-card" onclick="loadReport('${esc(r.run_id || '')}').then(()=>showSection('results'))">
        <div class="report-company">${esc(r.company || r.run_id || '—')}</div>
        <div class="report-meta">
          ${r.run_id ? `<span>${esc(r.run_id)}</span>` : ''}
          ${r.elapsed ? `<span>${r.elapsed.toFixed(1)}s · 12 pipelines</span>` : ''}
          ${r.completed_at ? `<span>${new Date(r.completed_at).toLocaleDateString()}</span>` : ''}
        </div>
        <div class="report-status">${badge(r.status || '?', r.status === 'success' ? 'green' : r.status === 'partial' ? 'amber' : 'red')}</div>
      </div>`).join('');
  } catch {
    grid.innerHTML = '<div style="color:var(--red);font-family:var(--mono);font-size:12px">Could not load reports — is the API running?</div>';
  }
}
