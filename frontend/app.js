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
      $(`pi-${p.id}-status`).textContent = 'scanning…';
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
    renderReport(data);
    showSection('results');
    resetSubmitBtn();
  } catch (err) {
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

  /* ── Results header ── */
  $('rhCompany').textContent = data.company_name || '—';
  const elapsed = data.total_elapsed ? ` · ${data.total_elapsed.toFixed(1)}s` : '';
  $('rhMeta').textContent = `${data.run_id || ''} · ${data.category || ''}${elapsed}`;

  const icp = p01.icp_fit_score ?? 0;
  const icpColor = icp >= 70 ? 'var(--green)' : icp >= 40 ? 'var(--amber)' : 'var(--red)';
  $('rhScore').textContent = icp || '—';
  $('rhScore').style.color = icpColor;
  $('rhScoreBar').style.width = `${icp}%`;
  $('rhScoreBar').style.background = icpColor;

  const v  = p08.overall_verdict || '';
  const vEl = $('rhVerdict');
  if (v && vEl) {
    vEl.className = `rh-verdict ${v}`;
    vEl.textContent = v;
  }

  /* ── All cards ── */
  renderIcpCard(p01);
  renderCompanyCard(p01);
  renderWatchoutsCard(p08);
  renderReputationCard(p07);
  renderTimingCard(p08);
  renderColorsCard(p02);
  renderVoiceCard(p02);
  renderCompetitorsCard(p04);
  renderPositionCard(p03);
  renderActivityCard(p05);
  renderEventsCard(p06);
  renderPeopleCard(p09, p10);
  renderOutreachSection(p11, p09);
  renderTrackingCard(p12);
}

/* ════════════════════════════════════════════════════════
   CARD RENDERERS
════════════════════════════════════════════════════════ */

/* ICP Gauge */
function renderIcpCard(d) {
  const score = d.icp_fit_score ?? 0;
  const color  = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--amber)' : 'var(--red)';
  const colorHex = score >= 70 ? '#10B981' : score >= 40 ? '#F59E0B' : '#EF4444';
  const pct   = score;
  const r     = 44;
  const cx    = 60; const cy = 64;
  const circ  = Math.PI * r;
  const offset = circ * (1 - pct / 100);

  const readiness = d.experiential_readiness || '';
  const readCls   = verdictCls(readiness) === 'g' ? 'green' : verdictCls(readiness) === 'r' ? 'red' : verdictCls(readiness) === 'a' ? 'amber' : '';

  $('card-icp-score').innerHTML = `
    <div class="card-head"><span class="card-title">ICP Fit</span></div>
    <div class="icp-card-body">
      <div class="icp-gauge-wrap">
        <svg width="120" height="72" viewBox="0 0 120 72">
          <path d="M16,64 A44,44,0,0,1,104,64" fill="none" stroke="var(--bg-3)" stroke-width="8" stroke-linecap="round"/>
          <path d="M16,64 A44,44,0,0,1,104,64" fill="none" stroke="${colorHex}" stroke-width="8"
            stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}" stroke-linecap="round"/>
        </svg>
        <div class="icp-label-center">
          <span class="icp-score-big" style="color:${color}">${score}</span>
          <span class="icp-score-sub">/100</span>
        </div>
      </div>
      <div class="icp-subtitle">ICP Score</div>
      ${readiness ? `<div class="icp-readiness badge ${readCls}">${esc(readiness)}</div>` : ''}
      ${d.recommended_service ? `<div style="font-size:11px;color:var(--text-3);text-align:center;margin-top:6px;line-height:1.4">${esc(d.recommended_service)}</div>` : ''}
    </div>`;
}

