const $ = id => document.getElementById(id);
const BASE = 'http://127.0.0.1:8765';
let records = []; // Personal indicators, shown in editable watchlist table.
let feedRecords = []; // Imported feed records are read-only in the UI.
let feedUpdatedAt = null;
let reviewEvents = []; // Local audit trail returned by the private API.
let publicFeedCount = 0; // Only records explicitly selected for publishing.
let selectedReviewId = null; // Report currently selected in the review form.
let connected = false;
let token = '';

function message(id, content, isError = false) {
  const el = $(id); el.textContent = content; el.style.color = isError ? '#bf4540' : '';
}
function setConnected(value) {
  connected = value;
  $('apiState').textContent = value ? 'Online' : 'Offline';
  $('connectionDot').className = 'connection-dot ' + (value ? 'online' : '');
  $('connectionText').textContent = value ? 'Database connected' : 'Database not connected';
}
async function request(path, options = {}) {
  if (!token) throw new Error('Enter your access token first.');
  const response = await fetch(BASE + path, {
    ...options, headers: { 'Authorization': `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
    signal: AbortSignal.timeout(5000)
  });
  const json = await response.json();
  if (!response.ok) throw new Error(json.error || `Request failed (${response.status})`);
  return json;
}
async function sync() {
  // Keep manual watchlist and outside threat intelligence as separate datasets.
  const [response, external, reviewResult] = await Promise.all([
    request('/api/indicators'), request('/api/intelligence'), request('/api/reviews')
  ]);
  if (!Array.isArray(response.records) || !Array.isArray(external.records)) throw new Error('Unexpected database response. Update Python backend to v0.5.');
  records = response.records;
  feedRecords = external.records;
  feedUpdatedAt = external.updatedAt || null;
  reviewEvents = Array.isArray(reviewResult.records) ? reviewResult.records : [];
  const synced = new Date().toISOString();
  // Content scripts receive combined indicator data, NEVER the API token.
  // Only pending and approved personal reports are used for scanning.
  // Dismissed reports remain visible to the owner for review, not as alerts.
  const activeReports = records.filter(r => r.review_state !== 'dismissed');
  await chrome.storage.local.set({ dbCache: [...activeReports, ...feedRecords], feedCount: feedRecords.length, feedUpdatedAt, dbSyncedAt: synced, apiToken: token });
  $('lastSync').textContent = `Synced ${new Date(synced).toLocaleString()}`;
  setConnected(true);
  renderRecords();
  renderReviewQueue();
  renderReviewHistory();
}
async function connect() {
  // Local administration is optional; consumers never use this connection.
  const allowed = await chrome.permissions.request({origins: ['http://127.0.0.1:8765/*']});
  if (!allowed) { message('connectionMessage', 'Local database permission was declined.', true); return; }
  token = $('apiToken').value.trim();
  message('connectionMessage', 'Connecting to local database…');
  try { await sync(); message('connectionMessage', 'Connected. Your watchlist is now synchronized.'); }
  catch (error) { setConnected(false); message('connectionMessage', `Could not connect: ${error.message}. Start the Python server and check your token.`, true); }
}
function cell(text, className = '') {
  const td = document.createElement('td'); td.textContent = text;
  if (className) td.className = className;
  return td;
}
function renderRecords() {
  $('totalCount').textContent = records.length;
  publicFeedCount = records.filter(r => r.public_share === 1 && r.review_state === 'approved' && ['domain', 'url'].includes(r.kind)).length;
  $('publicCount').textContent = `${publicFeedCount} opt-in record(s) currently selected for publishing.`;
  $('verifiedCount').textContent = records.filter(r => r.review_state === 'approved' || (r.review_state === undefined && r.status === 'verified')).length;
  $('externalCount').textContent = feedRecords.length;
  $('feedUpdated').textContent = feedUpdatedAt ? `Last imported ${new Date(feedUpdatedAt).toLocaleString()}` : 'Not imported yet';
  const search = $('recordSearch').value.trim().toLowerCase();
  const filtered = records.filter(r => [r.kind, r.value, r.status, r.review_state, r.reason, r.source].some(v => String(v || '').toLowerCase().includes(search)));
  $('visibleCount').textContent = filtered.length;
  const body = $('recordsBody'); body.replaceChildren();
  if (!filtered.length) { const row = document.createElement('tr'); const td = cell(records.length ? 'No records match your filter.' : 'No indicators saved yet. Add your first record above.', 'empty-state'); td.colSpan = 5; row.append(td); body.append(row); return; }
  filtered.forEach(record => {
    const tr = document.createElement('tr');
    const valueTd = document.createElement('td');
    const kind = document.createElement('span'); kind.className = 'record-kind'; kind.textContent = record.kind;
    const val = document.createElement('strong'); val.className = 'record-value'; val.textContent = record.value;
    const note = document.createElement('small'); note.className = 'record-note'; note.textContent = record.reason || 'No notes';
    valueTd.append(kind, val, note);
    const status = document.createElement('span');
    const state = record.review_state || (record.status === 'verified' ? 'approved' : 'pending');
    status.className = `status-tag ${state === 'approved' ? 'verified' : state}`;
    status.textContent = state;
    const statusTd = document.createElement('td'); statusTd.append(status);
    const deleteTd = document.createElement('td');
    const button = document.createElement('button'); button.type = 'button'; button.className = 'delete-button'; button.textContent = 'Remove';
    button.addEventListener('click', () => removeRecord(record)); deleteTd.append(button);
    // Only reviewed domains/URLs can be offered for public sharing.
    // The Python API independently checks eligibility; UI checks alone are not security.
    if (record.review_state === 'approved' && ['domain','url'].includes(record.kind)) {
      const sharing = document.createElement('button'); sharing.type = 'button';
      sharing.className = 'subtle-button';
      sharing.textContent = record.public_share === 1 ? 'Unshare' : 'Share in feed';
      sharing.style.marginLeft = '8px';
      sharing.addEventListener('click', () => changeSharing(record));
      deleteTd.append(sharing);
    }
    tr.append(valueTd, statusTd, cell(record.source || 'Manual entry'), cell(String(record.created_at || '').slice(0, 10)), deleteTd);
    body.append(tr);
  });
}
function renderReviewQueue() {
  // The queue lists reports without modifying the database until the reviewer saves.
  const filter = $('reviewFilter').value;
  const pending = records.filter(r => (r.review_state || (r.status === 'verified' ? 'approved' : 'pending')) === 'pending').length;
  $('pendingCount').textContent = `${pending} pending`;
  const list = records.filter(r => filter === 'all' || (r.review_state || (r.status === 'verified' ? 'approved' : 'pending')) === filter);
  const body = $('queueBody'); body.replaceChildren();
  if (!list.length) {
    const tr = document.createElement('tr'); const td = cell('No reports in this view.', 'empty-state');
    td.colSpan = 4; tr.append(td); body.append(tr); return;
  }
  for (const r of list) {
    const tr = document.createElement('tr');
    const state = r.review_state || (r.status === 'verified' ? 'approved' : 'pending');
    const action = document.createElement('td');
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'subtle-button'; button.textContent = 'Review';
    button.addEventListener('click', () => selectReview(r));
    action.append(button);
    tr.append(cell(`${r.kind}: ${r.value}`), cell(state), cell(String(r.created_at || '').slice(0, 10)), action);
    body.append(tr);
  }
}
function selectReview(record) {
  // Prefill the form using existing notes without approving anything yet.
  selectedReviewId = Number(record.id);
  $('reviewTarget').textContent = `${record.kind}: ${record.value}`;
  $('reviewDecision').value = 'approved';
  $('reviewNote').value = record.review_note || '';
  // Require a deliberate evidence reference for each new approval.
  $('evidenceReference').value = record.evidence_reference || '';
  $('reviewForm').hidden = false;
  message('reviewMessage', '');
  $('reviewForm').scrollIntoView({behavior: 'smooth', block: 'center'});
}
function renderReviewHistory() {
  const body = $('reviewHistoryBody'); body.replaceChildren();
  if (!reviewEvents.length) {
    const tr = document.createElement('tr'); const td = cell('No review decisions logged yet.', 'empty-state');
    td.colSpan = 4; tr.append(td); body.append(tr); return;
  }
  for (const e of reviewEvents) {
    const tr = document.createElement('tr');
    tr.append(cell(e.indicator_value), cell(e.decision),
      cell(e.note + (e.evidence_reference ? ` · ${e.evidence_reference}` : '')),
      cell(new Date(e.reviewed_at).toLocaleString()));
    body.append(tr);
  }
}
async function submitReview(event) {
  event.preventDefault();
  if (!connected || selectedReviewId === null) return;
  const payload = {
    decision: $('reviewDecision').value,
    note: $('reviewNote').value.trim(),
    evidence_reference: $('evidenceReference').value.trim()
  };
  try {
    await request(`/api/indicators/${selectedReviewId}/review`, {
      method: 'POST', body: JSON.stringify(payload)
    });
    selectedReviewId = null;
    $('reviewForm').hidden = true;
    await sync();
    message('formMessage', 'Review decision saved and extension watchlist refreshed.');
  } catch (error) { message('reviewMessage', error.message, true); }
}
async function removeRecord(record) {
  if (!connected) { message('formMessage', 'Connect to the database before editing records.', true); return; }
  if (!confirm(`Remove ${record.value} from your watchlist?`)) return;
  try { await request(`/api/indicators/${Number(record.id)}`, { method: 'DELETE' }); await sync(); message('formMessage', 'Record removed.'); }
  catch (error) { message('formMessage', error.message, true); }
}
async function addRecord(event) {
  event.preventDefault();
  if (!connected) { message('formMessage', 'Connect to the local database first.', true); return; }
  const data = { kind: $('kind').value, value: $('value').value.trim(), status: $('status').value, source: $('source').value.trim() || 'Manual entry', reason: $('reason').value.trim() };
  if (!data.value) return;
  try {
    await request('/api/indicators', { method: 'POST', body: JSON.stringify(data) });
    $('addForm').reset(); await sync(); message('formMessage', 'Indicator saved in your SQLite database.');
  } catch (error) { message('formMessage', error.message, true); }
}
async function changeSharing(record) {
  if (!connected) { message('publicMessage', 'Connect to the database first.', true); return; }
  const enabled = record.public_share !== 1;
  // Publication is always a separate, deliberate consent decision.
  if (enabled && !confirm(`Include ${record.value} in a future public intelligence feed?\n\nThis may be published for other users to see. Only share records supported by reliable evidence and your rights to redistribute the information.`)) return;
  try {
    await request(`/api/indicators/${Number(record.id)}/sharing`, {
      method: 'POST', body: JSON.stringify({enabled})
    });
    await sync();
    message('publicMessage', enabled ? 'Selected for the public feed. Nothing has been uploaded.' : 'Removed from the public feed selection.');
  } catch (error) { message('publicMessage', error.message, true); }
}
async function downloadPublicFeed() {
  if (!connected) { message('publicMessage', 'Connect to the local database first.', true); return; }
  try {
    // Download only the filtered JSON snapshot returned by the Python backend.
    const feed = await request('/api/public-preview');
    if (!Array.isArray(feed.indicators)) throw new Error('Unexpected feed response');
    const blob = new Blob([JSON.stringify(feed, null, 2)], {type:'application/json'});
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = `scamlens-public-feed-${new Date().toISOString().slice(0,10)}.json`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message('publicMessage', `Downloaded ${feed.indicators.length} record(s). This file is not hosted or published.`);
  } catch (error) { message('publicMessage', error.message, true); }
}
function exportRecords() {
  const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), records }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = `scamlens-watchlist-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function importRecords(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!connected) { message('importMessage', 'Connect to your database before importing.', true); event.target.value = ''; return; }
  if (file.size > 5_000_000) { message('importMessage', 'Choose a JSON file smaller than 5 MB.', true); event.target.value = ''; return; }
  try {
    const content = JSON.parse(await file.text());
    const items = Array.isArray(content) ? content : content?.records;
    if (!Array.isArray(items) || !items.length || items.length > 5000) {
      throw new Error('The JSON must contain between 1 and 5000 records.');
    }
    if (!items.every(record => record && typeof record === 'object' && !Array.isArray(record))) {
      throw new Error('Some records are not valid objects.');
    }
    if (!confirm(`Import ${items.length} watchlist entries from ${file.name}? Existing duplicates will be skipped.`)) return;
    $('importButton').disabled = true;
    let added = 0, skipped = 0;
    for (let i = 0; i < items.length; i += 100) {
      const result = await request('/api/import', { method: 'POST', body: JSON.stringify({ records: items.slice(i, i + 100) }) });
      added += result.added;
      skipped += result.skipped;
      message('importMessage', `Importing… ${Math.min(i + 100, items.length)} / ${items.length}`);
    }
    await sync();
    message('importMessage', `Import complete: ${added} added, ${skipped} already existed or were repeated.`);
  } catch (error) {
    message('importMessage', `Import stopped: ${error.message}. Previous batches, if any, were saved.`, true);
  } finally {
    $('importButton').disabled = false;
    event.target.value = '';
  }
}
async function savePreferences() {
  const old = (await chrome.storage.local.get('settings')).settings || {};
  const settings = {...old, autoScan: $('autoScan').checked, showWarning: $('showWarning').checked, saveHistory: $('saveHistory').checked, sensitivity: $('sensitivity').value, accent: $('accent').value };
  await chrome.storage.local.set({ settings });
  document.documentElement.style.setProperty('--accent', settings.accent);
  message('preferencesMessage', 'Preferences saved.');
  renderHistory();
}
async function renderHistory() {
  const data = await chrome.storage.local.get(['recentAlerts', 'settings']);
  const rows = data.recentAlerts || [];
  const body = $('historyBody'); body.replaceChildren();
  if (!rows.length) {const tr = document.createElement('tr'); const td = cell(data.settings?.saveHistory ? 'No alerts saved yet.' : 'Alert history is turned off. Enable it in Preferences.', 'empty-state'); td.colSpan = 3; tr.append(td); body.append(tr); return;}
  for (const item of rows) {
    const tr = document.createElement('tr');
    const type = {reviewed: 'Reviewed record', external: 'External malware URL', published: 'Published feed match', reported: 'Unverified report', patterns: 'Suspicious wording'}[item.assessment] || 'Alert';
    tr.append(cell(item.hostname || ''), cell(type), cell(new Date(item.at).toLocaleString())); body.append(tr);
  }
}
async function clearHistory() {
  await chrome.storage.local.set({recentAlerts: []}); renderHistory();
}
async function renderMuted() {
  const settings = (await chrome.storage.local.get('settings')).settings || {};
  const list = $('mutedList'); list.replaceChildren();
  (settings.mutedHosts || []).forEach(host => {
    const row = document.createElement('div'); row.className = 'muted-item';
    const name = document.createElement('span'); name.textContent = host;
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Remove';
    remove.addEventListener('click', async () => {
      const current = (await chrome.storage.local.get('settings')).settings || {};
      await chrome.storage.local.set({settings: {...current, mutedHosts: (current.mutedHosts || []).filter(x => x !== host)}});
      renderMuted();
    });
    row.append(name, remove); list.append(row);
  });
}
async function addMuted() {
  const raw = $('mutedInput').value.trim().toLowerCase();
  let host = '';
  try {host = new URL(raw.includes('://') ? raw : 'https://' + raw).hostname;} catch {}
  if (!host || !/^(?=.{1,253}$)[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(host)) {
    message('preferencesMessage', 'Enter a valid hostname such as example.org.', true); return;
  }
  const settings = (await chrome.storage.local.get('settings')).settings || {};
  const list = Array.isArray(settings.mutedHosts) ? settings.mutedHosts : [];
  await chrome.storage.local.set({settings: {...settings, mutedHosts: [...new Set([...list, host])]}});
  $('mutedInput').value = ''; renderMuted(); message('preferencesMessage', 'Paused site saved.');
}
// --- Optional public intelligence: separate from the private owner database. ---
// This function runs only in the extension settings page, NOT inside a webpage.
// Public feed connections are intentionally restricted to Open Scam's owned API.
// Keep localhost only for your current Windows development tests.
function parseCloudFeedUrl(value) {
  const url = new URL(value.trim());
  const loopback = url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port === '8877';
  const remote = url.protocol === 'https:' && !url.port;
  if (!(remote || loopback) || url.pathname !== '/v1/feed' ||
      url.search || url.hash || url.username || url.password) {
    throw new Error('Use an HTTPS feed ending in /v1/feed or http://127.0.0.1:8877/v1/feed for local testing.');
  }
  return url;
}
function publishedRecord(raw) {
  if (!raw || raw.classification !== 'reviewed_report' || !['domain', 'url'].includes(raw.kind) || typeof raw.value !== 'string') {
    throw new Error('Unexpected feed indicator type');
  }
  const normalized = ScamLensCanonical(raw.kind, raw.value);
  if (!normalized || normalized !== raw.value || raw.value.length > 2100 || /[?#]/.test(raw.value)) {
    throw new Error('Invalid indicator value in feed');
  }
  // No private notes or other untrusted metadata is accepted from this server.
  return {kind: raw.kind, value: raw.value, canonical: normalized,
          status: 'published', review_state: 'approved', source: 'User-configured public feed', reason: ''};
}
function ScamLensCanonical(kind, value) {
  if (kind === 'domain') {
    if (/^(?:\d+\.){3}\d+$/.test(value) || value === 'localhost') return '';
    if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(value)) return '';
    if (value.endsWith('.local') || value.endsWith('.internal')) return '';
    return value;
  }
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash ||
        !url.hostname.includes('.') || /^(?:localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)/.test(url.hostname)) return '';
    return `${url.protocol}//${url.host.toLowerCase()}${url.pathname || '/'}`;
  } catch { return ''; }
}
async function limitedJson(response) {
  if (!response.ok) throw new Error(`Cloud feed request failed (${response.status})`);
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Cloud response body unavailable');
  const chunks = []; let size = 0;
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 700_000) { await reader.cancel(); throw new Error('Cloud feed too large'); }
    chunks.push(value);
  }
  const decoder = new TextDecoder('utf-8', {fatal:true});
  const text = chunks.map(x => decoder.decode(x, {stream:true})).join('') + decoder.decode();
  return JSON.parse(text);
}
async function syncCloudFeed() {
  // User-initiated: request permission only for the selected API hostname.
  let url;
  try { url = parseCloudFeedUrl($('cloudUrl').value); }
  catch (error) { message('cloudMessage', error.message, true); return; }
  try {
    // Browsers display a permission prompt if this origin has not been granted.
    const allowed = await chrome.permissions.request({origins: [`${url.origin}/*`]});
    if (!allowed) { message('cloudMessage', 'Site permission was not granted.', true); return; }
    message('cloudMessage', 'Downloading published indicators…');
    const response = await fetch(url.href, {signal: AbortSignal.timeout(10000), cache: 'no-store'});
    const doc = await limitedJson(response);
    if (doc.schema !== 'scamlens.public-feed.v1' || !Array.isArray(doc.indicators) || doc.indicators.length > 5000) {
      throw new Error('Unexpected public-feed format');
    }
    // A stale source should not be accepted as fresh intelligence.
    if (doc.generated_at && (Math.abs(Date.now() - Date.parse(doc.generated_at)) > 7 * 86400000 || Number.isNaN(Date.parse(doc.generated_at)))) {
      throw new Error('Published snapshot is stale or has an invalid timestamp');
    }
    const unique = new Set();
    const records = doc.indicators.map(item => {
      const record = publishedRecord(item);
      const key = record.kind + ':' + record.canonical;
      if (unique.has(key)) throw new Error('Duplicate published record');
      unique.add(key); return record;
    });
    const synced = new Date().toISOString();
    // Store only the permitted public indicators; NEVER send a local admin token.
    await chrome.storage.local.set({publicFeedCache: records, publicFeedUrl: url.href, publicFeedSyncedAt: synced});
    $('cloudFeedStatus').textContent = `${records.length} published entries · Synced ${new Date(synced).toLocaleString()}`;
    message('cloudMessage', `Cloud feed synchronized (${records.length} record(s)).`);
  } catch (error) {
    message('cloudMessage', `Cloud sync failed: ${error.message}. The previous cache is unchanged.`, true);
  }
}
async function clearCloudFeed() {
  await chrome.storage.local.set({publicFeedCache: [], publicFeedUrl: '', publicFeedSyncedAt: null});
  $('cloudFeedStatus').textContent = 'No public indicators cached.';
  $('cloudUrl').value = '';
  message('cloudMessage', 'Public feed cache cleared. Local reports were not changed.');
}

