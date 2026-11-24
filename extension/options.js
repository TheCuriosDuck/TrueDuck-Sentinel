const $ = id => document.getElementById(id);
function message(id, content, isError = false) {
  const el = $(id); el.textContent = content; el.style.color = isError ? '#bf4540' : '';
}
function cell(text, className = '') {
  const td = document.createElement('td'); td.textContent = text;
  if (className) td.className = className;
  return td;
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
// Users choose their own trusted public API.
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
    const doc = await ScamLensFeed.readLimitedJson(response);
    const records = ScamLensFeed.validateFeed(doc);
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
  message('cloudMessage', 'Public feed cache cleared.');
}

async function main() {
  const saved = await chrome.storage.local.get(['settings', 'publicFeedUrl', 'publicFeedCache', 'publicFeedSyncedAt']);
  $('cloudUrl').value = saved.publicFeedUrl || '';
  $('cloudFeedStatus').textContent = saved.publicFeedSyncedAt ? `${(saved.publicFeedCache || []).length} published entries · Synced ${new Date(saved.publicFeedSyncedAt).toLocaleString()}` : 'Cloud feed not synchronized.';
  const preferences = saved.settings || {};
  $('autoScan').checked = preferences.autoScan !== false;
  $('saveHistory').checked = !!preferences.saveHistory;
  $('showWarning').checked = preferences.showWarning !== false;
  $('sensitivity').value = preferences.sensitivity || 'balanced';
  $('accent').value = preferences.accent || '#3977e8';
  document.documentElement.style.setProperty('--accent', $('accent').value);
  $('syncCloudButton').addEventListener('click', syncCloudFeed);
  $('clearCloudButton').addEventListener('click', clearCloudFeed);
  $('savePreferences').addEventListener('click', savePreferences);
  $('clearHistory').addEventListener('click', clearHistory);
  $('addMuted').addEventListener('click', addMuted);
  $('mutedInput').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); addMuted();}});
  renderHistory(); renderMuted();
}
main().catch(error => message('cloudMessage', error.message, true));
