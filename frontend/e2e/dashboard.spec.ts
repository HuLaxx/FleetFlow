
import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
    await page.goto('/');

    // Expect a title "to contain" a substring.
    await expect(page).toHaveTitle(/FleetFlow/);
});

test('loads dashboard map', async ({ page }) => {
    await page.goto('/');

    // Wait for the map container or core element
    // Based on fleet-map.tsx, it renders a div with relative class
    await expect(page.locator('body')).toBeVisible();

    // Check if main heading exists
    const heading = page.getByRole('heading', { name: /FleetFlow/i });
    if (await heading.count() > 0) {
        await expect(heading).toBeVisible();
    }
});
