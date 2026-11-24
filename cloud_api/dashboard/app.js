/* TrueDuck Sentinel community console v0.9.
 * No analytics, remote libraries, dynamic HTML templates, or automatic submission.
 * All report content enters the page through textContent to avoid HTML injection.
 */
'use strict';
const $ = id => document.getElementById(id);
const publicReport = location.pathname === '/report';
let token = publicReport ? '' : (sessionStorage.getItem('scamlensCommunitySession') || '');
let profile = null;
let queue = [];
let selected = null;
const SCREENS = ['overview', 'submit', 'moderation', 'audit'];

function showToast(message, error = false) {
  const node = $('toast');
  node.textContent = message;
  node.className = error ? 'toast error' : 'toast';
  node.hidden = false;
}
function clearToast() { $('toast').hidden = true; }
function element(tag, value, className) {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = String(value);
  if (className) node.className = className;
  return node;
}
function statusNode(value) { return element('span', value, `status ${value}`); }
function button(label, handler, cls = 'small-button') {
  const node = element('button', label, cls);
  node.type = 'button';
  node.addEventListener('click', handler);
  return node;
}
async function api(path, method = 'GET', body) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store', signal: AbortSignal.timeout(12000)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && token && path !== '/v1/auth/login') signOut(false);
    throw new Error(data.detail || `Request failed (HTTP ${response.status})`);
  }
  return data;
}
function openScreen(name) {
  if (!SCREENS.includes(name)) return;
  if (!profile && !(publicReport && name === 'submit')) return;
  if (['moderation', 'audit'].includes(name) && profile.role !== 'owner') return;
  for (const key of SCREENS) $(key + 'Screen').hidden = key !== name;
  document.querySelectorAll('[data-screen]').forEach(node => {
    node.classList.toggle('active', node.dataset.screen === name);
  });
  clearToast();
  if (name === 'moderation') loadModeration();
  if (name === 'audit') loadAudit();
  if (name === 'overview') loadOverview();
}
function displaySession(user) {
  profile = user;
  $('authScreen').hidden = true;
  $('workspace').hidden = false;
  $('sidebar').hidden = false;
  $('logoutButton').hidden = false;
  $('userLabel').textContent = `${user.username} · ${user.role}`;
  document.querySelectorAll('.owner-only').forEach(node => {
    node.hidden = user.role !== 'owner';
  });
  // A user-initiated "Community report" click in Edge can prefill ONLY the hostname.
  const selectedHost = new URLSearchParams(location.search).get('domain');
  if (selectedHost && selectedHost.length <= 253) {
    openScreen('submit');
    $('reportKind').value = 'domain';
    $('reportValue').value = selectedHost;
    history.replaceState(null, '', '/dashboard');
  } else {
    openScreen('overview');
  }
}
function signOut(callApi = true) {
  const oldToken = token;
  if (callApi && oldToken) api('/v1/auth/logout', 'POST').catch(() => {});
  token = '';
  profile = null;
  sessionStorage.removeItem('scamlensCommunitySession');
  $('authScreen').hidden = false;
  $('workspace').hidden = true;
  $('sidebar').hidden = true;
  $('logoutButton').hidden = true;
  $('userLabel').textContent = '';
  $('loginPass').value = '';
  clearToast();
}
async function loadOverview() {
  if (!profile || profile.role !== 'owner') return;
  try {
    const data = await api('/v1/admin/metrics');
    $('metricTotal').textContent = data.total;
    $('metricPending').textContent = data.pending;
    $('metricApproved').textContent = data.approved;
    $('metricPublished').textContent = data.published;
    $('navPending').textContent = data.pending;
    drawBars('typeBars', Object.entries(data.by_kind).map(([name, count]) => ({name, count})));
    drawBars('dailyBars', data.daily.map(x => ({name: x.date.slice(5), count: x.count})));
  } catch (error) { showToast(error.message, true); }
}
function drawBars(id, items) {
  const root = $(id); root.replaceChildren();
  if (!items.length) { root.append(element('p', 'No reports yet.', 'muted')); return; }
  const max = Math.max(1, ...items.map(x => x.count));
  for (const item of items) {
    const row = element('div', undefined, 'bar-row');
    const track = element('div', undefined, 'bar-track');
    const fill = element('div', undefined, 'bar-fill');
    fill.style.width = `${Math.max(2, item.count / max * 100)}%`;
    track.append(fill);
    row.append(element('span', item.name), track, element('span', item.count, 'bar-value'));
    root.append(row);
  }
}
async function loadModeration() {
  if (profile?.role !== 'owner') return;
  try {
    const data = await api('/v1/admin/reports');
    queue = data.records;
    $('navPending').textContent = queue.filter(x => x.status === 'pending').length;
    const filter = $('moderationFilter').value;
    const root = $('moderationList'); root.replaceChildren();
    const visible = queue.filter(x => filter === 'all' || x.status === filter);
    if (!visible.length) { root.append(element('p', 'Nothing in this view yet.', 'muted')); return; }
    for (const report of visible) {
      const card = element('article', undefined, 'report-card');
      const header = element('div', undefined, 'row');
      const title = element('div');
      title.append(element('h3', `${report.kind.toUpperCase()} · ${report.value}`),
                   element('small', `Report #${report.id} · ${report.created_at.slice(0, 16)}`));
      const state = element('div'); state.append(statusNode(report.published ? 'published' : report.status));
      header.append(title, state); card.append(header);
      card.append(element('p', report.details));
      if (report.evidence_ref) card.append(element('p', `Reporter reference: ${report.evidence_ref}`));
      if (report.review_note) card.append(element('p', `Owner review: ${report.review_note}`));
      const actions = element('div', undefined, 'actions');
      actions.append(button('Review', () => openReview(report)));
      if (report.status === 'approved' && ['domain', 'url'].includes(report.kind) && !report.published) {
        actions.append(button('Publish indicator', async () => {
          if (!confirm(`Publish ${report.value} to the public intelligence feed? Review the evidence before confirming.`)) return;
          await ownerAction(`/v1/admin/reports/${report.id}/publish`);
        }, 'primary'));
      }
      if (report.published) actions.append(button('Retract', async () => {
        if (!confirm(`Remove ${report.value} from the public feed?`)) return;
        await ownerAction(`/v1/admin/reports/${report.id}/retract`);
      }));
      if (report.status === 'approved' && ['email','phone'].includes(report.kind)) {
        // Contact lookup is never enabled automatically after approval.
        actions.append(button(report.lookup_visible ? 'Disable public lookup' : 'Enable contact lookup', async () => {
          const enabled = !report.lookup_visible;
          if (!confirm(enabled
            ? 'Make this exact contact searchable without login? Review evidence and privacy rights first. The address/number will NOT appear in the downloadable public feed.'
            : 'Stop returning matches for this contact in anonymous lookup?')) return;
          try {
            await api(`/v1/admin/reports/${report.id}/lookup-access`, 'POST', {enabled});
            await loadModeration();
            showToast(enabled ? 'Contact is now eligible for exact-match lookups.' : 'Contact removed from public lookups.');
          } catch (error) { showToast(error.message, true); }
        }, report.lookup_visible ? 'small-button' : 'primary'));
      }
      card.append(actions); root.append(card);
    }
  } catch (error) { showToast(error.message, true); }
}
function openReview(report) {
  selected = report;
  $('selectedReport').textContent = `${report.kind}: ${report.value} | Report: ${report.details} | Evidence: ${report.evidence_ref || 'not supplied'}`;
  $('decisionValue').value = report.status === 'pending' ? 'approved' : report.status;
  $('decisionReference').value = report.review_reference || '';
  $('decisionNote').value = report.review_note || '';
  $('reviewPanel').hidden = false;
  $('reviewPanel').scrollIntoView({behavior: 'smooth', block: 'start'});
}
async function ownerAction(path) {
  try { await api(path, 'POST'); showToast('Saved. The public feed will reflect this change after clients synchronize.'); await loadModeration(); await loadOverview(); }
  catch (error) { showToast(error.message, true); }
}
async function loadAudit() {
  try {
    const data = await api('/v1/admin/audit');
    const body = $('auditBody'); body.replaceChildren();
    if (!data.events.length) { const tr = element('tr'); const td = element('td', 'No review decisions yet.'); td.colSpan = 4; tr.append(td); body.append(tr); return; }
    for (const event of data.events) {
      const tr = element('tr');
      tr.append(element('td', `#${event.report_id}`), element('td', event.event),
                element('td', `${event.note} ${event.reference ? '· ' + event.reference : ''}`),
                element('td', event.created_at.slice(0, 16)));
      body.append(tr);
    }
  } catch (error) { showToast(error.message, true); }
}
// Wire controls after the HTML has loaded (the script uses the defer attribute).
document.querySelectorAll('[data-screen]').forEach(nav => nav.addEventListener('click', () => openScreen(nav.dataset.screen)));
$('logoutButton').addEventListener('click', () => signOut());
$('refreshButton').addEventListener('click', loadOverview);
$('moderationFilter').addEventListener('change', loadModeration);
$('cancelReview').addEventListener('click', () => { $('reviewPanel').hidden = true; selected = null; });
$('loginForm').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const result = await api('/v1/auth/login', 'POST', {username: $('loginUser').value, password: $('loginPass').value});
    token = result.token;
    sessionStorage.setItem('scamlensCommunitySession', token);
    $('loginPass').value = '';
    displaySession(result.user);
  } catch (error) { showToast(error.message, true); }
});
$('reportForm').addEventListener('submit', async event => {
  event.preventDefault();
  const submitButton = $('reportForm').querySelector('button[type=submit]');
  if (submitButton.disabled) return;
  submitButton.disabled = true;
  try {
    await api('/v1/reports', 'POST', {
      kind: $('reportKind').value, value: $('reportValue').value,
      details: $('reportDetails').value, evidence_ref: $('reportEvidence').value
    });
    $('reportForm').reset();
    showToast('Report received for review. It has not been published. Duplicate pending reports may be merged.');
  } catch (error) { showToast(error.message, true); }
  finally { submitButton.disabled = false; }
});
$('decisionForm').addEventListener('submit', async event => {
  event.preventDefault();
  if (!selected) return;
  try {
    await api(`/v1/admin/reports/${selected.id}/decision`, 'POST', {
      decision: $('decisionValue').value, reference: $('decisionReference').value,
      note: $('decisionNote').value
    });
    $('reviewPanel').hidden = true; selected = null;
    await loadModeration(); await loadOverview();
    showToast('Decision saved and recorded in the audit trail. Any old publication was retracted.');
  } catch (error) { showToast(error.message, true); }
});
(async () => {
  if (publicReport) {
    $('workspace').hidden = false;
    openScreen('submit');
    // Fragment is local to the browser and never part of the initial HTTP request.
    const host = new URLSearchParams(location.hash.slice(1)).get('domain');
    if (host && host.length <= 253 && /^(?:[a-z0-9-]+\.)+[a-z0-9-]+$/i.test(host)) {
      $('reportKind').value = 'domain';
      $('reportValue').value = host;
      history.replaceState(null, '', '/report');
    }
    return;
  }
  $('authScreen').hidden = false;
  if (!token) return;
  try { displaySession(await api('/v1/auth/me')); }
  catch { signOut(false); }
})();
