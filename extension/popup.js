const byId = id => document.getElementById(id);
const app = { records: [], settings: {} };
const OFFICIAL_API = ''; // No backend is preconfigured or contacted automatically.
function addFinding(parent, title, description, type) {
  const item = document.createElement('div'); item.className = 'finding-item';
  const indicator = document.createElement('span'); indicator.className = `finding-marker ${type}`;
  const body = document.createElement('div');
  const heading = document.createElement('strong'); heading.textContent = title;
  const sub = document.createElement('div'); sub.className = 'secondary-text'; sub.textContent = description;
  body.append(heading, sub); item.append(indicator, body); parent.append(item);
}
function renderAnalysis(parent, outcome) {
  parent.replaceChildren();
  if (outcome.level === 'clear') {
    addFinding(parent, outcome.assessment === 'paused' ? 'Scanning paused' : 'No indicators found', outcome.assessment === 'paused' ? 'This site is excluded in Preferences.' : 'No matches in your local checks. This does not guarantee safety.', 'ok');
  }
  outcome.matches.slice(0, 5).forEach(match => {
    const label = match.status === 'external' ? 'external malware URL feed'
      : match.status === 'published' ? 'published reviewed report'
      : match.status === 'verified' ? 'reviewed record' : 'unverified report';
    addFinding(parent, `${match.kind.toUpperCase()} · ${label}`, `${match.value} · ${match.context || 'page content'}${match.reason ? ' · ' + match.reason : ''}${match.source ? ' · Source: ' + match.source : ''}`, ['verified', 'external', 'published'].includes(match.status) ? 'bad' : 'caution');
  });
  if (outcome.matches.length > 5) addFinding(parent, 'Additional matches', `${outcome.matches.length - 5} more entries detected.`, 'bad');
  if (outcome.signals.length) addFinding(parent, 'Suspicious language', outcome.signals.join(' · '), 'caution');
}
function siteState(outcome, name) {
  byId('siteName').textContent = name || 'This page';
  const state = outcome.assessment;
  byId('siteIcon').className = 'status-orb ' + (['reviewed', 'external', 'published'].includes(state) ? 'bad' : ['reported', 'patterns'].includes(state) ? 'caution' : 'ok');
  byId('siteMessage').textContent = state === 'reviewed' ? 'Reviewed watchlist record detected' : state === 'external' ? 'Imported malware URL indicator detected' : state === 'published' ? 'Published threat report matched' : state === 'reported' ? 'Unverified watchlist report detected' : state === 'patterns' ? 'Suspicious wording detected' : state === 'paused' ? 'Scanning paused for this site' : 'No matches detected (not a safety guarantee)';
  renderAnalysis(byId('siteFindings'), outcome);
}
async function scanTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const name = tab?.url ? (() => { try { return new URL(tab.url).hostname; } catch { return tab.title || 'This page'; } })() : 'This page';
  try {
    const outcome = await chrome.tabs.sendMessage(tab.id, { type: 'GET_SCAN' });
    if (outcome?.level) siteState(outcome, name);
    else throw new Error('No scan result');
  } catch {
    byId('siteName').textContent = name;
    byId('siteMessage').textContent = 'This browser page cannot be scanned';
    byId('siteFindings').replaceChildren();
  }
}
async function synchronize() {
  const token = (await chrome.storage.local.get('apiToken')).apiToken;
  if (!token) { byId('syncMessage').textContent = 'Personal database sync is for administrators. Website protection requires no account.'; return; }
  byId('syncMessage').textContent = 'Connecting to your local database…';
  try {
    // Download both sources. Only the extension sees the API token.
    const headers = { Authorization: `Bearer ${token}` };
    const [manualResponse, feedResponse] = await Promise.all([
      fetch('http://127.0.0.1:8765/api/indicators', { headers, signal: AbortSignal.timeout(12000) }),
      fetch('http://127.0.0.1:8765/api/intelligence', { headers, signal: AbortSignal.timeout(12000) })
    ]);
    const [manual, external] = await Promise.all([manualResponse.json(), feedResponse.json()]);
    if (!manualResponse.ok || !feedResponse.ok) throw new Error(manual.error || external.error || 'Sync failed; update the Python backend to v0.5');
    if (!Array.isArray(manual.records) || !Array.isArray(external.records)) throw new Error('Unexpected database response');
    // Dismissed reports are preserved in the database, not distributed to scanners.
    const activeReports = manual.records.filter(r => r.review_state !== 'dismissed');
    const publicData = await chrome.storage.local.get(['publicFeedCache', 'publicFeedSyncedAt']);
    const fresh = publicData.publicFeedSyncedAt && Date.now() - Date.parse(publicData.publicFeedSyncedAt) <= 7 * 86400000;
    const published = fresh && Array.isArray(publicData.publicFeedCache) ? publicData.publicFeedCache : [];
    app.records = [...activeReports, ...external.records, ...published];
    await chrome.storage.local.set({ dbCache: [...activeReports, ...external.records], feedCount: external.records.length, dbSyncedAt: new Date().toISOString() });
    byId('dbCount').textContent = `${activeReports.length} personal + ${external.records.length} external + ${published.length} published`;
    byId('syncMessage').textContent = 'Database synchronized.';
    await scanTab();
  } catch (error) { byId('syncMessage').textContent = `Offline: using cached records. ${error.message}`; }
}
async function toggleMute() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  let host;
  try { host = new URL(tab.url).hostname.toLowerCase(); } catch { return; }
  if (!host) return;
  const saved = await chrome.storage.local.get('settings');
  const current = saved.settings || {};
  const hosts = Array.isArray(current.mutedHosts) ? current.mutedHosts : [];
  const updated = hosts.includes(host) ? hosts.filter(x => x !== host) : [...hosts, host];
  await chrome.storage.local.set({settings: {...current, mutedHosts: updated}});
  byId('muteButton').textContent = updated.includes(host) ? 'Resume this site' : 'Pause this site';
  setTimeout(scanTab, 150);
}
async function updateMuteButton() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  const saved = await chrome.storage.local.get('settings');
  let host;
  try { host = new URL(tab.url).hostname.toLowerCase(); } catch { host = ''; }
  byId('muteButton').disabled = !host;
  byId('muteButton').textContent = (saved.settings?.mutedHosts || []).includes(host) && host ? 'Resume this site' : 'Pause this site';
}
async function reportCurrentSite() {
  // Only a user-initiated click opens this report form. We do not upload the
  // webpage, its content, or the URL to the database automatically.
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  let candidate;
  try {
    const u = new URL(tab?.url || '');
    if (!['http:', 'https:'].includes(u.protocol)) throw new Error('Unsupported page');
    // Report the hostname, not the full URL. Query strings can contain
    // personal details, one-time links, or authentication tokens.
    candidate = u.hostname;
  } catch {
    byId('siteMessage').textContent = 'Open a regular website first to report it.';
    return;
  }
  await chrome.tabs.create({url: chrome.runtime.getURL('options.html') + '?report=' + encodeURIComponent(candidate)});
}
async function lookupIndicator() {
  const kind = byId('lookupKind').value;
  const value = byId('lookupValue').value.trim();
  const output = byId('lookupResult');
  output.hidden = false;
  output.replaceChildren();
  const local = ScamLensLookup.findLocal(app.records, kind, value);
  if (!local.valid) {
    output.textContent = kind === 'email' ? 'Enter a valid email address.' : 'Enter a valid 10-digit US/Canada phone number.';
    return;
  }
  const save = (title, description, type) => addFinding(output, title, description, type);
  if (local.match) {
    const reviewed = ['verified','published','external'].includes(local.match.status);
    save(reviewed ? 'Matching reviewed record' : 'Matching unverified report',
      'Found an exact match in your locally cached records. A report is not proof of fraud.',
      reviewed ? 'bad' : 'caution');
  }
  // Only the user's explicit Look up click sends this value to the API.
  // Browsing, automatic scanning, and passive webpage content NEVER use this endpoint.
  let origin = OFFICIAL_API;
  const saved = await chrome.storage.local.get('publicFeedUrl');
  try {
    const url = new URL(saved.publicFeedUrl || '');
    if (url.pathname === '/v1/feed' && (url.protocol === 'https:' ||
        (url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port === '8877'))) {
      origin = url.origin;
    }
  } catch { /* No online lookup server configured. */ }
  if (!origin) {
    save('Online lookup not configured',
      'Only locally cached indicators were checked. An unknown contact is not necessarily safe.', 'caution');
    return;
  }
  byId('lookupButton').disabled = true;
  try {
    const response = await fetch(origin + '/v1/lookup', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind, value}),
      cache: 'no-store',
      signal: AbortSignal.timeout(8000)
    });
    if (!response.ok) throw Error(response.status === 429 ? 'Rate limit reached.' : 'Lookup service unavailable.');
    const data = await response.json();
    if (data?.match === true && data?.classification === 'reviewed_report') {
      save('Reviewed contact indicator match', 'A reviewer explicitly made this contact searchable. This does not prove the sender or number is fraudulent.', 'bad');
    } else if (!local.match) {
      save('No reviewed match found', 'No exact match in the available local data or published lookup records. This is not a safety guarantee.', 'ok');
    }
  } catch {
    save(local.match ? 'Online lookup unavailable' : 'Unable to verify online',
      'Your local check completed, but the Sentinel lookup service was unreachable. No online reputation result was returned.', 'caution');
  } finally { byId('lookupButton').disabled = false; }
}
async function main() {
  const data = await chrome.storage.local.get(['dbCache', 'publicFeedCache', 'publicFeedSyncedAt', 'settings', 'dbSyncedAt', 'feedCount']);
  const fresh = data.publicFeedSyncedAt && Date.now() - Date.parse(data.publicFeedSyncedAt) <= 7 * 86400000;
  const published = fresh && Array.isArray(data.publicFeedCache) ? data.publicFeedCache : [];
  app.records = [...(data.dbCache || []), ...published]; app.settings = data.settings || {};
  document.documentElement.style.setProperty('--accent', app.settings.accent || '#3977e8');
  const externalCount = Number(data.feedCount || 0);
  byId('dbCount').textContent = `${Math.max(0, (data.dbCache || []).length - externalCount)} personal + ${externalCount} external + ${published.length} published`;
  if (data.publicFeedSyncedAt) byId('syncMessage').textContent = `Published feed updated ${new Date(data.publicFeedSyncedAt).toLocaleString()}`;
  else byId('syncMessage').textContent = 'Offline detection active. Online feed not yet synchronized.';
  byId('settingsButton').addEventListener('click', () => chrome.runtime.openOptionsPage());
  byId('manageButton').addEventListener('click', () => chrome.runtime.openOptionsPage());
  byId('scanButton').addEventListener('click', scanTab);
  byId('reportSiteButton').addEventListener('click', reportCurrentSite);
  byId('muteButton').addEventListener('click', toggleMute);
  updateMuteButton();
  byId('syncButton').addEventListener('click', synchronize);
  byId('lookupButton').addEventListener('click', lookupIndicator);
  byId('lookupKind').addEventListener('change', () => {
    byId('lookupValue').placeholder = byId('lookupKind').value === 'phone' ? '(202) 555-0199' : 'name@example.com';
  });
  byId('lookupValue').addEventListener('keydown', event => { if (event.key === 'Enter') lookupIndicator(); });
  byId('checkButton').addEventListener('click', () => {
    const text = byId('manualInput').value.trim();
    if (!text) { byId('manualResults').hidden = false; byId('manualResults').textContent = 'Enter something to check.'; return; }
    const results = ScamLensDetector.analyze({ text }, app.records, app.settings);
    byId('manualResults').hidden = false;
    renderAnalysis(byId('manualResults'), results);
  });
  scanTab();
}
main().catch(error => { byId('siteMessage').textContent = error.message; });

// Opens the separate community console after a user click.
// Never copy a whole URL: the query, fragment and path may hold private data.
async function openCommunitySite() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  let host = '';
  try {
    const url = new URL(tab?.url || '');
    if (['http:', 'https:'].includes(url.protocol)) host = url.hostname;
  } catch { /* A browser-internal tab has no reportable hostname. */ }
  // Use only the selected feed service; do not send the hostname to a default server.
  const saved = await chrome.storage.local.get('publicFeedUrl');
  let origin;
  try {
    const url = new URL(saved.publicFeedUrl || '');
    if (url.pathname !== '/v1/feed' || url.username || url.password || url.search || url.hash ||
        !(url.protocol === 'https:' || (url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port === '8877'))) throw Error();
    origin = url.origin;
  } catch {
    byId('siteMessage').textContent = 'Set a trusted reporting API in Settings (Published intelligence feed) first.';
    return;
  }
  const consoleUrl = origin + '/report' +
    (host ? '#domain=' + encodeURIComponent(host) : '');
  await chrome.tabs.create({url: consoleUrl});
}
byId('communitySiteButton').addEventListener('click', openCommunitySite);
