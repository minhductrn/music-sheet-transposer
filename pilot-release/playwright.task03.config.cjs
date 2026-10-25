const {createRequire}=require('node:module');
const path=require('node:path');
const repo=path.resolve(__dirname,'..');
const {defineConfig}=createRequire(path.join(repo,'frontend-v2/package.json'))('@playwright/test');
const bundle=process.env.MST_TASK03_BUNDLE;
if(!bundle)throw Error('Set MST_TASK03_BUNDLE to the extracted pilot directory.');
module.exports=defineConfig({testDir:'../frontend-v2/tests/e2e',timeout:30000,workers:1,fullyParallel:false,reporter:[['list'],['json',{outputFile:path.join(repo,'frontend-v2/evidence/task03/regression.json')}]],use:{baseURL:'http://127.0.0.1:5183',viewport:{width:1440,height:900},browserName:'firefox',launchOptions:{executablePath:'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'},screenshot:'only-on-failure'},webServer:{command:`/usr/bin/python3 -I -B "${path.join(bundle,'start.py')}" --port 5183`,cwd:repo,url:'http://127.0.0.1:5183/api/v1/health',reuseExistingServer:false,timeout:30000},outputDir:path.join(repo,'frontend-v2/evidence/task03/test-results')});
