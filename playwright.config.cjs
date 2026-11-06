const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'./tests/browser',testIgnore:'**/long_navigation.spec.cjs',workers:1,fullyParallel:false,timeout:30000,
  reporter:[['list'],['json',{outputFile:'.cache/editor-tests/browser-results.json'}]],
  use:{baseURL:'http://127.0.0.1:8772',headless:true,trace:'retain-on-failure',screenshot:'only-on-failure',
    launchOptions:{args:['--mute-audio','--disable-gpu']},viewport:{width:1366,height:768}},
  projects:[{name:'1366x768',use:{viewport:{width:1366,height:768}}},{name:'1920x1080',use:{viewport:{width:1920,height:1080}}}],
  webServer:{command:'.venv\\Scripts\\python.exe -u tools/editor_test_server.py',url:'http://127.0.0.1:8772/api/state',reuseExistingServer:false,timeout:90000}
});
