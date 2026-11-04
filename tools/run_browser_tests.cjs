const {spawnSync}=require('node:child_process');
const path=require('node:path');
const result=spawnSync(process.execPath,[require.resolve('@playwright/test/cli'),'test',...process.argv.slice(2)],{
  cwd:path.resolve(__dirname,'..'),stdio:'inherit',windowsHide:true,
  env:{...process.env,PLAYWRIGHT_BROWSERS_PATH:path.resolve(__dirname,'../.cache/ms-playwright'),PYTHONIOENCODING:'utf-8',OMP_NUM_THREADS:'2',MKL_NUM_THREADS:'2'}});
process.exit(result.status??1);
