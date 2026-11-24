const assert = require('node:assert/strict');
const detect = require('../extension/shared/detector.js');
const records = [
  { kind:'email', value:'alerts@example.test', canonical:'alerts@example.test', status:'reported' },
  { kind:'phone', value:'(202) 555-0199', canonical:'2025550199', status:'reported' },
  { kind:'domain', value:'example-scam.test', canonical:'example-scam.test', status:'verified' },
  { kind:'address', value:'123 Example Road, Testville', canonical:'123 example road testville', status:'reported' }
];
const result = detect.analyze({text:'Send to alerts@example.test or call +1 202-555-0199. 123 Example Road, Testville.',urls:['https://sub.example-scam.test/pay']},records);
assert.equal(result.matches.length, 4);
assert.equal(result.level, 'watchlist');
assert.equal(detect.analyze({text:'This is a routine informational notice.'},records).level,'clear');
assert.equal(detect.analyze({text:'Urgent payment! Act now and use a gift card.'},[]).level,'caution');
assert.equal(detect.analyze({text:'A gift card is nice.'},[]).level,'clear');
assert.equal(detect.analyze({text:'A gift card is nice.'},[],{sensitivity:'high'}).level,'caution');
assert.equal(detect.analyze({text:'You can visit example-scam.test'},records).matches.length,1);
assert.equal(detect.analyze({text:'Send to notalerts@example.test'},records).matches.length,0);
assert.equal(detect.analyze({text:'Link: https://not-example-scam.test'},records).matches.length,0);
// The final success message is printed only after every test passes.
// Reviewed records and reported records must not be presented as the same finding.
const reviewed = detect.analyze({locationHref:'https://sub.example-scam.test/account', text:'hello'},records);
assert.equal(reviewed.assessment, 'reviewed');
assert.equal(reviewed.matches[0].context, 'current site');
const unverified = detect.analyze({text:'Contact alerts@example.test'},records);
assert.equal(unverified.assessment, 'reported');
assert.equal(unverified.matches[0].context, 'page content or link');
assert.equal(detect.analyze({text:'Urgent payment: act now using a gift card'},[]).assessment,'patterns');
assert.equal(detect.analyze({text:'ordinary page'},[]).assessment,'none');

// External intelligence must have its own assessment; do not call it verified.
const external = [{
  kind: 'url', value: 'https://example-malware.test/payload',
  canonical: 'https://example-malware.test/payload', status: 'external',
  source: 'URLhaus demo feed', reason: 'fictional test'
}];
const externalMatch = detect.analyze({
  text: 'Visit https://example-malware.test/payload'
}, external);
assert.equal(externalMatch.assessment, 'external');
assert.equal(externalMatch.matches.length, 1);
assert.equal(externalMatch.matches[0].status, 'external');
assert.equal(detect.analyze({
  locationHref: 'https://example-malware.test/another-path'
}, external).assessment, 'none');

// v0.5: dismissed reports never trigger warnings, even in old local caches.
const dismissed = [{
  kind: 'email', value: 'case@example.test', canonical: 'case@example.test',
  status: 'reported', review_state: 'dismissed'
}];
assert.equal(detect.analyze({text: 'Contact case@example.test'}, dismissed).assessment, 'none');
const pending = [{...dismissed[0], review_state: 'pending'}];
assert.equal(detect.analyze({text: 'Contact case@example.test'}, pending).assessment, 'reported');

// Published entries are not the owner's personal verified reports.
{
  const result = detect.analyze({text:'Visit review-feed.example.test now!'}, [
    {kind:'domain', value:'review-feed.example.test', canonical:'review-feed.example.test', status:'published'}
  ]);
  assert.equal(result.assessment, 'published');
}

console.log("Detector tests passed, including published-feed assessment.");
