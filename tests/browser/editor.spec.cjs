const {test,expect}=require('@playwright/test');
const fs=require('node:fs');const crypto=require('node:crypto');
const base='http://127.0.0.1:8772';let fixture;
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const notes=page=>page.evaluate(()=>JSON.parse(JSON.stringify(state.notes)));
const regions=page=>page.evaluate(()=>JSON.parse(JSON.stringify(state.reference.regions)));
const block=(page,id)=>page.locator('.note-block').filter({has:page.locator('span.note-name')}).and(page.locator(`[data-note-id="${id}"]`));
async function post(request,route,data){const response=await request.post(base+'/api/'+route,{data,headers:{Origin:base}});expect(response.ok(),await response.text()).toBeTruthy();return response.json();}
async function select(page,id,modifiers){await block(page,id).click({modifiers:modifiers||[]});}
async function gesture(page,from,to,button='left'){await page.mouse.move(from.x,from.y);await page.mouse.down({button});await page.mouse.move(to.x,to.y,{steps:8});await page.mouse.up({button});}
async function drag(page,id,dx,dy,edge){const target=edge?block(page,id).locator('.note-edge.'+edge):block(page,id);const b=await target.boundingBox();await gesture(page,{x:b.x+b.width/2,y:b.y+b.height/2},{x:b.x+b.width/2+dx,y:b.y+b.height/2+dy});}
async function saved(page){await page.locator('#save').click();await expect(page.locator('#status')).toContainText(/revision saved/i);}
async function signal(page,bus){return page.evaluate(bus=>{
  const a=pianoEditor.audition,meter=bus==='piano'?a.pianoMeter:a.vocalMeter;
  const samples=new Float32Array(meter.fftSize);meter.getFloatTimeDomainData(samples);
  const bins=new Float32Array(meter.frequencyBinCount);meter.getFloatFrequencyData(bins);
  let best=0;for(let i=20;i<bins.length;i++)if(bins[i]>bins[best]||best===0)best=i;
  return {rms:Math.sqrt(samples.reduce((sum,x)=>sum+x*x,0)/samples.length),peak_hz:best*a.context.sampleRate/meter.fftSize,
    piano_gain:a.pianoGain.gain.value,vocal_gain:a.vocalGain.gain.value,sample_rate:a.context.sampleRate,
    last_tone:a.lastTone,media_sources:a.source?1:0,segment:a.segment,source_time:a.audio.currentTime,speed:a.audio.playbackRate};
},bus);}

test.beforeAll(()=>{fixture=JSON.parse(fs.readFileSync('.cache/editor-tests/current.json','utf8'));});
test.beforeEach(async({page,request})=>{
  const ref=await post(request,'reference-create',{id:fixture.analysis,start:.1,end:fixture.duration-.1,
    annotator:'SYNTHETIC BROWSER FIXTURE — NOT HUMAN LABELS',split:'development',song_group:'disposable-editor-fixture',seed:true});
  ref.notes[0].pitch+=.37;
  const edition=await post(request,'reference-save',{reference_id:ref.id,base_revision:ref.revision,notes:ref.notes,regions:[],annotator:ref.annotator});
  await page.goto(`/?analysis=${fixture.analysis}&reference=${edition.id}`);
  await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');
  await expect(page.locator('.note-block')).toHaveCount(edition.notes.length);
  await expect.poll(()=>page.locator('#audio').evaluate(a=>a.readyState)).toBeGreaterThanOrEqual(2);
});
test.afterEach(async()=>{expect(hash(fixture.audio_path)).toBe(fixture.audio_sha256);expect(hash(fixture.prediction_path)).toBe(fixture.prediction_sha256);});

