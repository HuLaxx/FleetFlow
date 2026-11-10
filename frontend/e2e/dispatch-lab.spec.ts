test('intro shows once per session, can be skipped and does not return on reload', async ({ page }) => {
  await page.goto('/');
  const intro = page.getByRole('dialog', { name: 'FleetFlow opening screen' });
  await expect(intro).toBeVisible();
  await expect(page.getByRole('button', { name: /skip intro/i })).toBeVisible();

  await page.getByRole('button', { name: /skip intro/i }).click();
  await expect(intro).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('heading', { name: /a better way to move everything/i })).toBeVisible();
  await expect(intro).toHaveCount(0);
});

import { test, expect } from '@playwright/test';

test.describe('FleetFlow dispatch lab', () => {
  test('plans, approves, and completes a delivery without backend services', async ({ page }) => {
    await page.goto('/demo');
    await expect(page.getByRole('heading', { name: /make every stop count/i })).toBeVisible();
    await expect(page.getByText('NO LIVE ORDERS OR GPS')).toBeVisible();

    await page.getByRole('button', { name: 'Generate plan' }).click();
    await expect(page.getByText('Route proposal calculated')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Approve dispatch' })).toBeEnabled();

    await page.getByRole('button', { name: 'Approve dispatch' }).click();
    await expect(page.getByText('Routes dispatched')).toBeVisible();
    await page.getByRole('button', { name: 'Mark delivered' }).click();
    await expect(page.getByText('Stop delivered')).toBeVisible();
    await expect(page.getByText('1 / 9 delivered')).toBeVisible();
  });

  test('adding a stop invalidates a previous route proposal', async ({ page }) => {
    await page.goto('/demo');
    await page.getByRole('button', { name: 'Generate plan' }).click();
    await page.getByRole('button', { name: 'Add stop' }).click();

    await page.getByPlaceholder('Business name').fill('Scenario QA Test');
    await page.getByRole('button', { name: 'Add to manifest' }).click();
    await expect(page.getByText('Scenario QA Test').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate plan' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Approve dispatch' })).toBeDisabled();
  });

  test('mobile viewport keeps controls operable', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/demo');
    await expect(page.getByRole('heading', { name: /make every stop count/i })).toBeVisible();
    await page.getByRole('button', { name: 'Generate plan' }).click();
    await expect(page.getByRole('heading', { name: 'Vehicle run sheets' })).toBeVisible();
  });
});
