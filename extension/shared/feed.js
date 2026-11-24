/* Read-only public intelligence feed parsing; no account, token, or page text. */
(function (root) {
  'use strict';
  function normalize(kind, value) {
    if (kind === 'domain') {
      if (value.length > 253 || !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(value)) return '';
      if (value.endsWith('.local') || value.endsWith('.internal')) return '';
      return value;
    }
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.port || !url.hostname.includes('.') || /^(?:localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)/.test(url.hostname)) return '';
      return `${url.protocol}//${url.host.toLowerCase()}${url.pathname || '/'}`;
    } catch { return ''; }
  }
  function validateFeed(doc) {
    if (!doc || doc.schema !== 'scamlens.public-feed.v1' || !Array.isArray(doc.indicators) || doc.indicators.length > 5000) throw Error('Invalid feed format');
    const timestamp = Date.parse(doc.generated_at);
    if (doc.generated_at && (!Number.isFinite(timestamp) || Math.abs(Date.now() - timestamp) > 7 * 86400000)) throw Error('Feed is stale');
    const values = new Set();
    return doc.indicators.map(item => {
      if (item?.classification !== 'reviewed_report' || !['domain', 'url'].includes(item.kind) || typeof item.value !== 'string' || item.value.length > 2100) throw Error('Invalid feed indicator');
      const value = normalize(item.kind, item.value);
      if (!value || value !== item.value || values.has(item.kind + ':' + value)) throw Error('Invalid or duplicate feed indicator');
      values.add(item.kind + ':' + value);
      // The optional summary is public text, never HTML or a private review note.
      const summary = typeof item.public_summary === 'string' && item.public_summary.length <= 240 ? item.public_summary : '';
      return {kind: item.kind, value, canonical: value, status: 'published', review_state: 'approved', reason: summary};
    });
  }
  async function readLimitedJson(response) {
    if (!response.ok) throw Error(`Feed returned HTTP ${response.status}`);
    const reader = response.body?.getReader();
    if (!reader) throw Error('Feed body unavailable');
    const chunks = []; let total = 0;
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > 14000000) { await reader.cancel(); throw Error('Feed too large'); }
      chunks.push(value);
    }
    const decoder = new TextDecoder('utf-8', {fatal: true});
    const text = chunks.map(chunk => decoder.decode(chunk, {stream: true})).join('') + decoder.decode();
    return JSON.parse(text);
  }
  const api = {validateFeed, readLimitedJson, normalize};
  root.ScamLensFeed = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
