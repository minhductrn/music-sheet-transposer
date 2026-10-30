const {createRequire}=require('node:module');
const path=require('node:path');
const repo=path.resolve(__dirname,'..');
const {defineConfig}=createRequire(repo+'/frontend-v2/package.json')('@playwright/test');
const port=Number(process.env.MST_RELEASE_PORT||5222);const result=process.env.MST_RELEASE_RESULT||'browser';
const bundle=process.env.MST_RELEASE_BUNDLE;if(!bundle)throw Error('Set MST_RELEASE_BUNDLE to the extracted Task 05 package.');
module.exports=defineConfig({testDir:repo+'/frontend-v2/tests/e2e',timeout:45000,workers:1,reporter:[['list'],['json',{outputFile:repo+'/frontend-v2/evidence/task06/'+result+'-results.json'}]],use:{baseURL:'http://127.0.0.1:'+port,viewport:{width:1440,height:900},browserName:'firefox',launchOptions:{executablePath:'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'},screenshot:'only-on-failure'},webServer:{command:'/usr/bin/python3 -I -B '+bundle+'/start.py --port '+port,cwd:'/tmp',url:'http://127.0.0.1:'+port+'/api/v1/health',reuseExistingServer:false},outputDir:repo+'/frontend-v2/evidence/task06/'+result+'-output'});
