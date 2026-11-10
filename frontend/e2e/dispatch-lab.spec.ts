import { test, expect } from '@playwright/test';

test('intro appears at first paint, can replay and appears after full refresh', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const intro = page.getByRole('dialog', { name: 'FleetFlow opening screen' });
  await expect(intro).toBeVisible();
  await page.getByRole('button', { name: /skip intro/i }).click();
  await expect(intro).toHaveCount(0);

  await page.getByRole('button', { name: /replay loading intro/i }).click();
  await expect(intro).toBeVisible();
  await page.getByRole('button', { name: /skip intro/i }).click();

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(intro).toBeVisible();
});

test('mobile nav starts opaque without scrolling and stays opaque when scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const skip = page.getByRole('button', { name: /skip intro/i });
  if (await skip.isVisible()) await skip.click();
  const nav = page.locator('header.fixed.top-4 > div.max-w-6xl');
  await expect(nav).toBeVisible();

  const hasOpaqueBackground = async () => nav.evaluate(element => {
    const value = getComputedStyle(element).backgroundColor;
    const match = value.match(/rgba?\\(([^)]+)\\)/);
    if (!match) return false;
    const channels = match[1].split(/[,\\s]+/).filter(Boolean);
    return channels.length === 3 || (channels.length >= 4 && Number(channels[3]) >= 0.95);
  });

  expect(await hasOpaqueBackground()).toBe(true);
  await page.locator('header.fixed.top-4 button[class*="md:hidden"]').click();
  await expect(page.getByRole('link', { name: 'Architecture' })).toBeVisible();
  expect(await hasOpaqueBackground()).toBe(true);
});


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
