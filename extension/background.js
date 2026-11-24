/* Trusted extension service worker. Page scripts receive the watchlist, never the API token. */
'use strict';
importScripts('shared/feed.js');
const DEFAULT_SETTINGS = {
  autoScan: true, showWarning: true, sensitivity: 'balanced',
  accent: '#1d70bd', saveHistory: false, mutedHosts: []
};
const PUBLIC_FEED_URL = ''; // No centralized feed is configured in the source release.
const FEED_ALARM = 'scamlens-public-feed-refresh';
const DEFAULTS = {
  settings: DEFAULT_SETTINGS, dbCache: [], dbSyncedAt: null, publicFeedCache: [], publicFeedUrl: PUBLIC_FEED_URL, publicFeedSyncedAt: null,
  apiToken: '', recentAlerts: []
};
// Do not expose the owner's local API token through chrome.storage to content scripts.
// Only extension-owned pages and this background worker may read local storage.
const protectionReady = chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});

const ALLOWED_KINDS = new Set(['domain', 'url', 'email', 'phone', 'address']);
const ALLOWED_STATUSES = new Set(['reported', 'verified', 'external', 'published']);
function recordsForPage(list) {
  // A content script needs the indicator value to match locally, NOT notes,
  // evidence references, reviewer identities, publisher credentials, or tokens.
  // The scan stays local; these records are never sent to a website server.
  if (!Array.isArray(list)) return [];
  return list.slice(0, 5000).filter(record =>
    record && ALLOWED_KINDS.has(record.kind) &&
    typeof record.value === 'string' && record.value.length <= 2100 &&
    record.review_state !== 'dismissed'
  ).map(record => ({
    kind: record.kind,
    value: record.value,
    canonical: typeof record.canonical === 'string' && record.canonical.length <= 2100 ? record.canonical : '',
    status: ALLOWED_STATUSES.has(record.status) ? record.status : 'reported',
    review_state: record.review_state === 'approved' ? 'approved' : 'pending'
  }));
}

async function initialize() {
  await protectionReady;
  const saved = await chrome.storage.local.get(Object.keys(DEFAULTS));
  const missing = Object.fromEntries(Object.entries(DEFAULTS).filter(([key]) => saved[key] === undefined));
  if (Object.keys(missing).length) await chrome.storage.local.set(missing);
}
// Automatic, read-only feed updates require no account or access token.
// No required network host: users opt in to a feed server in Settings.
async function refreshPublicFeed() {
  // Only fetch from a feed manually configured by the user in Settings.
  await protectionReady;
  const stored = await chrome.storage.local.get('publicFeedUrl');
  if (!stored.publicFeedUrl) return;
  try {
    const url = new URL(stored.publicFeedUrl);
    const loopback = url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port === '8877';
    if (!(url.protocol === 'https:' || loopback) || url.pathname !== '/v1/feed') return;
    // A user grants the host permission explicitly when configuring the feed.
    if (!await chrome.permissions.contains({origins: [`${url.origin}/*`]})) return;
    const response = await fetch(url.href, {cache: 'no-store', signal: AbortSignal.timeout(12000)});
    const doc = await ScamLensFeed.readLimitedJson(response);
    const records = ScamLensFeed.validateFeed(doc);
    await chrome.storage.local.set({
      publicFeedCache: records,
      publicFeedSyncedAt: new Date().toISOString(),
      publicFeedState: 'updated'
    });
  } catch {
    // No network / failed feed must not be mistaken for a clean or safe result.
    await chrome.storage.local.set({publicFeedState: 'unavailable'});
  }
}
async function boot() {
  await initialize();
  await chrome.alarms.create(FEED_ALARM, {periodInMinutes: 360});
  await refreshPublicFeed();
}
chrome.runtime.onInstalled.addListener(() => { boot().catch(console.error); });
chrome.runtime.onStartup.addListener(() => { boot().catch(console.error); });
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === FEED_ALARM) refreshPublicFeed().catch(console.error);
});
// Also refresh if a service worker is first launched after an update.
initialize().then(() => chrome.alarms.create(FEED_ALARM, {periodInMinutes: 360})).catch(console.error);


async function getConfig() {
  await protectionReady;
  const saved = await chrome.storage.local.get(['settings', 'dbCache', 'publicFeedCache', 'publicFeedSyncedAt']);
  // A published report that has not been refreshed for a week should not
  // keep generating warnings forever if the owner has retracted it.
  const publishedFresh = saved.publicFeedSyncedAt && Date.now() - Date.parse(saved.publicFeedSyncedAt) <= 7 * 86400000;
  return {
    settings: {...DEFAULT_SETTINGS, ...(saved.settings || {})},
    records: recordsForPage([...(Array.isArray(saved.dbCache) ? saved.dbCache : []), ...(publishedFresh && Array.isArray(saved.publicFeedCache) ? saved.publicFeedCache : [])])
  };
}
function hostnameOf(url) {
  try { const u = new URL(url); return ['http:', 'https:'].includes(u.protocol) ? u.hostname.toLowerCase() : ''; }
  catch { return ''; }
}
async function recordAlert(sender, message) {
  const host = hostnameOf(sender.url || sender.tab?.url || '');
  if (!host || !['reviewed', 'external', 'published', 'reported', 'patterns'].includes(message.assessment)) return;
  await protectionReady;
  const data = await chrome.storage.local.get(['settings', 'recentAlerts']);
  if (!data.settings?.saveHistory) return;
  const old = Array.isArray(data.recentAlerts) ? data.recentAlerts : [];
  const now = Date.now();
  const similar = old.some(x => x.hostname === host && x.assessment === message.assessment && now - Date.parse(x.at) < 300000);
  if (similar) return;
  // Hostname and category only. No full URLs, message text, recipient addresses, or matching indicator values.
  await chrome.storage.local.set({recentAlerts: [{hostname: host, assessment: message.assessment, at: new Date(now).toISOString()}, ...old].slice(0, 50)});
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  // GET_CONFIG is strictly for an extension content script in a real tab.
  // A remote website has no permission to call this extension message handler.
  if (message?.type === 'GET_CONFIG' && sender.id === chrome.runtime.id && sender.tab?.id !== undefined && sender.frameId === 0) {
    getConfig().then(reply).catch(() => reply({settings: DEFAULT_SETTINGS, records: []}));
    return true;
  }
  if (message?.type === 'SCAN_RESULT' && sender.id === chrome.runtime.id && sender.tab?.id !== undefined && sender.frameId === 0) {
    const assessment = ['reviewed','external','published','reported','patterns'].includes(message.assessment) ? message.assessment : 'none';
    const mark = assessment === 'reviewed' ? '!' : assessment === 'external' ? '!' : assessment === 'published' ? '!' : assessment === 'reported' ? '?' : assessment === 'patterns' ? '·' : '';
    chrome.action.setBadgeText({tabId: sender.tab.id, text: mark}).catch(() => {});
    if (mark) chrome.action.setBadgeBackgroundColor({tabId: sender.tab.id, color: ['reviewed', 'external', 'published'].includes(assessment) ? '#bf4242' : '#ba842a'}).catch(() => {});
    recordAlert(sender, {...message, assessment}).catch(() => {});
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local' || (!changes.settings && !changes.dbCache && !changes.publicFeedCache)) return;
  chrome.tabs.query({}).then(tabs => {
    tabs.forEach(tab => {
      if (tab.id !== undefined) chrome.tabs.sendMessage(tab.id, {type: 'CONFIG_CHANGED'}).catch(() => {});
    });
  }).catch(() => {});
});
