const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
let fixture;
test.beforeAll(()=>fixture=JSON.parse(fs.readFileSync('.cache/editor-tests/current.json','utf8')));

test('real upload and transcription become ready without refresh, and survive reload',async({page})=>{
  test.setTimeout(60000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const originalReport=fs.readFileSync(fixture.report_path);
  try {
  await page.goto('/');
  const name='Uploaded listening fixture '+test.info().project.name+'.wav';
  await page.locator('#files').setInputFiles({name,mimeType:'audio/wav',buffer:fs.readFileSync(fixture.audio_path)});
  const row=page.locator('.import-job').filter({has:page.locator('strong',{hasText:name})}).first();
  await expect(row).toContainText('Ready',{timeout:45000});
  await expect(page.locator('#study-workspace')).toBeVisible();
  const id=await page.evaluate(()=>state.id);expect(id).toBeTruthy();
  const job=await page.evaluate(name=>importQueue.jobs.find(j=>j.name===name),name);
  expect(job.status).toBe('complete');expect(job.analysis_id).toBe(id);
  await page.reload();await expect(row).toContainText('Ready');
  await row.getByRole('button',{name:'Open song'}).click();
  await expect(page.locator('#study-workspace')).toBeVisible();
  expect(await page.evaluate(()=>state.id)).toBe(id);
  expect(errors).toEqual([]);
  } finally {fs.writeFileSync(fixture.report_path,originalReport);}
});

test('processing feedback survives refresh; completion preserves unsaved edits',async({page})=>{
  let status='processing';let requests=0;
  const job={id:'test-durable-import',name:'Background fixture.wav',created:new Date().toISOString(),status,
    analysis_id:fixture.analysis,request:{upload_id:'fixture'}};
  await page.route('**/api/import-jobs',route=>route.fulfill({json:[{...job,status}]}));
  await page.goto('/?analysis='+fixture.analysis);
  await expect(page.locator('#study-workspace')).toBeVisible();
  const row=page.locator('[data-job="test-durable-import"]');
  await expect(row).toContainText('File uploaded · transcribing');
  await page.reload();await expect(row).toContainText('transcribing');
  await expect(page.locator('#study-workspace')).toBeVisible();
  await page.evaluate(()=>{pianoEditor.remember();state.notes[0].pitch+=.125;});
  const before=await page.evaluate(()=>({id:state.id,notes:JSON.stringify(state.notes)}));
  page.on('request',r=>{if(r.url().includes('/api/report?'))requests++;});
  status='complete';await expect(row).toContainText('Ready',{timeout:6000});
  expect(await page.evaluate(()=>({id:state.id,notes:JSON.stringify(state.notes)}))).toEqual(before);
  expect(requests).toBe(0);
  await page.evaluate(()=>pianoEditor.resetHistory());
});

test('failed processing displays exact error and retries without a second upload',async({page})=>{
  let retried=false,uploads=0;
  const job={id:'failed-import',name:'Retry fixture.wav',created:new Date().toISOString(),status:'failed',
    error:'Optional model weights missing',request:{upload_id:'existing-source',config:{},metadata:{song:'Retry fixture.wav'}}};
  await page.route('**/api/import-jobs',route=>route.fulfill({json:[retried?{...job,id:'retry-import',status:'processing'}:job]}));
  await page.route('**/api/import-start',route=>{retried=true;return route.fulfill({json:{...job,id:'retry-import',status:'queued'}});});
  page.on('request',r=>{if(new URL(r.url()).pathname==='/api/import')uploads++;});
  await page.goto('/');await expect(page.locator('#import-progress')).toContainText('Optional model weights missing');
  await page.getByRole('button',{name:'Retry processing'}).click();
  await expect(page.locator('[data-job="retry-import"]')).toContainText('transcribing');
  expect(uploads).toBe(0);
});