async function main() {
  const saved = await chrome.storage.local.get(['apiToken', 'dbCache', 'dbSyncedAt', 'feedUpdatedAt', 'settings', 'publicFeedUrl', 'publicFeedCache', 'publicFeedSyncedAt']);
  $('cloudUrl').value = saved.publicFeedUrl || '';
  $('cloudFeedStatus').textContent = saved.publicFeedSyncedAt ? `${(saved.publicFeedCache || []).length} published entries · Synced ${new Date(saved.publicFeedSyncedAt).toLocaleString()}` : 'Cloud feed not synchronized.';
  token = saved.apiToken || '';
  $('apiToken').value = token;
  // Previously cached feed entries must not appear as deletable manual records.
  const cached = Array.isArray(saved.dbCache) ? saved.dbCache : [];
  records = cached.filter(item => item.status !== 'external');
  feedRecords = cached.filter(item => item.status === 'external');
  feedUpdatedAt = saved.feedUpdatedAt || null;
  if (saved.dbSyncedAt) $('lastSync').textContent = `Synced ${new Date(saved.dbSyncedAt).toLocaleString()}`;
  const preferences = saved.settings || {};
  $('autoScan').checked = preferences.autoScan !== false;
  $('saveHistory').checked = !!preferences.saveHistory;
  $('showWarning').checked = preferences.showWarning !== false;
  $('sensitivity').value = preferences.sensitivity || 'balanced';
  $('accent').value = preferences.accent || '#3977e8';
  document.documentElement.style.setProperty('--accent', $('accent').value);
  renderRecords();
  renderReviewQueue();
  renderReviewHistory();
  $('reviewFilter').addEventListener('change', renderReviewQueue);
  $('reviewForm').addEventListener('submit', submitReview);
  $('cancelReview').addEventListener('click', () => { selectedReviewId = null; $('reviewForm').hidden = true; });
  // Opening the dashboard via "Report this site" prefills the report form.
  // It does not submit or upload the current page without the user's click.
  const reportUrl = new URLSearchParams(location.search).get('report');
  if (reportUrl && /^(?:[a-z0-9-]+\.)+[a-z0-9-]+$/i.test(reportUrl) && reportUrl.length <= 253) {
    $('kind').value = 'domain'; $('value').value = reportUrl;
    $('source').value = 'Browser report';
    $('reason').value = 'Submitted for manual review. Confirm the domain before saving.';
    location.hash = 'watchlist';
  }
  $('connectButton').addEventListener('click', connect);
  $('refreshButton').addEventListener('click', connect);
  $('addForm').addEventListener('submit', addRecord);
  $('recordSearch').addEventListener('input', renderRecords);
  $('exportButton').addEventListener('click', exportRecords);
  $('downloadPublicFeed').addEventListener('click', downloadPublicFeed);
  $('syncCloudButton').addEventListener('click', syncCloudFeed);
  $('clearCloudButton').addEventListener('click', clearCloudFeed);
  $('importButton').addEventListener('click', () => $('importFile').click());
  $('importFile').addEventListener('change', importRecords);
  $('savePreferences').addEventListener('click', savePreferences);
  $('clearHistory').addEventListener('click', clearHistory);
  $('addMuted').addEventListener('click', addMuted);
  $('mutedInput').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); addMuted();}});
  renderHistory(); renderMuted();
  // A stored token is not proof of connection: check the server.
  if (token) connect();
}
main().catch(error => message('connectionMessage', error.message, true));

// This button opens the separate website used to manage community submissions.
// It doesn't pass any private database access token to the reporting service.
$('openCommunityConsole')?.addEventListener('click', () => {
  window.open('http://127.0.0.1:8877/dashboard', '_blank', 'noopener');
});
