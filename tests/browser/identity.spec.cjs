const {test,expect}=require('@playwright/test');
test('two sources: correspondence, original A/B signals, pause/resume and independent idea',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 await page.locator('[data-tab="style"]').click();await expect(page.locator('#identity-a option')).not.toHaveCount(0);
 await page.locator('#identity-find').click();await expect(page.locator('#identity-detail')).toBeVisible();
 const run=await page.evaluate(()=>identityWorkspace.run);expect(run.sources[0].source_hash).not.toBe(run.sources[1].source_hash);expect(run.matches[0].matched_targets).toBeGreaterThanOrEqual(4);
 await page.locator('#identity-operations button').first().click();await expect(page.locator('#identity-roll-a .highlighted')).toHaveCount(1);await expect(page.locator('#identity-roll-b .highlighted')).toHaveCount(1);
 const signals=[];
 for(const side of ['a','b']){await page.locator('#identity-play-'+side).click();await expect.poll(()=>page.locator('#audio').evaluate(a=>!a.paused)).toBe(true);await page.waitForTimeout(160);
 signals.push(await page.evaluate(()=>{const p=pianoEditor.audition,x=new Float32Array(p.vocalMeter.fftSize);p.vocalMeter.getFloatTimeDomainData(x);return Math.sqrt(x.reduce((s,v)=>s+v*v,0)/x.length);}));
 expect(signals.at(-1)).toBeGreaterThan(.0001);expect(await page.locator('#audio').getAttribute('src')).toContain(run.matches[0][side].analysis_id);
 await page.locator('#identity-play-'+side).click();const t=await page.locator('#audio').evaluate(a=>a.currentTime);await page.waitForTimeout(100);expect(await page.locator('#audio').evaluate(a=>a.currentTime)).toBeCloseTo(t,5);
 await page.locator('#identity-play-'+side).click();await page.waitForTimeout(100);expect(await page.locator('#audio').evaluate(a=>a.currentTime)).toBeGreaterThan(t);await page.locator('#identity-stop').click();}
 await page.locator('#identity-normalize').uncheck();expect(await page.evaluate(()=>identityWorkspace.rolls[0].start)).toBe(run.matches[0].a.start);
 await page.locator('#identity-learn').click();await expect(page.locator('#compose')).toBeVisible();expect(await page.evaluate(()=>learning.ideaNotes.length)).toBe(0);await expect(page.locator('#idea-technique')).toContainText('own');
 expect(await page.evaluate(()=>learning.link.study.identity_evidence.run_id)).toBe(run.id);
 for(const [a,b,p]of [[0,.75,60],[1,1.75,64],[2,2.75,62]]){await page.locator('#idea-roll').scrollIntoViewIfNeeded();const points=await page.evaluate(([a,b,p])=>{const r=learning.ideaRoll,g=r.node.getBoundingClientRect();return [[g.x+r.x(a),g.y+r.y(p)],[g.x+r.x(b),g.y+r.y(p)]];},[a,b,p]);await page.mouse.move(...points[0]);await page.mouse.down();await page.mouse.move(...points[1],{steps:5});await page.mouse.up();}
 expect(await page.evaluate(()=>learning.ideaNotes.length)).toBe(3);await page.locator('#idea-save').click();await expect(page.locator('#idea-midi')).toBeVisible();const idea=await page.evaluate(()=>learning.idea.id);await page.goto('/?idea='+idea);await expect(page.locator('#idea-midi')).toBeVisible();expect(await page.evaluate(()=>learning.ideaNotes.length)).toBe(3);expect(await page.evaluate(()=>learning.idea.link.identity_evidence.run_id)).toBe(run.id);expect(errors).toEqual([]);
 await info.attach('original-source-signal-RMS',{body:JSON.stringify(signals),contentType:'application/json'});
});