/* Company Overview */
function renderCompanyCard(d) {
  $('card-company').innerHTML = `
    <div class="card-head"><span class="card-title">Company Overview</span></div>
    <div class="card-body">
      ${kv('Business Model', d.business_model)}
      ${kv('Industry', d.industry_vertical)}
      ${kv('Founded', d.founding_year)}
      ${kv('Employees', d.employee_count || d.employee_count_range)}
      ${kv('Funding', d.funding_status || d.funding_stage)}
      ${kv('Revenue', d.revenue_range)}
      ${kv('HQ', d.hq_city ? `${d.hq_city}, ${d.geography || ''}` : d.geography)}
      ${d.company_narrative ? `<div class="card-note">${esc(d.company_narrative)}</div>` : ''}
    </div>`;
}

/* Strategic Watchouts */
function renderWatchoutsCard(d) {
  const v   = d.overall_verdict || '';
  const cls = v === 'GREEN' ? 'green' : v === 'RED' ? 'red' : 'amber';
  $('card-watchouts').innerHTML = `
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
  const lc  = verdictCls(d.reputation_label);
  const lcl = lc === 'g' ? 'green' : lc === 'r' ? 'red' : lc === 'a' ? 'amber' : '';
  $('card-reputation').innerHTML = `
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
  $('card-timing').innerHTML = `
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
  const colors   = d.primary_colors || d.extracted_colors || [];
  const swatches = colors.slice(0, 12).map(c =>
    `<div class="swatch" style="background:${esc(c)}" title="${esc(c)}"></div>`).join('');
  $('card-colors').innerHTML = `
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
  const kw    = d.brand_voice_keywords || [];
  const fonts = d.primary_fonts || d.extracted_fonts || [];
  $('card-voice').innerHTML = `
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
  const comps = d.competitors || [];
  const rows  = comps.slice(0, 5).map(c => `
    <tr>
      <td>${esc(c.name || '—')}</td>
      <td>${esc(c.brand_positioning || '—')}</td>
      <td>${esc(c.events_activity || '—')}</td>
      <td style="color:var(--text-3);font-size:11px">${esc(c.experiential_gap || '—')}</td>
      <td>${badge(c.threat_level_to_brand, c.threat_level_to_brand === 'HIGH' ? 'red' : c.threat_level_to_brand === 'LOW' ? 'green' : 'amber')}</td>
    </tr>`).join('');
  $('card-competitors').innerHTML = `
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
  $('card-position').innerHTML = `
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
  const campaigns = d.recent_campaigns || [];
  $('card-activity').innerHTML = `
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
  const events = d.events_timeline || [];
  const score  = d.experiential_maturity_score;
  const pct    = score ? (score / 5) * 100 : 0;
  const sColor = score >= 4 ? 'green' : score >= 2 ? '' : 'amber';

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

  $('card-events').innerHTML = `
    <div class="card-head">
      <span class="card-title">Experiential Footprint</span>
      ${score ? `<span style="font-family:var(--mono);font-size:22px;font-weight:700;color:var(--green)">${score}<span style="font-size:12px;color:var(--text-3)">/5</span></span>` : ''}
    </div>
    <div class="card-body">
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

  $('card-people').innerHTML = `
    <div class="card-head"><span class="card-title">Decision Makers & Contact Intelligence</span>
      ${people.length ? `<span class="badge indigo">${people.length} stakeholder${people.length !== 1 ? 's' : ''}</span>` : ''}
    </div>
    <div class="card-body">
      <div class="people-grid">
        ${cards || '<div style="color:var(--text-3);padding:16px 0;font-family:var(--mono);font-size:12px">No decision makers found</div>'}
      </div>
      ${p10.email_pattern ? `<div class="email-pattern-bar">
        Email pattern: <strong style="color:var(--indigo)">${esc(p10.email_pattern)}@${esc(p10.domain || '?')}</strong>
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

  $('card-tracking').innerHTML = `
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
  const icpCol = icp >= 70 ? '#10B981' : icp >= 40 ? '#F59E0B' : '#EF4444';

  function svgGauge(pct, colour, size = 80) {
    const r = 28, cx = size / 2, cy = size / 2 + 8, circ = Math.PI * r;
    const offset = circ * (1 - pct / 100);
    return `<svg width="${size}" height="${Math.round(size * 0.7)}" viewBox="0 0 ${size} ${Math.round(size * 0.7)}">
      <path d="M${cx - r},${cy} A${r},${r},0,0,1,${cx + r},${cy}" fill="none" stroke="#1F2937" stroke-width="6"/>
      <path d="M${cx - r},${cy} A${r},${r},0,0,1,${cx + r},${cy}" fill="none" stroke="${colour}" stroke-width="6"
        stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}" stroke-linecap="round"/>
      <text x="${cx}" y="${cy - 2}" text-anchor="middle" fill="${colour}" font-size="16" font-weight="700" font-family="'Inter',monospace">${pct}</text>
    </svg>`;
  }

  function pdfSection(title, content) {
    return `<div style="margin-bottom:28px;page-break-inside:avoid">
      <div style="font-family:monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#00E676;border-bottom:1px solid #1F2937;padding-bottom:6px;margin-bottom:14px">${e(title)}</div>
      ${content}</div>`;
  }

  function pdfKV(k, v, col) {
    if (v == null || v === '') return '';
    return `<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1F2937;font-size:12px">
      <span style="color:#6B7280;font-family:monospace;font-size:10px;text-transform:uppercase">${e(k)}</span>
      <span style="color:${col || '#F9FAFB'};text-align:right;max-width:60%">${e(v)}</span>
    </div>`;
  }

  const colors = p02.primary_colors || p02.extracted_colors || [];
  const colSwatches = colors.slice(0, 8).map(c =>
    `<div style="width:28px;height:28px;border-radius:4px;background:${e(c)};display:inline-block;margin-right:4px;border:1px solid rgba(255,255,255,.1)" title="${e(c)}"></div>`).join('');

  const compRows = (p04.competitors || []).slice(0, 5).map(c => `
    <tr>
      <td style="font-weight:600;color:#00E676;font-family:monospace;font-size:11px;padding:7px 8px;border-bottom:1px solid #1F2937">${e(c.name || '')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1F2937;font-size:11px;color:#9CA3AF">${e(c.brand_positioning || '—')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1F2937;font-size:11px">${e(c.events_activity || '—')}</td>
      <td style="padding:7px 8px;border-bottom:1px solid #1F2937;font-size:11px;color:#6B7280">${e(c.experiential_gap || '—')}</td>
    </tr>`).join('');

  const eventCards = (p06.events_timeline || []).slice(0, 8).map(ev => `
    <div style="padding:10px 12px;background:#111827;border:1px solid #1F2937;border-left:3px solid #00E676;border-radius:4px;margin-bottom:8px;page-break-inside:avoid">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px">
        <span style="font-weight:600;font-size:13px">${e(ev.event_name || ev.name || '?')}</span>
        <span style="font-family:monospace;font-size:10px;color:#6B7280">${e(ev.date || ev.year || '')}</span>
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap">
        ${ev.format ? `<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid rgba(59,130,246,.3);color:#3B82F6;border-radius:3px">${e(ev.format)}</span>` : ''}
        ${ev.brand_role ? `<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid rgba(16,185,129,.3);color:#10B981;border-radius:3px">${e(ev.brand_role)}</span>` : ''}
        ${ev.location ? `<span style="font-family:monospace;font-size:9px;padding:1px 6px;border:1px solid #374151;color:#9CA3AF;border-radius:3px">📍 ${e(ev.location)}</span>` : ''}
      </div>
    </div>`).join('');

  const peopleCards = (p09.buying_committee || []).slice(0, 4).map(p => {
    const ct = (p10.contacts || []).find(c => c.name === p.name) || {};
    return `
    <div style="padding:14px;background:#111827;border:1px solid #1F2937;border-radius:8px;margin-bottom:10px;page-break-inside:avoid">
      <div style="font-weight:700;font-size:14px;margin-bottom:2px">${e(p.name || '—')}</div>
      <div style="font-size:11px;color:#9CA3AF;margin-bottom:10px">${e(p.title || '—')}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
        ${p.outreach_priority === 'PRIMARY' ? `<span style="font-family:monospace;font-size:9px;padding:2px 7px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);color:#10B981;border-radius:100px">PRIMARY</span>` : ''}
        ${ct.email ? `<span style="font-family:monospace;font-size:9px;padding:2px 7px;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25);color:#3B82F6;border-radius:100px">✉ ${e(ct.email)}</span>` : ''}
        ${p.decision_relevance_score ? `<span style="font-family:monospace;font-size:9px;padding:2px 7px;border:1px solid #374151;color:#6B7280;border-radius:100px">Score ${p.decision_relevance_score}/5</span>` : ''}
      </div>
      ${p.personalisation_hook ? `<div style="font-size:11px;color:#6B7280;font-style:italic;margin-top:4px">${e(p.personalisation_hook)}</div>` : ''}
    </div>`;
  }).join('');

  // Build outreach sequences — multi-person
  let sequences = (p11.contacts_sequences || []).filter(s => s.contact && s.sequence);
  if (!sequences.length && p11.outreach_sequence) {
    sequences = [{ contact: p11.primary_contact || {}, sequence: p11.outreach_sequence, personalisation_vars: p11.personalisation_variables_used || {} }];
  }

  const outreachSections = sequences.slice(0, 4).map((item, idx) => {
    const c    = item.contact  || {};
    const seq  = item.sequence || {};
    const touches = Object.entries(seq)
      .filter(([, t]) => t && typeof t === 'object')
      .sort(([a], [b]) => (parseInt(a.replace(/\D/g,''))||0) - (parseInt(b.replace(/\D/g,''))||0));

    const touchCards = touches.map(([key, t]) => {
      const isLI = (t.channel || '').toLowerCase() === 'linkedin';
      return `
      <div style="padding:14px;background:#111827;border:1px solid #1F2937;border-left:3px solid ${isLI ? '#3B82F6' : '#00E676'};border-radius:4px;margin-bottom:10px;page-break-inside:avoid">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px">
          <span style="font-family:monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:${isLI ? '#3B82F6' : '#00E676'}">${e(t.channel || key)}</span>
          <span style="font-family:monospace;font-size:10px;color:#6B7280">Day ${t.send_day || '—'}</span>
        </div>
        ${t.subject_line ? `<div style="font-weight:600;font-size:13px;margin-bottom:8px">📧 ${e(t.subject_line)}</div>` : ''}
        <div style="font-size:12px;color:#9CA3AF;line-height:1.75;white-space:pre-line">${e(t.message || '—')}</div>
      </div>`;
    }).join('');

    return `
    <div style="margin-bottom:28px;page-break-before:${idx > 0 ? 'always' : 'avoid'}">
      <div style="font-family:monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#00E676;border-bottom:1px solid #1F2937;padding-bottom:6px;margin-bottom:14px">
        Sequence ${idx + 1} of ${sequences.length} — ${e(c.name || 'Unknown')}
      </div>
      <div style="padding:10px 14px;background:#111827;border:1px solid #1F2937;border-radius:6px;margin-bottom:14px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;font-size:12px">
        <span style="font-weight:700">${e(c.name || '—')}</span>
        ${c.title ? `<span style="color:#9CA3AF">${e(c.title)}</span>` : ''}
        ${c.email ? `<span style="font-family:monospace;font-size:11px;color:#3B82F6">✉ ${e(c.email)}</span>` : ''}
        ${c.outreach_priority === 'PRIMARY' ? `<span style="font-family:monospace;font-size:9px;padding:2px 7px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);color:#10B981;border-radius:100px">PRIMARY</span>` : ''}
      </div>
      ${touchCards}
    </div>`;
  }).join('');

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<title>BrandScope — ${e(data.company_name)}</title>
<style>
  @page { size: A4; margin: 16mm 20mm; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#0B0F1A; color:#F9FAFB; font-family:'Inter',system-ui,sans-serif; font-size:13px; line-height:1.6; }
  .pb { page-break-before: always; }
  @media print { body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }
</style></head><body>

<!-- COVER -->
<div style="min-height:100vh;display:flex;flex-direction:column;justify-content:space-between;padding:48px 40px;background:#0B0F1A">
  <div>
    <div style="font-family:monospace;font-size:11px;letter-spacing:.2em;color:#00E676;text-transform:uppercase;margin-bottom:10px">◈ BrandScope Intelligence Report</div>
    <h1 style="font-size:40px;font-weight:700;color:#F9FAFB;letter-spacing:-.03em;margin-bottom:6px">${e(data.company_name)}</h1>
    <div style="font-family:monospace;font-size:13px;color:#6B7280;margin-bottom:40px">${e(data.category || '')}</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;max-width:580px">
      <div style="background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center">
        ${svgGauge(icp, icpCol, 80)}
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#6B7280;text-transform:uppercase;margin-top:4px">ICP Score</div>
      </div>
      <div style="background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:26px;font-weight:700;font-family:monospace;color:${p08.overall_verdict === 'GREEN' ? '#10B981' : p08.overall_verdict === 'RED' ? '#EF4444' : '#F59E0B'};margin-bottom:4px">${e(p08.overall_verdict || '—')}</div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#6B7280;text-transform:uppercase">Watchout</div>
      </div>
      <div style="background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:26px;font-weight:700;font-family:monospace;color:#10B981;margin-bottom:4px">${e(p06.experiential_maturity_score || '—')}<span style="font-size:13px;color:#6B7280">/5</span></div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#6B7280;text-transform:uppercase">Events</div>
      </div>
      <div style="background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:26px;font-weight:700;font-family:monospace;color:#10B981;margin-bottom:4px">${p09.total_contacts_found || (p09.buying_committee || []).length || 0}</div>
        <div style="font-family:monospace;font-size:9px;letter-spacing:.1em;color:#6B7280;text-transform:uppercase">Contacts</div>
      </div>
    </div>
  </div>
  <div style="font-family:monospace;font-size:10px;color:#374151;letter-spacing:.06em">
    ${e(data.run_id || '')} · Generated ${new Date().toLocaleDateString('en-GB', {day:'numeric', month:'long', year:'numeric'})} · ${data.total_elapsed?.toFixed(1) || '?'}s · 12 pipelines
  </div>
</div>

<!-- COMPANY + BRAND -->
<div class="pb" style="padding:40px">
  ${pdfSection('Company Overview', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        ${pdfKV('Business Model', p01.business_model)}
        ${pdfKV('Industry', p01.industry_vertical)}
        ${pdfKV('Founded', p01.founding_year)}
        ${pdfKV('Employees', p01.employee_count_range)}
        ${pdfKV('Funding', p01.funding_status)}
        ${pdfKV('Revenue', p01.revenue_range)}
        ${pdfKV('HQ', p01.hq_city ? p01.hq_city + ', ' + (p01.geography || '') : p01.geography)}
        ${pdfKV('Readiness', p01.experiential_readiness)}
        ${pdfKV('Service', p01.recommended_service)}
      </div>
      <div>
        <div style="font-size:12px;color:#9CA3AF;line-height:1.75;padding:14px;background:#111827;border-radius:6px;border:1px solid #1F2937">${e(p01.company_narrative || 'No narrative.')}</div>
      </div>
    </div>
  `)}

  ${pdfSection('Brand Identity', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        ${colSwatches ? `<div style="margin-bottom:12px">${colSwatches}</div>` : ''}
        ${pdfKV('Primary Font', (p02.primary_fonts || p02.extracted_fonts || [])[0])}
        ${pdfKV('Brand Tone', p02.brand_tone)}
        ${pdfKV('Visual Style', p02.visual_style)}
        ${pdfKV('Brand Maturity', p02.brand_maturity)}
        ${pdfKV('Tagline', p02.tagline)}
      </div>
      <div>
        ${(p02.brand_voice_keywords || []).length ? `<div style="margin-bottom:10px"><div style="font-family:monospace;font-size:9px;color:#6B7280;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">Voice Keywords</div><div style="display:flex;flex-wrap:wrap;gap:4px">${p02.brand_voice_keywords.map(k => `<span style="font-family:monospace;font-size:10px;padding:2px 7px;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.25);color:#00E676;border-radius:100px">${e(k)}</span>`).join('')}</div></div>` : ''}
        ${p02.experiential_design_angle ? `<div style="font-size:12px;color:#9CA3AF;line-height:1.65;padding:12px;background:#111827;border:1px solid #1F2937;border-radius:6px;margin-top:8px">🎨 ${e(p02.experiential_design_angle)}</div>` : ''}
      </div>
    </div>
  `)}
</div>

<!-- MARKET + COMPETITORS -->
<div class="pb" style="padding:40px">
  ${pdfSection('Market Position & Reputation', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        <div style="font-family:monospace;font-size:9px;color:#6B7280;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">Market Position</div>
        ${pdfKV('Share of Voice', p03.share_of_voice_level)}
        ${pdfKV('Sentiment', p03.brand_sentiment)}
        ${pdfKV('Perception Gap', p03.perception_gap_score ? p03.perception_gap_score + '/5' : null)}
        ${p03.market_position_summary ? `<div style="margin-top:10px;font-size:11px;color:#6B7280;line-height:1.65">${e(p03.market_position_summary)}</div>` : ''}
      </div>
      <div>
        <div style="font-family:monospace;font-size:9px;color:#6B7280;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">Reputation</div>
        ${pdfKV('Score', p07.overall_reputation_score ? p07.overall_reputation_score + '/100' : null)}
        ${pdfKV('Label', p07.reputation_label)}
        ${pdfKV('NPS Signal', p07.nps_signal)}
        ${pdfKV('Community', p07.brand_community_strength)}
        ${p07.reputation_opportunity ? `<div style="margin-top:10px;font-size:11px;color:#10B981;padding:8px 10px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);border-radius:4px">🎯 ${e(p07.reputation_opportunity)}</div>` : ''}
      </div>
    </div>
  `)}

  ${pdfSection('Competitor Mapping', `
    ${compRows ? `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">
      <thead><tr>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:6px 8px;text-align:left;border-bottom:1px solid #1F2937">Brand</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:6px 8px;text-align:left;border-bottom:1px solid #1F2937">Positioning</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:6px 8px;text-align:left;border-bottom:1px solid #1F2937">Events</th>
        <th style="font-family:monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;padding:6px 8px;text-align:left;border-bottom:1px solid #1F2937">Their Gap</th>
      </tr></thead>
      <tbody>${compRows}</tbody></table></div>` : '<div style="color:#6B7280;font-family:monospace;font-size:12px">No competitor data</div>'}
    ${p04.experiential_white_space ? `<div style="margin-top:12px;font-size:12px;color:#00E676;padding:10px 12px;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.25);border-radius:4px">🎯 White space: ${e(p04.experiential_white_space)}</div>` : ''}
  `)}
</div>

<!-- EVENTS -->
<div class="pb" style="padding:40px">
  ${pdfSection('Experiential Footprint', `
    <div style="display:grid;grid-template-columns:160px 1fr;gap:24px;margin-bottom:20px">
      <div style="text-align:center;padding:16px;background:#111827;border:1px solid #1F2937;border-radius:8px">
        <div style="font-size:40px;font-weight:700;font-family:monospace;color:#10B981">${p06.experiential_maturity_score || '?'}</div>
        <div style="font-size:10px;font-family:monospace;color:#6B7280;text-transform:uppercase;letter-spacing:.1em">/5 Maturity</div>
      </div>
      <div>
        ${pdfKV('Events Found', (p06.events_timeline || []).length || null)}
        ${pdfKV('Frequency', p06.events_frequency)}
        ${pdfKV('Last Event', p06.last_event_months_ago != null ? p06.last_event_months_ago + ' months ago' : null)}
        ${pdfKV('Geography', (p06.geography_of_events || []).join(' · ') || null)}
        ${p06.pitch_angle ? `<div style="margin-top:10px;font-size:12px;color:#00E676;padding:8px 10px;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.25);border-radius:4px">🎯 ${e(p06.pitch_angle)}</div>` : ''}
      </div>
    </div>
    ${eventCards || '<div style="color:#6B7280;font-family:monospace;font-size:12px;padding:16px 0">No confirmed events found</div>'}
    ${(p06.formats_missing || []).length ? `<div style="margin-top:12px;padding:10px 12px;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);border-radius:4px;font-size:11px;color:#F59E0B">📌 Missing formats: ${e(p06.formats_missing.join(' · '))}</div>` : ''}
  `)}
</div>

<!-- DECISION MAKERS -->
<div class="pb" style="padding:40px">
  ${pdfSection('Decision Makers & Contact Intelligence', `
    ${peopleCards || '<div style="color:#6B7280;font-family:monospace;font-size:12px">No decision makers found</div>'}
    ${p10.email_pattern ? `<div style="margin-top:12px;padding:10px 12px;background:#111827;border:1px solid #1F2937;border-radius:4px;font-family:monospace;font-size:11px;color:#6B7280">Email pattern: <span style="color:#00E676">${e(p10.email_pattern)}@${e(p10.domain || '?')}</span> · ${p10.verified_emails || 0} verified · ${p10.inferred_emails || 0} inferred</div>` : ''}
  `)}

  ${pdfSection('Strategic Watchouts', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        ${pdfKV('Verdict', p08.overall_verdict, p08.overall_verdict === 'GREEN' ? '#10B981' : p08.overall_verdict === 'RED' ? '#EF4444' : '#F59E0B')}
        ${pdfKV('Timing', p08.timing_recommendation)}
        ${pdfKV('Tone', p08.pitch_tone_adjustment)}
        ${p08.verdict_reasoning ? `<div style="margin-top:10px;font-size:11px;color:#9CA3AF;line-height:1.65">${e(p08.verdict_reasoning)}</div>` : ''}
      </div>
      <div>
        ${(p08.financial_distress_signals || []).length ? `<div style="margin-bottom:12px">${p08.financial_distress_signals.slice(0, 2).map(s => `<div style="font-size:11px;color:#9CA3AF;padding:5px 8px;border-left:2px solid #EF4444;margin-bottom:4px">${e(s)}</div>`).join('')}</div>` : ''}
        ${(p08.leadership_changes || []).length ? p08.leadership_changes.map(lc => `<div style="font-size:11px;color:#9CA3AF;padding:5px 8px;border-left:2px solid #10B981;margin-bottom:4px"><span style="color:#10B981">${e(lc.role)}</span>: ${e(lc.change)}</div>`).join('') : ''}
      </div>
    </div>
  `)}
</div>

<!-- OUTREACH SEQUENCES -->
${outreachSections ? `<div class="pb" style="padding:40px">
  <div style="font-family:monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#00E676;border-bottom:1px solid #1F2937;padding-bottom:6px;margin-bottom:20px">4-Touch Outreach Sequences — ${sequences.length} Contact${sequences.length !== 1 ? 's' : ''}</div>
  ${outreachSections}
</div>` : ''}

<!-- FOOTER -->
<div style="padding:24px 40px;border-top:1px solid #1F2937;font-family:monospace;font-size:10px;color:#374151;display:flex;justify-content:space-between">
  <span>BrandScope · Brand Intelligence System</span>
  <span>${e(data.run_id || '')} · ${data.total_elapsed?.toFixed(1) || '?'}s · 12 pipelines</span>
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
