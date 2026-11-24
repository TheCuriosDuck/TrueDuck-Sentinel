/* Local email and phone lookup; returns records only when an exact match exists. */
(function (root) {
  'use strict';
  function canonical(kind, value) {
    if (!['email','phone'].includes(kind) || typeof value !== 'string' || value.length > 190) return '';
    if (kind === 'email') {
      const email = value.trim().toLowerCase();
      return /^[^\s@]{1,100}@[^\s@]{1,180}\.[^\s@]{2,30}$/.test(email) ? email : '';
    }
    const digits = value.replace(/\D/g, '').replace(/^1(?=\d{10}$)/, '');
    return digits.length === 10 ? digits : '';
  }
  function findLocal(records, kind, value) {
    const target = canonical(kind, value);
    if (!target) return {valid:false, match:null};
    const found = (Array.isArray(records) ? records : []).find(r =>
      r && r.kind === kind && r.review_state !== 'dismissed' &&
      canonical(kind, r.canonical || r.value) === target);
    return {valid:true, match:found || null};
  }
  const api = {canonical, findLocal};
  root.ScamLensLookup = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
