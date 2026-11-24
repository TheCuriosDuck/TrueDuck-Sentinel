const assert = require('node:assert/strict');
const feed = require('../extension/shared/feed.js');
function doc(indicators) {return {schema:'scamlens.public-feed.v1',generated_at:new Date().toISOString(),indicators};}
const ok = {kind:'domain',value:'scam-test.example.test',classification:'reviewed_report'};
const result = feed.validateFeed(doc([ok]));
assert.equal(result[0].status,'published');
assert.deepEqual(feed.validateFeed(doc([])),[]);
assert.throws(()=>feed.validateFeed(doc([{...ok,kind:'email'}])));
assert.throws(()=>feed.validateFeed(doc([ok,ok])));
assert.throws(()=>feed.validateFeed(doc([{...ok,value:'localhost'}])));
assert.throws(()=>feed.validateFeed({...doc([ok]),generated_at:'2020-01-01T00:00:00Z'}));
const summary = 'Reviewed reports describe suspicious payment requests.';
const published = feed.validateFeed(doc([{...ok, public_summary:summary, review_note:'private'}]));
assert.equal(published[0].reason, summary);
assert.equal(published[0].review_note, undefined);
assert.equal(feed.validateFeed(doc([{...ok, public_summary:'x'.repeat(241)}]))[0].reason, '');
const detector = require('../extension/shared/detector.js');
assert.equal(detector.analyze({locationHref:'https://scam-test.example.test/'}, published).matches[0].reason, summary);
console.log('Public feed validation tests passed.');
