/* ─────────────────────────────────────────────
   BrandScope — Frontend Application
   Connects to FastAPI at /api or localhost:8000
   ───────────────────────────────────────────── */

'use strict';

// ── CONFIG ──────────────────────────────────────
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : '';   // same-origin when served by FastAPI

const POLL_INTERVAL = 3000; // ms
let currentRunId   = null;
let pollTimer      = null;
let currentReport  = null;

// ── PIPELINE LABELS ─────────────────────────────
const PIPELINES = [
  { id: 'p01', name: 'Company Overview' },
  { id: 'p02', name: 'Brand Identity'   },
  { id: 'p03', name: 'Market Position'  },
  { id: 'p04', name: 'Competitor Map'   },
  { id: 'p05', name: 'Brand Activity'   },
  { id: 'p06', name: 'Events Footprint' },
  { id: 'p07', name: 'Reputation'       },
  { id: 'p08', name: 'Watchouts'        },
  { id: 'p09', name: 'Decision Makers'  },
  { id: 'p10', name: 'Contact Intel'    },
  { id: 'p11', name: 'Outreach Drafts'  },
  { id: 'p12', name: 'Tracking Setup'   },
];

// ── UTILITY ─────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => $( id)?.classList.remove('hidden');
const hide = id => $( id)?.classList.add('hidden');

function toast(msg, duration = 3000) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), duration);
}

function fmt(val) {
  if (val === null || val === undefined) return '<span style="color:var(--text-dim)">—</span>';
  if (typeof val === 'boolean') return val ? '✓' : '✗';
  return String(val);
}

// ── NAVIGATION ──────────────────────────────────
function showAnalyse() {
  show('analyseForm'); hide('progressSection'); hide('resultsSection'); hide('reportsSection');
  document.querySelector('.nav-link[href="#analyse"]').classList.add('active');
  document.querySelector('.nav-link[onclick="showReports()"]').classList.remove('active');
}
function showReports() {
  hide('analyseForm'); hide('progressSection'); hide('resultsSection'); show('reportsSection');
  document.querySelector('.nav-link[href="#analyse"]').classList.remove('active');
  document.querySelector('.nav-link[onclick="showReports()"]').classList.add('active');
  loadReports();
}

// ── TAB SWITCHING ────────────────────────────────
document.addEventListener('click', e => {
  if (!e.target.classList.contains('tab')) return;
  const id = e.target.dataset.tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  $(`panel-${id}`)?.classList.add('active');
});

