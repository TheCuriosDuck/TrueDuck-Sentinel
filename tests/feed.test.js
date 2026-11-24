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
console.log('Public feed validation tests passed.');
