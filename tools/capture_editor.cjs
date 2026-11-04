/* Read-only screenshots of the real draft; no audio playback and no annotation save. */
const fs=require('node:fs');const path=require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.resolve('.cache/ms-playwright');
const {chromium}=require('playwright');
(async()=>{
  const target=JSON.parse(fs.readFileSync('.cache/editor/mhs-open.json','utf8'));
  const url=new URL(target.url);if(!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Local workspace only');
  fs.mkdirSync('outputs/editor',{recursive:true});const browser=await chromium.launch({headless:true,args:['--mute-audio','--disable-gpu']});const checks=[];
  try{for(const [width,height] of [[1366,768],[1920,1080]]){
    const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(target.url);await page.waitForFunction(()=>document.querySelector('#mode-badge').textContent.includes('UNREVIEWED')&&document.querySelectorAll('.note-block').length===11);
    await page.waitForFunction(()=>document.querySelector('#audio').readyState>=2);
    await page.locator('.note-block').first().click();
    const state=await page.evaluate(()=>({reference:state.reference.id,revision:state.reference.revision,notes:state.notes.length,
      review:state.reference.review.status,attestation:document.querySelector('#reference-reviewed').checked,audio_paused:document.querySelector('#audio').paused,dirty:pianoEditor.dirty,
      excerpt:state.reference.excerpt,viewport:[innerWidth,innerHeight]}));
    if(state.dirty||state.attestation||!state.audio_paused||state.notes!==11||state.review!=='draft'||errors.length)throw Error('Read-only capture invariant failed');
    const file=`outputs/editor/mhs-${width}x${height}.png`;await page.screenshot({path:file});checks.push({...state,file,console_errors:errors});await context.close();
  }}finally{await browser.close();}
  fs.writeFileSync('outputs/editor/read-only-review-checks.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
})().catch(error=>{console.error(error);process.exit(1);});
