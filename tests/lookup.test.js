const assert = require('node:assert/strict');
const lookup = require('../extension/shared/lookup.js');
assert.equal(lookup.canonical('email','  HELP@Example.test '),'help@example.test');
assert.equal(lookup.canonical('phone','+1 (202) 555-0199'),'2025550199');
assert.equal(lookup.canonical('phone','1234'),'');
assert.equal(lookup.canonical('email','bad-email'),'');
const records = [
  {kind:'email',value:'support@example.test',status:'reported'},
  {kind:'phone',value:'(202) 555-0199',status:'verified'},
  {kind:'email',value:'private@example.test',review_state:'dismissed'}
];
assert.equal(lookup.findLocal(records,'email','SUPPORT@example.test').match.status,'reported');
assert.equal(lookup.findLocal(records,'phone','2025550199').match.status,'verified');
assert.equal(lookup.findLocal(records,'email','private@example.test').match,null);
assert.equal(lookup.findLocal(records,'email','unknown@example.test').match,null);
console.log('Contact lookup tests passed.');
