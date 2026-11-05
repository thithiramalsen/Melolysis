/* Preserve real Playwright results and measured bus signals, without test fixture/audio files. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const source='.cache/editor-tests/browser-results.json',results=JSON.parse(fs.readFileSync(source,'utf8'));
if(!results.stats.expected||results.stats.unexpected||results.stats.flaky||results.stats.skipped)throw Error('Archive only a complete passing, unskipped browser run.');
const tests=[],audio=[];
function collect(suite){
  for(const spec of suite.specs||[])for(const test of spec.tests)for(const result of test.results){
    tests.push({name:spec.title,viewport:test.projectName,status:result.status,duration_ms:result.duration});
    for(const item of result.attachments||[])if(item.contentType==='application/json'&&item.body)
      audio.push({test:spec.title,viewport:test.projectName,measurement:item.name,data:JSON.parse(Buffer.from(item.body,'base64').toString('utf8'))});
  }
  for(const child of suite.suites||[])collect(child);
}
for(const suite of results.suites)collect(suite);
if(tests.length!==results.stats.expected||tests.some(t=>t.status!=='passed'))throw Error('Incomplete browser result records');
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const files=['src/web/editor-core.js','src/web/editor.js','src/web/audition.js','src/web/app.js','src/web/index.html','src/web/style.css',
  'src/references.py','src/storage.py','src/workspace.py','tests/browser/editor.spec.cjs','package-lock.json'];
const contextual=process.argv.includes('--contextual');
const transport=process.argv.includes('--transport');
const learning=process.argv.includes('--learning')||transport;
if(contextual)files.push('src/library.py','src/web/library.js','tests/test_library.py','tools/editor_test_server.py');
if(learning)files.push('src/learning.py','src/learning_store.py','src/web/learning.js','src/web/learning-roll.js','src/web/learning.css','src/web/library.js','tests/test_learning.py','tests/browser/learning.spec.cjs','tools/editor_test_server.py');
if(transport)files.push('tests/browser/transport.spec.cjs');
const output=transport?'docs/transport':learning?'docs/learning':contextual?'docs/ux':'docs/editor';fs.mkdirSync(output,{recursive:true});
fs.writeFileSync(path.join(output,'browser-validation.json'),JSON.stringify({date:transport?'2026-11-05':'2026-11-04',runner:'@playwright/test 1.64.1',
  node:process.version,stats:results.stats,tests,source_sha256:Object.fromEntries(files.map(p=>[p,sha(p)])),
  scope:'Headless Chromium, speakers muted; one worker; disposable synthetic audio and references only; no user annotations created/reviewed',
  limitation:'Actual oscillator and decoded media signals measured internally; no acoustic output/device-latency or perceptual singing-quality validation'},null,2));
fs.writeFileSync(path.join(output,'audio-measurements.json'),JSON.stringify({fft_size:8192,measurements:audio,
  interpretation:'Frequency bins have finite resolution. RMS after muting tests bus output, not just UI volume values. Mute tests keep vocal transport running. These are routing tests, not real-vocal transcription accuracy.'},null,2));
for(const size of ['1366x768','1920x1080'])fs.copyFileSync(`.cache/editor-tests/editor-${size}.png`,path.join(output,`fixture-${size}.png`));
if(learning)for(const size of ['1366x768','1920x1080'])for(const stage of ['study','compose'])fs.copyFileSync(`.cache/editor-tests/learning-${stage}-${size}.png`,path.join(output,`fixture-${stage}-${size}.png`));
fs.copyFileSync(transport?'.cache/transport/evaluation-regression.json':learning?'.cache/learning/evaluation-regression.json':contextual?'.cache/ux/evaluation-regression.json':'.cache/editor/evaluation-regression.json',path.join(output,'evaluation-regression.json'));
console.log(`Archived ${tests.length} passing browser checks and ${audio.length} actual signal/transport measurements.`);