test('draft, full source audio, bounded layout and distinct prediction layers',async({page,request},info)=>{
  const r=await page.evaluate(()=>state.reference);expect(r.origin.kind).toBe('model_assisted_draft');expect(r.review.status).toBe('draft');expect(r.origin.seed_prediction_id).toBeTruthy();
  expect(await page.locator('#reference-reviewed').isChecked()).toBe(false);
  await expect(page.locator('#exports a[data-export-type="json"]')).toHaveText('Saved reference JSON');
  expect(await page.locator('#exports a[data-export-type="midi"]').isVisible()).toBe(false);
  const exported=await (await request.get(base+await page.locator('#exports a[data-export-type="json"]').getAttribute('href'))).json();expect(exported.id).toBe(r.id);expect(exported.notes).toEqual(await notes(page));
  expect(await page.locator('#audio').getAttribute('src')).toContain('/api/source-audio');
  const audio=await request.get(base+'/api/source-audio?id='+fixture.analysis);expect(crypto.createHash('sha256').update(await audio.body()).digest('hex')).toBe(fixture.audio_sha256);
  const layout=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth,roll:document.querySelector('#roll-viewport').getBoundingClientRect().toJSON(),height:innerHeight}));
  expect(layout.scroll).toBeLessThanOrEqual(layout.width);expect(layout.roll.height).toBeGreaterThan(200);expect(layout.roll.bottom).toBeLessThan(layout.height);
  await page.screenshot({path:`.cache/editor-tests/editor-${info.project.name}.png`,fullPage:true});
});
test('direct move commits only on release, preserves fractional pitch and correct note identity',async({page})=>{
  const before=await notes(page),n=before[0],b=await block(page,n.id).boundingBox(),g=await page.evaluate(()=>pianoEditor.geometry());
  await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2+15,b.y+b.height/2-g.row,{steps:6});
  expect(await notes(page)).toEqual(before);await page.mouse.up();const after=await notes(page);
  expect(after[0].id).toBe(n.id);expect(after[0].pitch).toBeCloseTo(n.pitch+1,8);expect(after[0].start).toBeGreaterThan(n.start);expect(after.slice(1)).toEqual(before.slice(1));
  await page.locator('#undo').click();expect(await notes(page)).toEqual(before);await page.locator('#redo').click();expect(await notes(page)).toEqual(after);
});
test('resize clamps neighbours and source bounds, with undo/redo',async({page})=>{
  const before=await notes(page),n=before[0];await drag(page,n.id,1000,0,'end');const after=await notes(page);
  expect(after[0].end).toBeCloseTo(after[1].start,8);expect(after[0].end).toBeGreaterThan(after[0].start);
  await page.locator('#undo').click();expect(await notes(page)).toEqual(before);await page.locator('#redo').click();expect(await notes(page)).toEqual(after);
  await drag(page,n.id,-1000,0,'start');expect((await notes(page))[0].start).toBeCloseTo(.1,8);
});
test('split, compatible merge, delete, drawing and undo/redo use the same edit history',async({page})=>{
  const before=await notes(page),first=before[0];await select(page,first.id);
  const p=await page.evaluate(t=>({x:pianoEditor.x(t),rect:pianoEditor.roll.getBoundingClientRect().toJSON()}),(first.start+first.end)/2);
  await page.mouse.click(p.rect.x+p.x,p.rect.y+40);await page.locator('#split').click();expect((await notes(page)).length).toBe(before.length+1);
  await page.locator('#undo').click();expect(await notes(page)).toEqual(before);await page.locator('#redo').click();
  const split=await notes(page);await select(page,split[0].id);await select(page,split[1].id,['Shift']);await page.locator('#merge').click();expect((await notes(page)).length).toBe(before.length);
  expect((await notes(page))[0].pitch).toBeCloseTo(first.pitch,8);await page.locator('#undo').click();expect((await notes(page)).length).toBe(before.length+1);
  await page.locator('#redo').click();await select(page,first.id);await page.locator('#delete').click();expect((await notes(page)).length).toBe(before.length-1);await page.locator('#undo').click();
  const ns=await notes(page),a=ns[0].end+.02,b=ns[1].start-.02;
  await page.locator('#edit-tool').selectOption('draw');const pos=await page.evaluate(([a,b])=>{const r=pianoEditor.roll.getBoundingClientRect();return {a:{x:r.x+pianoEditor.x(a),y:r.y+pianoEditor.y(70)},b:{x:r.x+pianoEditor.x(b),y:r.y+pianoEditor.y(70)}};},[a,b]);
  await gesture(page,pos.a,pos.b);expect((await notes(page)).length).toBe(before.length+1);const drawn=await notes(page);await page.locator('#undo').click();expect(await notes(page)).toEqual(ns);await page.locator('#redo').click();expect(await notes(page)).toEqual(drawn);
});
test('multi-selection moves two notes and region uncertainty has undo/redo',async({page})=>{
  const before=await notes(page);await select(page,before[0].id);await select(page,before[1].id,['Shift']);
  const g=await page.evaluate(()=>pianoEditor.geometry());await drag(page,before[0].id,0,-g.row);
  const after=await notes(page);expect(after[0].pitch).toBeCloseTo(before[0].pitch+1,8);expect(after[1].pitch).toBeCloseTo(before[1].pitch+1,8);expect(after[2]).toEqual(before[2]);
  await page.locator('#uncertainty-reason').fill('Disposable fixture ambiguity');await page.locator('#mark-uncertain').click();expect((await regions(page)).length).toBe(1);
  await page.locator('#undo').click();expect(await regions(page)).toEqual([]);await page.locator('#redo').click();expect((await regions(page)).length).toBe(1);expect(await page.locator('#reference-reviewed').isChecked()).toBe(false);
});
test('pitch keyboard stays aligned after time/pitch zoom and middle pan',async({page})=>{
  const n=(await notes(page))[1],alignment=async()=>{
    const key=await page.locator(`.piano-key[data-pitch="${Math.round(n.pitch)}"]`).boundingBox(),note=await block(page,n.id).boundingBox();
    expect(Math.abs((key.y+key.height/2)-(note.y+note.height/2))).toBeLessThan(1.5);
  };
  await alignment();const box=await page.locator('#roll-viewport').boundingBox();await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);
  await page.keyboard.down('Control');await page.mouse.wheel(0,-130);await page.keyboard.up('Control');await page.waitForTimeout(80);await alignment();
  await page.keyboard.down('Alt');await page.mouse.wheel(0,-80);await page.keyboard.up('Alt');await page.waitForTimeout(80);await alignment();
  const old=await page.evaluate(()=>({...pianoEditor.view}));await gesture(page,{x:box.x+box.width*.6,y:box.y+box.height*.6},{x:box.x+box.width*.6-30,y:box.y+box.height*.6+8},'middle');
  const now=await page.evaluate(()=>({...pianoEditor.view}));expect(now.low).not.toBe(old.low);expect((await notes(page))[1]).toEqual(n);
});
test('saved reference edits survive refresh; revision restore appends an unreviewed revision',async({page,request})=>{
  const before=await notes(page),ref=await page.evaluate(()=>({id:state.reference.id,revision:state.reference.revision}));
  await select(page,before[0].id);await page.locator('#pitch-up').click();await saved(page);const edited=await notes(page);await page.reload();await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');expect(await notes(page)).toEqual(edited);
  await page.locator('#reference-tools>summary').click();await expect(page.locator(`#revision-list option[value="${ref.revision}"]`)).toHaveCount(1);await page.locator('#revision-list').selectOption(ref.revision);await page.locator('#restore-revision').click();await expect(page.locator('#status')).toContainText('Restored as a new revision');expect(await notes(page)).toEqual(before);
  const revisions=await (await request.get(base+'/api/reference-history?reference_id='+ref.id)).json();expect(revisions.length).toBeGreaterThan(3);expect(revisions[0].review.status).toBe('draft');expect(revisions[0].restored_from_revision).toBe(ref.revision);expect(revisions.some(r=>r.revision===ref.revision)).toBe(true);
});
test('working corrections and reference histories stay independent',async({page,request})=>{
  const ref=await page.evaluate(()=>({id:state.reference.id,revision:state.reference.revision,notes:JSON.parse(JSON.stringify(state.notes))}));
  await page.locator('#reference-working').click();await expect(page.locator('#exports a[data-export-type="midi"]')).toBeVisible();const original=await notes(page);await select(page,original[0].id);await page.locator('#pitch-up').click();await saved(page);const corrected=await notes(page);
  await page.reload();await expect(page.locator('#mode-badge')).toContainText('Working');await expect(page.locator('.note-block')).toHaveCount(corrected.length);expect(await notes(page)).toEqual(corrected);
  const stored=await (await request.get(base+'/api/reference?reference_id='+ref.id)).json();expect(stored.revision).toBe(ref.revision);expect(stored.notes).toEqual(ref.notes);
  await page.locator('#reference-list').selectOption(ref.id);await page.locator('#reference-load').click();await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');expect(await notes(page)).toEqual(ref.notes);
  const history=await (await request.get(base+'/api/correction-history?id='+fixture.analysis)).json();expect(history.length).toBeGreaterThan(0);expect(history[0].notes).toEqual(corrected);
});
test('review queue uses measurable disagreement, never verifies references automatically',async({page})=>{
  await page.locator('#review-tools>summary').click();await expect(page.locator('#review-count')).toContainText('1 alternatives');await expect(page.locator('.review-item').first()).toBeVisible();
  expect(await page.locator('#review-queue').innerText()).toContain('Disagreement');await page.locator('.review-item').first().click();await page.locator('#confirm-note').click();
  expect((await notes(page)).some(n=>n.flags.includes('review_confirmed'))).toBe(true);expect(await page.locator('#reference-reviewed').isChecked()).toBe(false);
  await page.locator('#undo').click();expect((await notes(page)).some(n=>n.flags.includes('review_confirmed'))).toBe(false);
});
test('piano keys generate measured A4 and A sharp frequencies without starting vocal audio',async({page},info)=>{
  await page.locator('.piano-key[data-pitch="69"]').click();await page.waitForTimeout(220);const a=await signal(page,'piano');expect(a.last_tone.frequency).toBe(440);expect(Math.abs(a.peak_hz-440)).toBeLessThan(3);expect(a.rms).toBeGreaterThan(.001);expect(await page.locator('#audio').evaluate(a=>a.paused)).toBe(true);
  await page.locator('.piano-key[data-pitch="70"]').click();await page.waitForTimeout(250);const sharp=await signal(page,'piano');expect(sharp.last_tone.frequency).toBeCloseTo(466.1638,3);expect(Math.abs(sharp.peak_hz-466.1638)).toBeLessThan(3);await info.attach('measured-reference-audio',{body:JSON.stringify({A4:a,Asharp4:sharp}),contentType:'application/json'});
});
test('vocal segment audition uses edited source boundaries with preroll/postroll and loop',async({page},info)=>{
  let n=(await notes(page))[0];await select(page,n.id);await page.locator('#inspect-start').fill(String(n.start+.01));await page.locator('#inspect-start').press('Tab');await saved(page);await page.reload();await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');n=(await notes(page))[0];await select(page,n.id);await page.locator('#audition-mode').selectOption('vocal');await page.locator('#audition-selected').click();await page.waitForTimeout(180);
  const s=await signal(page,'vocal');expect(s.segment.start).toBeCloseTo(Math.max(0,n.start-.06),8);expect(s.segment.end).toBeCloseTo(n.end+.08,8);expect(s.rms).toBeGreaterThan(.005);expect(Math.abs(s.peak_hz-440)).toBeLessThan(5);
  await page.locator('#stop').click();await page.locator('#loopselected').click();await page.waitForTimeout(1100);const loop=await page.evaluate(()=>({time:document.querySelector('#audio').currentTime,paused:document.querySelector('#audio').paused,segment:pianoEditor.audition.segment}));
  expect(loop.paused).toBe(false);expect(loop.segment.loop).toBe(true);expect(loop.time).toBeGreaterThanOrEqual(loop.segment.start);expect(loop.time).toBeLessThan(loop.segment.end+.07);await page.locator('#stop').click();await info.attach('measured-vocal-audio',{body:JSON.stringify(s),contentType:'application/json'});
});
test('Both mode has one vocal source, simultaneous audible buses and independent volumes',async({page},info)=>{
  const n=(await notes(page))[0];await select(page,n.id);await page.locator('#audition-mode').selectOption('both');await page.locator('#loop').check();await page.locator('#audition-selected').click();await page.waitForTimeout(220);
  const piano=await signal(page,'piano'),vocal=await signal(page,'vocal');expect(piano.rms).toBeGreaterThan(.001);expect(vocal.rms).toBeGreaterThan(.005);expect(vocal.media_sources).toBe(1);expect(Math.abs(piano.last_tone.frequency-440*2**((n.pitch-69)/12))).toBeLessThan(.00001);
  await page.locator('#piano-volume').press('Home');await page.waitForTimeout(250);const mutedPiano=await signal(page,'piano'),stillVocal=await signal(page,'vocal');expect(mutedPiano.piano_gain).toBeLessThan(.0001);expect(mutedPiano.vocal_gain).toBeCloseTo(.8,4);expect(mutedPiano.rms).toBeLessThan(.0001);expect(stillVocal.rms).toBeGreaterThan(.005);
  await page.locator('#vocal-volume').press('Home');await page.waitForTimeout(240);const mutedBoth=await signal(page,'vocal');expect(mutedBoth.vocal_gain).toBeLessThan(.0001);expect(mutedBoth.piano_gain).toBeLessThan(.0001);expect(mutedBoth.rms).toBeLessThan(.0001);expect(await page.locator('#audio').evaluate(a=>a.paused)).toBe(false);expect(mutedBoth.segment.loop).toBe(true);await page.locator('#stop').click();await info.attach('both-buses',{body:JSON.stringify({piano,vocal,mutedPiano,stillVocal,mutedBoth}),contentType:'application/json'});
});
test('slow playback preserves source timestamps and requested pitch, with synchronized playhead',async({page},info)=>{
  const before=await notes(page),n=before[0];await select(page,n.id);await page.locator('#audition-mode').selectOption('vocal');await page.locator('#speed').selectOption('.5');await page.locator('#audition-selected').click();await page.waitForTimeout(400);
  const s=await signal(page,'vocal');expect(s.speed).toBe(.5);expect(Math.abs(s.peak_hz-440)).toBeLessThan(6);expect(await notes(page)).toEqual(before);
  const cursor=await page.evaluate(()=>({actual:parseFloat(document.querySelector('#playhead').style.left),expected:pianoEditor.x(document.querySelector('#audio').currentTime),preserves:document.querySelector('#audio').preservesPitch}));expect(cursor.preserves).toBe(true);expect(Math.abs(cursor.actual-cursor.expected)).toBeLessThan(8);
  await page.locator('#stop').click();await page.locator('#speed').selectOption('.75');await page.locator('#audition-selected').click();await page.waitForTimeout(300);const threeQuarter=await signal(page,'vocal');expect(Math.abs(threeQuarter.peak_hz-440)).toBeLessThan(6);expect(threeQuarter.speed).toBe(.75);expect(await notes(page)).toEqual(before);await page.locator('#stop').click();await info.attach('slow-vocal-measurement',{body:JSON.stringify({half:s,threeQuarter}),contentType:'application/json'});
});
test('Vocal keyboard fallback is explicit and Space plays complete original audio in Piano mode',async({page})=>{
  await page.locator('#audition-mode').selectOption('vocal');await page.locator('.piano-key[data-pitch="70"]').click();await expect(page.locator('#audition-status')).toContainText('piano reference fallback');
  await page.locator('#audition-mode').selectOption('piano');await page.locator('#roll-viewport').focus();await page.keyboard.press('Space');await expect.poll(()=>page.locator('#audio').evaluate(a=>a.paused)).toBe(false);await expect(page.locator('#audition-status')).toContainText('Complete original');await page.keyboard.press('Space');expect(await page.locator('#audio').evaluate(a=>a.paused)).toBe(true);
});
test('Escape cancels a drag without symbolic changes or an extra history step',async({page})=>{
  const before=await notes(page),b=await block(page,before[0].id).boundingBox(),count=await page.evaluate(()=>pianoEditor.history.undo.length);
  await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2+12,b.y+b.height/2-12,{steps:5});await page.keyboard.press('Escape');await page.mouse.up();
  expect(await notes(page)).toEqual(before);expect(await page.evaluate(()=>pianoEditor.history.undo.length)).toBe(count);
});
test('A/B plays original vocal then reference, with no vocal pitch-shift claim',async({page},info)=>{
  const n=(await notes(page))[0];await select(page,n.id);await page.locator('#audition-ab').click();await expect(page.locator('#audition-status')).toContainText('Original vocal');
  await expect(page.locator('#audition-status')).toContainText('Piano reference',{timeout:3000});await page.waitForTimeout(220);const a=await signal(page,'piano');expect(a.last_tone.frequency).toBeCloseTo(440*2**((n.pitch-69)/12),6);expect(a.rms).toBeGreaterThan(.001);expect(Math.abs(a.peak_hz-a.last_tone.frequency)).toBeLessThan(3);expect(await page.locator('#audio').evaluate(a=>a.paused)).toBe(true);await info.attach('A-B-sequence',{body:JSON.stringify(a),contentType:'application/json'});
});
test('working revision restore appends a correction and review attestation clears on note edits',async({page,request})=>{
  await page.locator('#reference-tools>summary').click();await page.locator('#reference-reviewed').check();const initial=await notes(page);await select(page,initial[0].id);await page.locator('#pitch-up').click();expect(await page.locator('#reference-reviewed').isChecked()).toBe(false);await page.locator('#undo').click();
  // No fabricated listening attestation is saved, even on this disposable fixture.
  await saved(page);await page.locator('#reference-working').click();const old=await notes(page);await select(page,old[0].id);await page.locator('#pitch-up').click();await saved(page);
  const one=await page.evaluate(()=>state.report.provenance.correction_revision),first=await notes(page);await page.locator('#pitch-up').click();await saved(page);
  if(!await page.locator('#reference-tools').evaluate(e=>e.open))await page.locator('#reference-tools>summary').click();await page.locator('#revision-list').selectOption(one);await page.locator('#restore-revision').click();await expect(page.locator('#status')).toContainText('Restored as a new revision');expect(await notes(page)).toEqual(first);
  const rows=await (await request.get(base+'/api/correction-history?id='+fixture.analysis)).json();expect(rows[0].revision).not.toBe(one);
});
test('range tool and missing-note queue windows remain source-aligned without inventing labels',async({page})=>{
  const before=await notes(page);await page.locator('#edit-tool').selectOption('range');const pos=await page.evaluate(()=>{const r=pianoEditor.roll.getBoundingClientRect();return {a:{x:r.x+pianoEditor.x(.4),y:r.y+pianoEditor.y(76)},b:{x:r.x+pianoEditor.x(1.1),y:r.y+pianoEditor.y(76)}};});
  await gesture(page,pos.a,pos.b);expect(+await page.locator('#loopstart').inputValue()).toBeCloseTo(.4,2);expect(+await page.locator('#loopend').inputValue()).toBeCloseTo(1.1,2);expect(await notes(page)).toEqual(before);
  // Deleting a fixture event produces an alternative-only review window, never an automatic replacement.
  await page.locator('#edit-tool').selectOption('select');await select(page,before[0].id);await page.locator('#delete').click();await page.locator('#review-tools>summary').click();await expect(page.locator('#review-queue')).toContainText('Possible missing event');expect((await notes(page)).length).toBe(before.length-1);
});
test('review suggestions are confined to a short reference excerpt',async({page,request})=>{
  const ref=await post(request,'reference-create',{id:fixture.analysis,start:1.8,end:2.7,
    annotator:'SYNTHETIC SHORT EXCERPT TEST — NOT HUMAN LABELS',split:'development',song_group:'disposable-editor-fixture',seed:true});
  await page.reload();await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');await page.locator('#reference-list').selectOption(ref.id);await page.locator('#reference-load').click();await expect(page.locator('#guide')).toContainText('1.800–2.700');
  expect(await page.evaluate(()=>pianoEditor.queue.every(r=>r.start>=1.8-1e-8&&r.end<=2.7+1e-8))).toBe(true);
});
test('raw predicted notes can be auditioned without populating a blank human reference',async({page,request})=>{
  const ref=await post(request,'reference-create',{id:fixture.analysis,start:.1,end:fixture.duration-.1,
    annotator:'SYNTHETIC BLANK REFERENCE TEST — NOT HUMAN LABELS',split:'development',song_group:'disposable-editor-fixture',seed:false});
  await page.goto(`/?analysis=${fixture.analysis}&reference=${ref.id}`);await expect(page.locator('#mode-badge')).toContainText('UNREVIEWED');await expect(page.locator('.note-block')).toHaveCount(0);
  const p=await page.evaluate(()=>{const n=state.report.predicted_notes[0],r=pianoEditor.roll.getBoundingClientRect();return {id:n.id,x:r.x+pianoEditor.x((n.start+n.end)/2),y:r.y+pianoEditor.y(n.pitch)};});
  await page.mouse.click(p.x,p.y);await expect(page.locator('#selection-summary')).toContainText('Raw model prediction');expect(await page.locator('#inspect-pitch').isDisabled()).toBe(true);
  await page.locator('#audition-mode').selectOption('vocal');await page.locator('#audition-selected').click();await page.waitForTimeout(150);expect((await signal(page,'vocal')).segment.note.id).toBe(p.id);expect(await notes(page)).toEqual([]);await page.locator('#stop').click();
});
