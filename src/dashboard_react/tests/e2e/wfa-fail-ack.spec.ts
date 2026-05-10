import { test, expect } from '@playwright/test';

// Storage key matches useWfaFailAck hook constant
const STORAGE_KEY = 'wfa_fail_ack_v1';

test.describe('WFA fail ack-gate', () => {
  test('banner shows on first visit, persists through reload, downgrades after ack', async ({ page, context }) => {
    // Clear localStorage to simulate first-visit state
    await context.addInitScript(() => {
      window.localStorage.clear();
    });
    await page.goto('/');

    // Full banner visible — title text in Russian
    const bannerTitle = page.getByText('ВНИМАНИЕ · S45 HONEST VERDICT');
    await expect(bannerTitle).toBeVisible();

    // Ack button visible via aria-label
    const ackBtn = page.getByRole('button', { name: 'Подтвердить понимание WFA вердикта' });
    await expect(ackBtn).toBeVisible();
    await expect(ackBtn).toBeEnabled();

    // Reload — banner persists (no ack yet)
    await page.reload();
    await expect(page.getByText('ВНИМАНИЕ · S45 HONEST VERDICT')).toBeVisible();

    // Click ack
    await page.getByRole('button', { name: 'Подтвердить понимание WFA вердикта' }).click();

    // Banner title gone (hook now shows chip — distinctDays=1, need 3 to fully downgrade)
    // After ack today: ackedToday=true → showFullBanner=false → showChip=true
    await expect(page.getByText('ВНИМАНИЕ · S45 HONEST VERDICT')).not.toBeVisible();

    // Chip with role="status" and aria-label visible
    const chip = page.getByRole('status', { name: 'WFA честный вердикт S45' });
    await expect(chip).toBeVisible();
  });

  test('chip mode persists after 3 distinct days pre-seeded in localStorage', async ({ page, context }) => {
    // Pre-seed 3 distinct days so hook enters chip mode immediately
    // Storage format per useWfaFailAck: { count: number, dates: string[] }
    await context.addInitScript(() => {
      window.localStorage.setItem(
        'wfa_fail_ack_v1',
        JSON.stringify({ count: 3, dates: ['2026-05-07', '2026-05-08', '2026-05-09'] }),
      );
    });
    await page.goto('/');

    // Full banner must NOT appear (distinctDays >= 3 → downgradeDone)
    await expect(page.getByText('ВНИМАНИЕ · S45 HONEST VERDICT')).not.toBeVisible();

    // Chip always visible after downgrade
    const chip = page.getByRole('status', { name: 'WFA честный вердикт S45' });
    await expect(chip).toBeVisible();
  });
});
