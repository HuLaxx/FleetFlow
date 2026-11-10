
import { defineConfig, devices } from '@playwright/test';

const frontendPort = Number(process.env.FRONTEND_PORT || process.env.PORT || 3000);
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${frontendPort}`;

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL,
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: {
        command: `npm run dev -- --port ${frontendPort}`,
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120 * 1000,
    },
});
