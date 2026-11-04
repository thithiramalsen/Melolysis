/* Read-only real-application captures. Never save, edit, play or attest MHS. */
const fs=require('node:fs'),path=require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.resolve('.cache/ms-playwright');
const {chromium}=require('playwright');
(async()=>{
  const target=JSON.parse(fs.readFileSync('.cache/ux/mhs-open.json','utf8'));
  const url=new URL(target.url);if(url.hostname!=='127.0.0.1')throw Error('Local only');
  fs.mkdirSync('outputs/ux',{recursive:true});const browser=await chromium.launch({headless:true,args:['--mute-audio','--disable-gpu']});const checks=[];
  try{for(const [width,height] of [[1366,768],[1920,1080]]){
    const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(target.url);await page.waitForFunction(()=>document.querySelectorAll('.note-block').length===11&&state.reference?.review.status==='draft');await page.waitForFunction(()=>document.querySelector('#audio').readyState>=2);
    await page.locator('#auto-audition').uncheck();await page.locator('.note-block').first().click();await page.locator('#auto-audition').check();
    const group=page.locator('.recording-group.current');await group.locator('.versions-toggle').click();
    const check=await page.evaluate(()=>{const roll=pianoEditor.roll.getBoundingClientRect();return {reference:state.reference.id,revision:state.reference.revision,
      notes:state.notes.length,review:state.reference.review.status,attestation:document.querySelector('#reference-reviewed').checked,audio_paused:document.querySelector('#audio').paused,dirty:pianoEditor.dirty,
      view:{...pianoEditor.view},excerpt:state.reference.excerpt,viewport:[innerWidth,innerHeight],bottom_collapsed:document.querySelector('#bottom-inspector').hidden,
      source_groups:state.recordings.length,analysis_versions:state.library.length,corpus_selected:state.selected.size,
      visible_events:[...document.querySelectorAll('.note-block')].filter(e=>{const b=e.getBoundingClientRect();return b.top>=roll.top+88&&b.bottom<=roll.bottom-22&&b.left>=roll.left+68&&b.right<=roll.right+1;}).length,
      page_width:document.documentElement.scrollWidth,roll:roll.toJSON()};});
    if(check.dirty||check.attestation||!check.audio_paused||check.notes!==11||check.visible_events!==11||check.view.start!==.5||check.view.length!==6||!check.bottom_collapsed||check.page_width>width||errors.length)throw Error(JSON.stringify({check,errors}));
    const file=`outputs/ux/mhs-${width}x${height}.png`;await page.screenshot({path:file});
    await page.locator('#bottom-toggle').click();await page.locator('#tab-history').click();await page.screenshot({path:`outputs/ux/mhs-history-${width}x${height}.png`});
    checks.push({...check,file,console_errors:errors});await context.close();
  }}finally{await browser.close();}
  fs.writeFileSync('outputs/ux/read-only-review-checks.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
})().catch(e=>{console.error(e);process.exit(1);});
