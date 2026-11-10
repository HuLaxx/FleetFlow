import { test, expect } from '@playwright/test';

test('intro is visible on first paint and accessible as a persistent showcase', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const intro = page.getByRole('dialog', { name: 'FleetFlow opening screen' });
  await expect(intro).toBeVisible();
  await page.getByRole('button', { name: /skip intro/i }).click();
  await expect(intro).toHaveCount(0);

  // Navigating through the public site must open the exact same intro.
  await page.getByRole('link', { name: /view loading screen/i }).click();
  await expect(page).toHaveURL(url => url.pathname === '/intro');
  await expect(intro).toBeVisible();
  await expect(intro.getByRole('heading', { name: 'FleetFlow' })).toBeVisible();
  await expect(intro.getByText('Loading your workspace')).toBeVisible();
  await expect(intro.getByRole('progressbar', { name: 'FleetFlow loading animation' })).toBeVisible();
  // This is a loading screen, not a second landing page or a navigation header.
  await expect(intro.locator('header')).toHaveCount(0);
  await expect(intro.getByTestId('fleetflow-loading-animation')).toBeVisible();

  // Unlike the auto intro, the direct preview cannot time out.
  await page.waitForTimeout(4700);
  await expect(intro).toBeVisible();
  await expect(page.getByRole('button', { name: /enter fleetflow/i })).toBeVisible();

  await page.getByRole('button', { name: /enter fleetflow/i }).click();
  await expect(page).toHaveURL(url => url.pathname === '/');
  await expect(intro).toHaveCount(0);

  // A full refresh restores the branded first-load animation.
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(intro).toBeVisible();
});

test('direct loading-screen link is persistent even on a mobile device', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/intro', { waitUntil: 'domcontentloaded' });
  const intro = page.getByRole('dialog', { name: 'FleetFlow opening screen' });
  await expect(intro).toBeVisible();
  await page.waitForTimeout(4700);
  await expect(intro).toBeVisible();
  await expect(intro.getByRole('progressbar')).toBeVisible();
  await expect(intro.locator('header')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /enter fleetflow/i })).toBeVisible();
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
    if (value === 'transparent' || value === '') return false;
    // Opaque hex colours resolve as rgb(...). Semitransparent rgba values
    // must have an alpha of at least 95%.
    if (value.startsWith('rgb(')) return true;
    if (value.startsWith('rgba(')) {
      const alpha = Number(value.slice(5, -1).split(',').at(-1)?.trim());
      return Number.isFinite(alpha) && alpha >= 0.95;
    }
    return !value.includes('transparent');
  });

  const before = await nav.evaluate(element => getComputedStyle(element).backgroundColor);
  expect(await hasOpaqueBackground(), 'Initial mobile header background: ' + before).toBe(true);

  await page.evaluate(() => window.scrollTo(0, 280));
  await page.waitForFunction(() => window.scrollY > 20);
  const scrolled = await nav.evaluate(element => getComputedStyle(element).backgroundColor);
  expect(await hasOpaqueBackground(), 'Scrolled mobile header background: ' + scrolled).toBe(true);

  await page.locator('header.fixed.top-4 button[class*="md:hidden"]').click();
  await expect(page.locator('header.fixed.top-4 div[class*="md:hidden"] a[href="/architecture"]')).toBeVisible();
  const opened = await nav.evaluate(element => getComputedStyle(element).backgroundColor);
  expect(await hasOpaqueBackground(), 'Open mobile menu background: ' + opened).toBe(true);
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
