const base=require('./playwright.config.cjs');
module.exports={...base,
 testIgnore:[],testMatch:['long_navigation.spec.cjs','study_playhead.spec.cjs','transport.spec.cjs','imports.spec.cjs'],
 outputDir:'.cache/navigation-validation/artifacts',
 reporter:[['list'],['json',{outputFile:'.cache/navigation-validation/results.json'}]],
 use:{...base.use,baseURL:'http://127.0.0.1:8773'},
 webServer:{command:'.venv\\Scripts\\python.exe -B -u tools/long_test_server.py',url:'http://127.0.0.1:8773/api/state',reuseExistingServer:true,timeout:90000}
};
