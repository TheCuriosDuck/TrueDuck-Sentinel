/* Browser-page scanning is local. Page text never goes to the database server. */
(() => {
  'use strict';
  let records = [];
  let settings = {autoScan: true, showWarning: true, sensitivity: 'balanced', mutedHosts: []};
  let result = {level: 'clear', assessment: 'none', matches: [], signals: [], signalCount: 0};
  let timer;
  let observer; // Page changes may require a new scan.
  let dismissed = false;
  const BANNER_ID = 'scamlens-notice-container';

  function pageSnapshot() {
    const text = document.body?.innerText?.slice(0, 50000) || '';
    const urls = [...document.querySelectorAll('a[href]')].slice(0, 200).map(a => a.href);
    return {text, urls, locationHref: location.href};
  }
  function muted() {
    const hosts = Array.isArray(settings.mutedHosts) ? settings.mutedHosts : [];
    return hosts.some(host => location.hostname.toLowerCase() === host || location.hostname.toLowerCase().endsWith('.' + host));
  }
  function removeWarning() { document.getElementById(BANNER_ID)?.remove(); }
  function warning() {
    removeWarning();
    if (!settings.showWarning || dismissed || result.assessment === 'none' || result.assessment === 'paused') return;
    const host = document.createElement('div');
    host.id = BANNER_ID;
    host.style.cssText = 'position:fixed;z-index:2147483647;top:16px;right:16px;width:min(365px,calc(100vw - 32px));';
    const shadow = host.attachShadow({mode: 'closed'});
    const wrap = document.createElement('section');
    wrap.style.cssText = 'box-sizing:border-box;background:#14233d;color:#fff;border:1px solid #41526a;box-shadow:0 18px 48px #101d3480;border-radius:12px;padding:16px;font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;';
    const title = document.createElement('strong');
    title.style.cssText = 'display:block;font-size:14px;margin-bottom:6px;';
    title.textContent = result.assessment === 'reviewed' ? 'community · Reviewed watchlist match'
      : result.assessment === 'external' ? 'community · Malware URL intelligence match'
      : result.assessment === 'published' ? 'community · Published intelligence match'
      : result.assessment === 'reported' ? 'community · Unverified report match' : 'community · Suspicious language';
    const detail = document.createElement('div');
    detail.style.cssText = 'color:#d2dded;font-size:13px;margin-bottom:12px;';
    detail.textContent = result.assessment === 'patterns'
      ? `${result.signals.length} warning patterns found. Context matters; this is not proof of fraud.`
      : result.assessment === 'published'
      ? 'A domain or exact URL matches a reviewed entry in the separately published feed. This is an advisory report, not proof of fraud.'
      : result.assessment === 'external'
      ? 'An exact URL on this page or in its links appears in an imported URLhaus malware feed. Check the source and context before drawing conclusions.'
      : `${result.matches.length} watchlist entry(s) found on this page or its links. A match alone does not prove this site is fraudulent.`;
    // Display only the explicitly public summary of a matching published indicator.
    const summary = result.matches.find(x => x.status === 'published' && x.reason)?.reason;
    if (summary) detail.textContent += ` Public review: ${summary}`;
    const foot = document.createElement('div');
    foot.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:11px;color:#b3c4df';
    const note = document.createElement('span'); note.textContent = 'Open TrueDuck Sentinel for details';
    const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Dismiss';
    close.style.cssText = 'color:#fff;border:1px solid #5f738f;background:#243754;border-radius:7px;padding:6px 10px;cursor:pointer;font:inherit;';
    close.addEventListener('click', () => { dismissed = true; removeWarning(); });
    foot.append(note, close); wrap.append(title, detail, foot); shadow.append(wrap);
    document.documentElement.append(host);
  }
  function scan(force = false) {
    // Pause the observer while drawing our own banner to avoid a rescan loop.
    observer?.disconnect();
    if (muted() || (!settings.autoScan && !force)) {
      result = {level: 'clear', assessment: muted() ? 'paused' : 'none', matches: [], signals: [], signalCount: 0};
      removeWarning();
    } else {
      result = ScamLensDetector.analyze(pageSnapshot(), records, settings);
      warning();
    }
    if (observer && document.body) observer.observe(document.body, {childList: true, subtree: true, characterData: true});
    chrome.runtime.sendMessage({type:'SCAN_RESULT', assessment: result.assessment}).catch(() => {});
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(() => scan(), 1300); }
  function readConfig() {
    return chrome.runtime.sendMessage({type: 'GET_CONFIG'}).then(config => {
      records = Array.isArray(config?.records) ? config.records : [];
      settings = {...settings, ...(config?.settings || {})};
      dismissed = false;
      scan();
    }).catch(() => {});
  }
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === 'GET_SCAN') { scan(true); sendResponse(result); }
    if (message?.type === 'CONFIG_CHANGED') readConfig();
  });
  readConfig();
  if (document.body) {
    observer = new MutationObserver(schedule);
    observer.observe(document.body, {childList: true, subtree: true, characterData: true});
  }
})();
