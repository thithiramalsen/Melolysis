/* Real MHS workflow capture. Only new learning snapshots/demo ideas are written.
   No correction/reference/model/source audio write is permitted. Speakers muted. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.resolve('.cache/ms-playwright');
const {chromium}=require('playwright');const base='http://127.0.0.1:8775';
const analysis='5fb48b6259d2a98d40c651bcbe3ea15420284cd49d9e6a8a62cd4deae598cf6e';
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
async function draw(page,a,b,pitch){const points=await page.evaluate(([a,b,p])=>{const roll=learning.ideaRoll,r=roll.node.getBoundingClientRect();return [[r.x+roll.x(a),r.y+roll.y(p)],[r.x+roll.x(b),r.y+roll.y(p)]];},[a,b,pitch]);await page.mouse.move(...points[0]);await page.mouse.down();await page.mouse.move(...points[1],{steps:6});await page.mouse.up();}
async function signal(page,bus){return page.evaluate(bus=>{const a=pianoEditor.audition,m=bus==='piano'?a.pianoMeter:a.vocalMeter,s=new Float32Array(m.fftSize);m.getFloatTimeDomainData(s);return {rms:Math.sqrt(s.reduce((sum,v)=>sum+v*v,0)/s.length),segment:a.segment,sequence:a.sequenceInfo,source_time:a.audio.currentTime};},bus);}
(async()=>{fs.mkdirSync('outputs/learning-demo',{recursive:true});const snapshot=JSON.parse(fs.readFileSync('.cache/learning/protected-before.json','utf8'));const previous=fs.existsSync('.cache/learning/mhs-journey.json')?JSON.parse(fs.readFileSync('.cache/learning/mhs-journey.json','utf8')):null;let saved=previous?{id:new URL(previous.idea_url).searchParams.get('idea')}:null;const checks=[];
  const browser=await chromium.launch({headless:true,args:['--mute-audio','--disable-gpu']});
  try{for(const [width,height] of [[1366,768],[1920,1080]]){
    const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[],mutations=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')mutations.push(new URL(r.url()).pathname);});
    await page.goto(`${base}/?analysis=${analysis}`);await page.waitForFunction(()=>learning.selection&&document.querySelector('#audio').readyState>=2);await page.locator('#study-analyze').click();await page.waitForFunction(()=>learning.study?.status==='ready');
    const finding=await page.evaluate(()=>learning.study.findings.find(f=>f.kind==='release')||learning.study.findings.find(f=>f.technique));if(!finding)throw Error('No supported technique in actual MHS notes');
    const article=page.locator(`.finding[data-finding-id="${finding.id}"]`);await article.locator('.hear-finding').click();await page.waitForTimeout(200);const vocal=await signal(page,'vocal');if(vocal.rms<=.00001||!vocal.segment)throw Error('Original MHS vocal bus was silent');await page.locator('#study-stop').click();
    await page.screenshot({path:`outputs/learning-demo/mhs-study-${width}x${height}.png`});
    await page.locator('#study-context>summary').click();await page.locator('#study-start').fill('.5');await page.locator('#study-end').fill('6.5');await page.locator('#study-end').press('Tab');await page.locator('#study-context>summary').click();await page.locator('#study-analyze').click();await page.waitForFunction(()=>learning.study?.features?.phrase_count>=2);await page.locator('#study-comparison>summary').click();
    await page.screenshot({path:`outputs/learning-demo/mhs-compare-${width}x${height}.png`});await page.locator('#compare-close').click();
    if(!saved){await page.locator('.try-technique').first().click();await page.locator('#idea-roll').scrollIntoViewIfNeeded();if((await page.evaluate(()=>learning.ideaNotes)).length)throw Error('Source copied into new idea');
      for(const [i,p] of [60,62,65,64,67,64].entries())await draw(page,.25+i,.85+i,p);
      const last=page.locator('#idea-roll .learning-note').last(),box=await last.boundingBox(),row=await page.evaluate(()=>learning.ideaRoll.geom().row);await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2,box.y+box.height/2-row,{steps:5});await page.mouse.up();
      await page.locator('#idea-title').fill('Demonstration · my rising phrase and lower ending');await page.locator('#idea-save').click();await page.waitForFunction(()=>learning.idea&&!learning.dirty);saved=await page.evaluate(()=>learning.idea);
    }else {await page.getByRole('button',{name:'2 · Create melody',exact:true}).click();await page.locator('#idea-list').selectOption(saved.id);await page.waitForFunction(id=>learning.idea?.id===id,saved.id);}
    await page.locator('#idea-play').click();await page.waitForTimeout(350);const piano=await signal(page,'piano');if(piano.rms<=.0001||piano.sequence?.frequencies.length!==6)throw Error('Drawn piano sequence inaudible');await page.locator('#idea-stop').click();
    await page.locator('#compose').evaluate(e=>e.scrollTop=0);await page.screenshot({path:`outputs/learning-demo/mhs-create-${width}x${height}.png`});
    const exportUrl=await page.locator('#idea-midi').getAttribute('href'),midi=await page.request.get(base+exportUrl);if(!midi.ok()||(await midi.body()).subarray(0,4).toString()!=='MThd')throw Error('Edited MIDI unavailable');
    const state=await page.evaluate(()=>({notes:learning.ideaNotes.length,source:learning.link.study.source,idea_id:learning.idea.id,revision:learning.idea.revision,dirty:learning.dirty,page_width:document.documentElement.scrollWidth,viewport:innerWidth}));
    if(errors.length||state.dirty||state.page_width>width||mutations.some(p=>['/api/reference-save','/api/correct','/api/compose','/api/analyze'].includes(p)))throw Error(JSON.stringify({errors,mutations,state}));checks.push({...state,viewport:[width,height],vocal,piano,runtime_errors:errors,mutations,export_url:exportUrl});await context.close();
  }}finally{await browser.close();}
  const changed=Object.entries(snapshot).filter(([p,h])=>hash(p)!==h).map(([p])=>p);if(changed.length)throw Error('Protected data changed: '+JSON.stringify(changed));
  const result={scope:'Real MHS analysis; independent demonstration idea drawn/edited through actual browser gestures, not human performance or ground truth.',url:`${base}/?analysis=${analysis}`,idea_url:`${base}/?analysis=${analysis}&idea=${saved.id}`,protected_files_unchanged:Object.keys(snapshot).length,checks};
  fs.writeFileSync('outputs/learning-demo/journey-checks.json',JSON.stringify(result,null,2));fs.writeFileSync('.cache/learning/mhs-journey.json',JSON.stringify(result,null,2));console.log(JSON.stringify({url:result.url,idea_url:result.idea_url,protected_files_unchanged:result.protected_files_unchanged,viewports:checks.map(c=>c.viewport)}));
})().catch(e=>{console.error(e);process.exit(1);});
