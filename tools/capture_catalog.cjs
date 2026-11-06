/* Read-only check of the actual personal library. Does not reconcile identities. */
const {chromium,expect}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:path.resolve('.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-win64/chrome-headless-shell.exe'),args:['--mute-audio']});
try{fs.mkdirSync('docs/catalog',{recursive:true});const checks=[];for(const width of [1366,1920]){
const page=await browser.newPage({viewport:{width,height:width===1366?768:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8783/');await expect(page.locator('.catalog-associate').first()).toBeVisible();
await page.locator('.catalog-associate').first().click();await expect(page.locator('#catalog-dialog')).toBeVisible();
await expect(page.locator('#catalog-source')).toContainText('unresolved');await page.screenshot({path:`docs/catalog/actual-library-${width}.png`});
checks.push({width,recordings:await page.evaluate(()=>state.recordings.length),personal:await page.evaluate(()=>state.recordings.filter(g=>g.category==='personal').length),errors});expect(errors).toEqual([]);await page.close();}
fs.writeFileSync('docs/catalog/actual-library-checks.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
