import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests/e2e',testMatch:['classic-home.spec.ts','classic-chord-label.spec.ts'],timeout:60000,workers:1,reporter:'list',use:{baseURL:'http://127.0.0.1:5182',viewport:{width:1338,height:590},browserName:'firefox',launchOptions:{executablePath:'/home/dtran/.cache/ms-playwright/firefox-1555/firefox/firefox'}}});
