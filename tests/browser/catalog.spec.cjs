const {test,expect}=require('@playwright/test');
// This suite only runs against the generated disposable fixture workspace.
async function clearAssociations(request){const headers={Origin:'http://127.0.0.1:8772'};let c=await (await request.post('/api/catalog-get',{headers,data:{}})).json();for(const g of c.recordings.filter(g=>g.category==='personal')){c=await (await request.post('/api/catalog-reconcile',{headers,data:{source_hash:g.source_hash,base_revision:c.revision,artist_ids:[],work_id:null}})).json();}}
test.beforeEach(async({request})=>clearAssociations(request));
test.afterEach(async({request})=>clearAssociations(request));
test('catalog reconciliation previews, groups takes, pins input and preserves editor/audio',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 await expect(page.locator('.catalog-associate').first()).toBeVisible();
 const groups=await page.evaluate(()=>state.recordings.filter(g=>g.category==='personal'));
 const sources=groups.map(g=>g.source_hash);
 const post=(route,data)=>page.evaluate(async([route,data])=>{const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const v=await r.json();if(!r.ok)throw Error(v.error);return v;},[route,data]);
 try{
 await page.locator('.recording-title').first().click();await expect(page.locator('#study-roll')).toBeVisible();
 const initial=await page.evaluate(()=>({id:state.id,notes:state.notes,selection:learning.selection}));
 await page.locator('#study-play-song').click();await page.waitForTimeout(200);
 await page.locator('.catalog-associate').first().click();await expect(page.locator('#catalog-dialog')).toBeVisible();
 const beforeCatalog=await post('catalog-get',{});const singer='CATALOG TEST SINGER '+info.project.name;
 await page.locator('#catalog-new-artist').fill(singer);await page.locator('#catalog-new-work').fill('CATALOG TEST WORK');await page.locator('#catalog-take').fill('Take 1');
 await page.locator('#catalog-preview').click();await expect(page.locator('#catalog-result')).toContainText('No files written');
 expect((await post('catalog-get',{})).artists).toEqual(beforeCatalog.artists);
 await page.locator('#catalog-save').click();await expect(page.locator('#catalog-result')).toContainText('Associations saved');
 let c=await post('catalog-get',{});const artist=Object.values(c.artists).find(a=>a.name===singer).id,work=c.associations[await page.locator('#catalog-recording').inputValue()].work_id;
 const first=await page.locator('#catalog-recording').inputValue();const second=sources.find(s=>s!==first);
 await page.locator('#catalog-recording').selectOption(second);await expect(page.locator('#catalog-artists')).toHaveValue('');await expect(page.locator('#catalog-artists option:checked')).toHaveText('Unresolved artist — choose one');
 await page.locator('#catalog-recording').selectOption(second);await page.locator('#catalog-artists').selectOption([artist]);await page.locator('#catalog-work').selectOption(work);await page.locator('#catalog-take').fill('Take 2');await page.locator('#catalog-save').click();await expect(page.locator('#catalog-result')).toContainText('1 confirmed works');
 const third=sources.find(s=>s!==first&&s!==second);await page.locator('#catalog-recording').selectOption(third);await page.locator('#catalog-artists').selectOption([artist]);await page.locator('#catalog-new-work').fill('SECOND DISTINCT WORK');await page.locator('#catalog-save').click();await expect(page.locator('#catalog-result')).toContainText('2 confirmed works');
 const preserved=await page.evaluate(()=>({id:state.id,notes:state.notes,selection:learning.selection}));expect(preserved).toEqual(initial);
 expect(await page.locator('#audio').evaluate(a=>a.paused)).toBe(false);
 const rms=await page.evaluate(()=>{const p=pianoEditor.audition,x=new Float32Array(p.vocalMeter.fftSize);p.vocalMeter.getFloatTimeDomainData(x);return Math.sqrt(x.reduce((s,v)=>s+v*v,0)/x.length);});expect(rms).toBeGreaterThan(.0001);
 await page.screenshot({path:`.cache/m0-catalog-${info.project.name}.png`});
 await page.locator('#catalog-dialog button[value=cancel]').click();await page.locator('#study-stop').click();await page.locator('[data-tab=style]').click();await page.locator('#corpus-all').click();await expect(page.locator('#corpus-count')).toContainText('2 confirmed works');
 await page.reload();await expect(page.locator('.recording-info').filter({hasText:'CATALOG TEST SINGER'})).toHaveCount(3);
 await page.locator('.catalog-associate').first().click();await page.locator('#catalog-recording').selectOption(second);await expect(page.locator('#catalog-artists')).toHaveValue(artist);await expect(page.locator('#catalog-work')).toHaveValue(work);await page.locator('#catalog-dialog button[value=cancel]').click();
 c=await post('catalog-get',{});const ids=c.recordings.filter(g=>g.category==='personal').map(g=>g.preferred_analysis);const snap=await post('corpus-save',{ids,catalog_revision:c.revision});expect(snap.counts.works).toBe(2);expect(snap.entries.length).toBe(3);expect(await post('corpus-get',{id:snap.id})).toEqual(snap);
 expect(errors).toEqual([]);await info.attach('catalog-audio-check',{body:JSON.stringify({rms,snapshot:snap.id}),contentType:'application/json'});
 }finally{for(const source of sources){const c=await post('catalog-get',{});await post('catalog-reconcile',{source_hash:source,base_revision:c.revision,artist_ids:[],work_id:null});}}
});
