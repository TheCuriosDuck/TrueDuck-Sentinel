/* Pure detection functions shared by the popup and content script. No network access. */
(function (root) {
  'use strict';
  const patterns = [
    { id: 'urgency', label: 'Urgent pressure', words: ['act now', 'immediate action', 'within 24 hours', 'urgent payment', 'last warning'] },
    { id: 'payment', label: 'Unusual payment request', words: ['gift card', 'bitcoin payment', 'crypto wallet', 'wire transfer', 'pay with cryptocurrency'] },
    { id: 'account', label: 'Threat to an account', words: ['account will be suspended', 'account has been locked', 'avoid account closure', 'verify your account immediately'] },
    { id: 'codes', label: 'Request for a security code', words: ['send your verification code', 'share the one-time code', 'tell me your otp', 'provide your password'] },
    { id: 'secrecy', label: 'Pressure to keep it secret', words: ['do not tell anyone', 'keep this secret', 'do not contact your bank'] },
    { id: 'threat', label: 'Threatening language', words: ['arrest warrant', 'face legal action', 'police will arrive'] }
  ];
  const normText = (v) => String(v || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const normalizePhone = (v) => {
    let digits = String(v || '').replace(/\D/g, '');
    if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1);
    return digits.length === 10 ? digits : '';
  };
  function hostOf(value) {
    try {
      const url = new URL(/^https?:\/\//i.test(value) ? value : `https://${value}`);
      if (!['http:', 'https:'].includes(url.protocol)) return '';
      return url.hostname.replace(/\.$/, '').toLowerCase();
    } catch { return ''; }
  }
  function canonicalUrl(value) {
    try {
      const u = new URL(value);
      if (!['http:', 'https:'].includes(u.protocol)) return '';
      return `${u.protocol}//${u.host.toLowerCase()}${u.pathname || '/'}${u.search}`;
    } catch { return ''; }
  }
  function canonical(kind, value) {
    if (kind === 'phone') return normalizePhone(value);
    if (kind === 'email') return String(value || '').trim().toLowerCase();
    if (kind === 'address') return normText(value);
    if (kind === 'domain') return hostOf(value);
    if (kind === 'url') return canonicalUrl(value);
    return '';
  }
  function analyze(input, records, settings = {}) {
    const text = String(input?.text || '').slice(0, 50000);
    const urls = [...(Array.isArray(input?.urls) ? input.urls : []), ...(text.match(/https?:\/\/[^\s<>"'`]+/gi) || [])];
    if (input?.locationHref) urls.push(input.locationHref);
    const emailSet = new Set((text.match(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/gi) || []).map(x => x.toLowerCase()));
    const phoneSet = new Set((text.match(/(?:\+?1[\s().-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4}\b/g) || []).map(normalizePhone));
    const urlSet = new Set(urls.map(canonicalUrl).filter(Boolean));
    const domainSet = new Set([...urls.map(hostOf), ...(text.match(/\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b/gi) || []).map(x => x.toLowerCase())].filter(Boolean));
    const normalizedBody = normText(text);
    const siteHost = hostOf(input?.locationHref || '');
    const matches = [];
    for (const entry of Array.isArray(records) ? records : []) {
      if (matches.length >= 20) break;
      // A dismissed report must never generate a browser warning, even
      // when an old cached watchlist has not been refreshed yet.
      if (!entry?.kind || entry.review_state === 'dismissed') continue;
      const value = entry.canonical || canonical(entry.kind, entry.value);
      if (!value) continue;
      let found = false;
      switch (entry.kind) {
        case 'email': found = emailSet.has(value.toLowerCase()); break;
        case 'phone': found = phoneSet.has(value); break;
        case 'url': found = urlSet.has(value); break;
        case 'address': found = normalizedBody.includes(value) && value.length >= 8; break;
        case 'domain':
          found = [...domainSet].some(domain => domain === value || domain.endsWith(`.${value}`));
          break;
        default: break;
      }
      if (found) matches.push({
        kind: entry.kind, value: entry.value, status: entry.status || 'reported',
        reason: entry.reason || '', source: entry.source || '',
        context: ['domain', 'url'].includes(entry.kind) && siteHost && (entry.kind === 'domain' ? (siteHost === value || siteHost.endsWith('.' + value)) : canonicalUrl(input?.locationHref || '') === value) ? 'current site' : 'page content or link'
      });
    }
    const lower = text.toLowerCase();
    const signals = patterns.filter(pattern => pattern.words.some(phrase => lower.includes(phrase))).map(({ label }) => label);
    const sensitivity = settings.sensitivity || 'balanced';
    const threshold = sensitivity === 'high' ? 1 : sensitivity === 'low' ? 3 : 2;
    return {
      matches,
      signals: signals.length >= threshold ? signals : [],
      signalCount: signals.length,
      level: matches.length ? 'watchlist' : signals.length >= threshold ? 'caution' : 'clear',
      // External feed URLs are NOT manually reviewed scam reports; label them separately.
      assessment: matches.some(x => x.status === 'verified') ? 'reviewed'
        : matches.some(x => x.status === 'external') ? 'external'
        : matches.some(x => x.status === 'published') ? 'published'
        : matches.length ? 'reported' : signals.length >= threshold ? 'patterns' : 'none'
    };
  }
  const api = { analyze, canonical, normalizePhone, hostOf };
  root.ScamLensDetector = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
