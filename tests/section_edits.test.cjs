const {test}=require('node:test'),assert=require('node:assert/strict'),S=require('../src/web/section-edits.js');
const s=(id,start,end,extra={})=>({id,start,end,type:'verse',name:'Custom preserved',...extra});
test('type-based names do not use unrelated display names',()=>{assert.equal(S.name('verse',[s('c',0,3,{type:'chorus',name:'Chorus 1'})]),'Verse 1');assert.equal(S.name('pre-chorus',[s('x',0,3,{type:'custom',name:'My title'})]),'Pre-chorus 1');});
test('near-touching boundaries snap only the candidate',()=>{const old=[s('a',0,3)];const result=S.plan(old,s('b',3.015,6),10);assert.equal(result.rows[1].start,3);assert.equal(old[0].end,3);});
test('conflicts never mutate originals and explicit analytical keep preserves both',()=>{const old=[s('a',0,4)];assert.equal(S.plan(old,s('b',2,5),10).conflicts.length,1);const r=S.plan(old,s('b',2,5),10,{resolution:'analysis'});assert.equal(r.rows.length,2);assert.equal(r.candidate.layer,'analysis');assert.deepEqual(old,[s('a',0,4)]);});
test('linked shared boundary changes exactly two adjacent sections',()=>{const old=[s('a',0,3),s('b',3,6),s('c',8,10)];const r=S.plan(old,s('a',0,4),10,{shared:true});assert.equal(r.rows[1].start,4);assert.deepEqual(r.rows[2],old[2]);assert.equal(old[1].start,3);});
test('explicit trimming retains surviving ID and creates ancestry for a split',()=>{const old=[s('a',0,10)];const r=S.plan(old,s('b',3,6),12,{resolution:'trim'});assert.equal(r.rows.length,3);assert.equal(r.rows[0].id,'a');assert.equal(r.rows[2].derived_from,'a');assert.equal(r.rows[2].name,'Custom preserved');});
test('source bounds and zero duration rejected',()=>{for(const n of [s('x',-1,2),s('x',1,1),s('x',8,12)])assert.throws(()=>S.plan([],n,10));});

test('occurrence numbering is independent of chronological name order',()=>{assert.equal(S.name('verse',[s('a',0,1,{name:'Verse 3'}),s('b',2,3,{name:'Verse 1'})]),'Verse 4');});

test('shared-boundary option never moves structural neighbours of an analytical label',()=>{const old=[s('a',0,3),s('b',3,6),s('x',0,3,{layer:'analysis',overlap_policy:'allow'})];const r=S.plan(old,{...old[2],end:4},10,{shared:true});assert.deepEqual(r.rows.find(n=>n.id==='b'),old[1]);});
