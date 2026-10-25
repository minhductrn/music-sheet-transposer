import { defineConfig } from 'vitest/config';
export default defineConfig({server:{proxy:{'/api':{target:process.env.AI_SDF_BACKEND_URL??'http://127.0.0.1:8000',changeOrigin:true}}},test:{include:['tests/*.test.ts']}});