// ── FORM SUBMIT ──────────────────────────────────
$('inputForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = $('submitBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Starting analysis…';

  const payload = {
    company_name: $('company_name').value.trim(),
    company_url:  $('company_url').value.trim(),
    category:     $('category').value.trim(),
  };

  try {
    const res  = await fetch(`${API_BASE}/analyse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    startPolling(data.job_id, payload.company_name);
  } catch (err) {
    toast(`⚠ Could not connect to API: ${err.message}`, 5000);
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">⚡</span> Run Full Analysis';
  }
});

// ── PROGRESS PIPELINE GRID ───────────────────────
function buildPipelineGrid() {
  const grid = $('pipelineGrid');
  grid.innerHTML = PIPELINES.map(p => `
    <div class="pipeline-item" id="pipe-${p.id}">
      <span class="pipeline-status" id="pipe-${p.id}-icon">⏸</span>
      <span class="pipeline-name">${p.name}</span>
    </div>`).join('');
}

function markPipeline(id, state /* running | done | error */) {
  const el   = $(`pipe-${id}`);
  const icon = $(`pipe-${id}-icon`);
  if (!el) return;
  el.className = `pipeline-item pipeline-item--${state}`;
  const icons = { running: '⚙', done: '✓', error: '✗' };
  icon.textContent = icons[state] || '⏸';
}

// ── POLLING ──────────────────────────────────────
function startPolling(jobId, companyName) {
  hide('analyseForm');
  show('progressSection');
  $('progressCompany').textContent = companyName;
  buildPipelineGrid();
  $('progressBar').style.width = '5%';

  let step = 0;
  pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`${API_BASE}/status/${jobId}`);
      const data = await res.json();
      updateProgress(data, step++);
      if (data.status === 'complete' || data.status === 'error') {
        clearInterval(pollTimer);
        if (data.status === 'complete') {
          $('progressBar').style.width = '100%';
          setTimeout(() => loadReport(data.run_id), 600);
        } else {
          toast('Analysis encountered errors — partial results may be available.', 6000);
          if (data.run_id) loadReport(data.run_id);
        }
      }
    } catch (err) {
      // silent retry
    }
  }, POLL_INTERVAL);
}

function updateProgress(data, step) {
  const completed = data.completed_pipelines || [];
  const running   = data.current_pipeline   || null;
  const total     = 12;
  const pct       = Math.max(5, Math.min(95, (completed.length / total) * 100));
  $('progressBar').style.width = `${pct}%`;

  PIPELINES.forEach(p => {
    if (completed.includes(p.id)) markPipeline(p.id, 'done');
    else if (running === p.id)    markPipeline(p.id, 'running');
  });
}

// ── LOAD REPORT ──────────────────────────────────
async function loadReport(runId) {
  try {
    const res  = await fetch(`${API_BASE}/report/${runId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentReport = data;
    currentRunId  = runId;
    renderReport(data);
    hide('progressSection');
    show('resultsSection');
    // reset form button
    const btn = $('submitBtn');
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">⚡</span> Run Full Analysis';
  } catch (err) {
    toast(`Could not load report: ${err.message}`, 6000);
  }
}

// ── RENDER REPORT ────────────────────────────────
function renderReport(data) {
  const r = data.results || {};

  // run id tag
  $('resultsTitle').textContent = data.company_name || 'Brand Report';
  $('resultsRunId').textContent = data.run_id || '';

  // ICP banner
  const icp = r.p01?.data?.icp_fit_score ?? r.p01?.icp_fit_score ?? '—';
  $('icpScore').textContent = icp;
  let verdictClass = 'mid';
  let verdictText  = 'Medium Fit';
  if (typeof icp === 'number') {
    if (icp >= 75) { verdictClass = 'high'; verdictText = 'Strong ICP Fit ✓'; }
    else if (icp < 40) { verdictClass = 'low'; verdictText = 'Low Fit'; }
  }
  const vEl = $('icpVerdict');
  vEl.textContent  = verdictText;
  vEl.className    = `icp-verdict icp-verdict--${verdictClass}`;

  const model = r.p01?.data?.business_model || '';
  const svc   = r.p01?.data?.recommended_service || '';
  $('icpSub').textContent = [model, svc].filter(Boolean).join(' · ') || 'Analysis complete';

  // render each card
  renderCompanyCard(r.p01?.data || {});
  renderMarketCard(r.p03?.data || {});
  renderReputationCard(r.p07?.data || {});
  renderWatchoutsCard(r.p08?.data || {});
  renderColorsCard(r.p02?.data || {});
  renderVoiceCard(r.p02?.data || {});
  renderCompetitorsCard(r.p04?.data || {});
  renderPositionCard(r.p03?.data || {});
  renderActivityCard(r.p05?.data || {});
  renderEventsCard(r.p06?.data || {});
  renderPeopleCard(r.p09?.data || {}, r.p10?.data || {});
  renderOutreachCard(r.p11?.data || {});
  renderTrackingCard(r.p12?.data || {});
}

// ─── INDIVIDUAL CARD RENDERERS ──────────────────

function field(key, val) {
  return `<div class="field-row"><span class="field-key">${key}</span><span class="field-val">${fmt(val)}</span></div>`;
}

function renderCompanyCard(d) {
  $('card-company').innerHTML = `
    <div class="card-title">Company Overview</div>
    <div class="card-body">
      ${field('Business Model',  d.business_model)}
      ${field('Employees',       d.employee_count)}
      ${field('Founded',         d.founding_year)}
      ${field('Funding Stage',   d.funding_stage)}
      ${field('Experiential Readiness', d.experiential_readiness)}
      ${field('Recommended Service',    d.recommended_service)}
    </div>`;
}

function renderMarketCard(d) {
  $('card-market').innerHTML = `
    <div class="card-title">Market Snapshot</div>
    <div class="card-body">
      ${field('Share of Voice',      d.share_of_voice_level)}
      ${field('Brand Sentiment',     d.brand_sentiment)}
      ${field('Perception Gap',      d.perception_gap_score ? `${d.perception_gap_score}/5` : '—')}
      ${field('Sentiment Shift',     d.recent_sentiment_shift)}
      ${d.pitch_implication ? `<div style="margin-top:12px;font-size:13px;color:var(--text-muted);border-top:1px solid var(--border);padding-top:12px;">${d.pitch_implication}</div>` : ''}
    </div>`;
}

function renderReputationCard(d) {
  $('card-reputation').innerHTML = `
    <div class="card-title">Reputation Research</div>
    <div class="card-body">
      ${field('Reputation Score',   d.overall_reputation_score ? `${d.overall_reputation_score}/5` : '—')}
      ${field('Community Strength', d.brand_community_strength)}
      ${d.reddit_key_themes?.length ? field('Reddit Themes', d.reddit_key_themes.join(', ')) : ''}
      ${d.common_customer_complaints?.length ? `<div class="field-row"><span class="field-key">Top Complaints</span><span class="field-val" style="font-size:12px">${d.common_customer_complaints.slice(0,2).join(' · ')}</span></div>` : ''}
      ${d.reputation_opportunity ? `<div style="margin-top:12px;font-size:12px;color:var(--green);border-top:1px solid var(--border);padding-top:10px;">💡 ${d.reputation_opportunity}</div>` : ''}
    </div>`;
}

function renderWatchoutsCard(d) {
  const v = d.overall_verdict || 'GREEN';
  $('card-watchouts').innerHTML = `
    <div class="card-title">Strategic Watchouts</div>
    <div class="card-body">
      <div style="margin-bottom:14px"><span class="verdict verdict-${v}">${v}</span></div>
      ${field('Timing',      d.timing_recommendation)}
      ${field('Tone Adjust', d.pitch_tone_adjustment)}
      ${d.leadership_changes?.length ? `<div class="field-row"><span class="field-key">Leadership Changes</span><span class="field-val" style="font-size:12px">${d.leadership_changes.map(l => l.name).join(', ')}</span></div>` : ''}
    </div>`;
}

function renderColorsCard(d) {
  const colors = d.primary_colors || [];
  const swatches = colors.slice(0,10).map(c =>
    `<div class="swatch" style="background:${c}" title="${c}"></div>`
  ).join('');
  $('card-colors').innerHTML = `
    <div class="card-title">Brand Colors</div>
    <div class="card-body">
      ${swatches ? `<div class="swatch-row">${swatches}</div>` : '<span style="color:var(--text-dim)">No colors extracted</span>'}
      ${d.brand_tone ? field('Brand Tone', d.brand_tone) : ''}
      ${d.experiential_design_angle ? `<div style="margin-top:12px;font-size:12px;color:var(--text-muted);border-top:1px solid var(--border);padding-top:10px;">🎨 ${d.experiential_design_angle}</div>` : ''}
    </div>`;
}

function renderVoiceCard(d) {
  const kw = d.brand_voice_keywords || [];
  $('card-voice').innerHTML = `
    <div class="card-title">Brand Voice & Fonts</div>
    <div class="card-body">
      ${d.primary_fonts?.length ? field('Primary Fonts', d.primary_fonts.join(', ')) : ''}
      ${kw.length ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0">${kw.map(k => `<span class="badge badge--purple">${k}</span>`).join('')}</div>` : ''}
      ${d.missing_brand_elements?.length ? field('Missing Elements', d.missing_brand_elements.join(', ')) : ''}
    </div>`;
}

function renderCompetitorsCard(d) {
  const comps = d.competitors || [];
  const rows  = comps.slice(0,5).map(c => `
    <tr>
      <td><strong>${c.name || '—'}</strong></td>
      <td>${c.brand_positioning || '—'}</td>
      <td>${c.events_activity || '—'}</td>
      <td>${c.experiential_gap || '—'}</td>
    </tr>`).join('');
  $('card-competitors').innerHTML = `
    <div class="card-title">Competitor Mapping</div>
    <div class="card-body">
      ${rows ? `<table class="comp-table"><thead><tr><th>Brand</th><th>Positioning</th><th>Events</th><th>Gap</th></tr></thead><tbody>${rows}</tbody></table>` : '<span style="color:var(--text-dim)">No competitors identified</span>'}
      ${d.experiential_white_space ? `<div style="margin-top:14px;font-size:12px;color:var(--accent);border-top:1px solid var(--border);padding-top:12px;">🎯 White space: ${d.experiential_white_space}</div>` : ''}
    </div>`;
}

function renderPositionCard(d) {
  $('card-position').innerHTML = `
    <div class="card-title">Market Position</div>
    <div class="card-body">
      ${field('Share of Voice',  d.share_of_voice_level)}
      ${field('Sentiment',       d.brand_sentiment)}
      ${field('Perception Gap',  d.perception_gap_score ? `${d.perception_gap_score}/5` : '—')}
      ${field('Sentiment Shift', d.recent_sentiment_shift)}
      ${d.pitch_implication ? `<div style="margin-top:12px;font-size:13px;color:var(--text-muted);border-top:1px solid var(--border);padding-top:12px;">${d.pitch_implication}</div>` : ''}
    </div>`;
}

function renderActivityCard(d) {
  const campaigns = d.recent_campaigns || [];
  $('card-activity').innerHTML = `
    <div class="card-title">Brand Activity</div>
    <div class="card-body">
      ${field('Content Cadence',   d.social_content_cadence)}
      ${field('Seasonal Pattern',  d.seasonal_pattern)}
      ${field('Budget Signal',     d.budget_signal)}
      ${field('Opportunity Window',d.upcoming_opportunity_window)}
      ${campaigns.length ? `<div style="margin-top:12px;font-size:12px;color:var(--text-muted)">Recent campaigns: ${campaigns.slice(0,3).map(c=>c.name||c).join(' · ')}</div>` : ''}
    </div>`;
}

function renderEventsCard(d) {
  const events = d.events_timeline || [];
  const score  = d.experiential_maturity_score;
  const cards  = events.slice(0,6).map(ev => `
    <div style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:14px;margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong style="font-size:14px">${ev.event_name || ev.name || 'Untitled Event'}</strong>
        ${ev.year ? `<span style="font-size:11px;color:var(--text-muted);font-family:var(--font-mono)">${ev.year}</span>` : ''}
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        ${ev.format  ? `<span class="badge badge--blue">${ev.format}</span>` : ''}
        ${ev.scale   ? `<span class="badge">${ev.scale}</span>` : ''}
        ${ev.location? `<span class="badge">📍 ${ev.location}</span>` : ''}
        ${ev.quality ? `<span class="badge badge--amber">${ev.quality}</span>` : ''}
      </div>
    </div>`).join('');

  $('card-events').innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="card-title" style="margin:0">Experiential Footprint</div>
      ${score ? `<div style="font-size:32px;font-weight:700;color:var(--accent);font-family:var(--font-mono)">${score}<span style="font-size:14px;color:var(--text-muted)">/5</span></div>` : ''}
    </div>
    ${cards || '<span style="color:var(--text-dim)">No events found</span>'}
    ${d.formats_missing?.length ? `<div style="margin-top:16px;padding:14px;background:var(--bg-input);border:1px solid var(--border);border-radius:6px;font-size:13px">
      <span style="color:var(--amber)">📌 Missing formats:</span> ${d.formats_missing.join(', ')}
    </div>` : ''}
    ${d.opening_line_for_pitch ? `<div style="margin-top:12px;padding:14px;background:var(--accent-glow);border:1px solid rgba(124,92,252,0.35);border-radius:6px;font-size:13px;font-style:italic">"${d.opening_line_for_pitch}"</div>` : ''}
  `;
}

function renderPeopleCard(p09, p10) {
  const people = p09.buying_committee || [];
  const contacts = p10.contact_cards  || [];

  const contactMap = {};
  contacts.forEach(c => { contactMap[c.name] = c; });

  const cards = people.map(p => {
    const ct = contactMap[p.name] || {};
    const email = ct.email || '—';
    const emailConf = ct.email_confidence ? `${ct.email_confidence}%` : '';
    const score = p.decision_relevance_score;
    return `
    <div class="person-card">
      <div class="person-name">${p.name || '—'}</div>
      <div class="person-title">${p.title || '—'} ${p.role_type ? `· ${p.role_type}` : ''}</div>
      ${score ? `<div class="score-bar-wrap"><div class="score-bar" style="width:${score*20}%"></div></div><div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">Decision relevance ${score}/5</div>` : ''}
      <div class="person-meta">
        ${p.outreach_priority === 'HIGH' ? `<span class="badge badge--green">Priority: HIGH</span>` : p.outreach_priority === 'MEDIUM' ? `<span class="badge badge--amber">Priority: MED</span>` : ''}
        ${email !== '—' ? `<span class="badge badge--blue">✉ ${email} ${emailConf ? `(${emailConf})` : ''}</span>` : ''}
        ${ct.recommended_channel ? `<span class="badge">${ct.recommended_channel}</span>` : ''}
      </div>
      ${p.personalisation_hook ? `<div style="margin-top:10px;font-size:12px;color:var(--text-muted)">💡 ${p.personalisation_hook}</div>` : ''}
    </div>`;
  }).join('');

  $('card-people').innerHTML = `
    <div class="card-title">Decision Makers & Contact Intelligence</div>
    ${cards || '<span style="color:var(--text-dim)">No decision makers identified</span>'}
    ${p10.data_disclaimer ? `<div style="margin-top:12px;font-size:11px;color:var(--text-dim);border-top:1px solid var(--border);padding-top:10px;">⚠ ${p10.data_disclaimer}</div>` : ''}
  `;
}

function renderOutreachCard(d) {
  const sequences = d.outreach_sequences || [];
  if (!sequences.length) {
    $('card-outreach').innerHTML = `<div class="card-title">Outreach Sequence</div><span style="color:var(--text-dim)">No sequences generated</span>`;
    return;
  }

  // Show first contact's 4-touch sequence
  const seq = sequences[0];
  const touches = seq.touches || [];
  const touchHtml = touches.map(t => `
    <div class="touch-card">
      <div class="touch-header">
        <span class="touch-label">${t.channel || 'Touch'} ${t.touch_number || ''}</span>
        <span class="touch-day">Day ${t.send_day || '—'}</span>
      </div>
      ${t.subject ? `<div class="touch-subject">📧 ${t.subject}</div>` : ''}
      <div class="touch-body">${t.body || t.message || '—'}</div>
    </div>`).join('');

  $('card-outreach').innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="card-title" style="margin:0">4-Touch Outreach Sequence</div>
      <div style="display:flex;gap:8px">
        ${sequences.map((s,i) => `<button onclick="switchSequence(${i})" class="badge badge--purple" id="seq-btn-${i}">${s.contact_name || `Contact ${i+1}`}</button>`).join('')}
      </div>
    </div>
    <div id="sequence-container">${touchHtml}</div>
    ${d.global_personalisation_context ? `<div style="margin-top:16px;padding:14px;background:var(--bg-input);border:1px solid var(--border);border-radius:6px;font-size:13px;color:var(--text-muted)">Context used: ${JSON.stringify(d.global_personalisation_context).slice(0,200)}…</div>` : ''}
  `;

  // store for switching
  window._sequences = sequences;
}

window.switchSequence = function(idx) {
  const sequences = window._sequences || [];
  const seq = sequences[idx];
  if (!seq) return;
  const touches = seq.touches || [];
  $('sequence-container').innerHTML = touches.map(t => `
    <div class="touch-card">
      <div class="touch-header">
        <span class="touch-label">${t.channel || 'Touch'} ${t.touch_number || ''}</span>
        <span class="touch-day">Day ${t.send_day || '—'}</span>
      </div>
      ${t.subject ? `<div class="touch-subject">📧 ${t.subject}</div>` : ''}
      <div class="touch-body">${t.body || t.message || '—'}</div>
    </div>`).join('');
};

function renderTrackingCard(d) {
  const entries = d.dashboard_entries || [];
  const rows = entries.map(e => `
    <div class="tracking-row">
      <div>
        <div class="tracking-name">${e.contact_name || '—'}</div>
        <div class="tracking-id">${e.tracking_id?.slice(0,16) || '—'}…</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="badge">${e.status || 'COLD'}</span>
        <span class="badge badge--blue">${e.next_action || ''}</span>
      </div>
      <div class="tracking-score">${e.score ?? 0}</div>
    </div>`).join('');

  $('card-tracking').innerHTML = `
    <div class="card-title">Engagement Tracking Dashboard</div>
    ${rows || '<span style="color:var(--text-dim)">No tracking entries yet</span>'}
    <div style="margin-top:16px;padding:14px;background:var(--bg-input);border:1px solid var(--border);border-radius:6px;font-size:12px;color:var(--text-muted)">
      Scoring: open = 1 · click = 5 · reply = 10 · meeting = 20 &nbsp;|&nbsp;
      HOT ≥ 20 · WARM ≥ 10 · ENGAGED ≥ 3 · OPENED ≥ 1
    </div>
  `;
}

// ── LOAD REPORTS LIST ────────────────────────────
async function loadReports() {
  const grid = $('reportsGrid');
  grid.textContent = 'Loading…';
  try {
    const res  = await fetch(`${API_BASE}/reports`);
    const data = await res.json();
    if (!data.reports?.length) {
      grid.innerHTML = '<div style="color:var(--text-muted);grid-column:1/-1">No past reports found. Run your first analysis above.</div>';
      return;
    }
    grid.innerHTML = data.reports.map(r => `
      <div class="report-card" onclick="loadReport('${r.run_id}').then(()=>{showAnalyse();hide('analyseForm')})">
        <div class="report-company">${r.company_name || r.run_id}</div>
        <div class="report-meta">${r.run_id}</div>
        ${r.icp_fit_score != null ? `<div class="report-score">${r.icp_fit_score}<span style="font-size:14px;color:var(--text-muted)">/100</span></div>` : ''}
      </div>`).join('');
  } catch {
    grid.innerHTML = '<div style="color:var(--red)">Could not load reports — is the API running?</div>';
  }
}

// ── RESET / DOWNLOAD ─────────────────────────────
function resetForm() {
  hide('resultsSection');
  show('analyseForm');
  $('inputForm').reset();
  currentReport = null; currentRunId = null;
}

function downloadReport() {
  if (!currentReport) return;
  const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `${currentRunId || 'report'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// expose globals used in HTML onclick
window.showReports  = showReports;
window.showAnalyse  = showAnalyse;
window.resetForm    = resetForm;
window.downloadReport = downloadReport;
window.loadReport   = loadReport;
window.hide         = hide;
