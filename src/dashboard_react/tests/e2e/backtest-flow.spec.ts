import { test, expect } from '@playwright/test';

// Pre-seed 3 distinct days so WFA banner is in chip mode — doesn't block the form
const WFA_ACK_SEEDED = JSON.stringify({
  count: 3,
  dates: ['2026-05-07', '2026-05-08', '2026-05-09'],
});

test.describe('Backtest flow', () => {
  test('form renders with STRATEGY/SYMBOL/TIMEFRAME selects and EXECUTE button', async ({ page, context }) => {
    await context.addInitScript(() => {
      window.localStorage.setItem('wfa_fail_ack_v1', WFA_ACK_SEEDED);
    });
    await page.goto('/');

    // Form section label visible
    await expect(page.getByText('> CONFIGURE_BACKTEST')).toBeVisible();

    // All three field labels render after API data loads
    await expect(page.getByText('STRATEGY')).toBeVisible();
    await expect(page.getByText('SYMBOL')).toBeVisible();
    await expect(page.getByText('TIMEFRAME')).toBeVisible();

    // Execute button visible and enabled (strategyId populated after API load)
    const executeBtn = page.getByRole('button', { name: /EXECUTE/ });
    await expect(executeBtn).toBeVisible();
    await expect(executeBtn).toBeEnabled();
  });

  test.skip(
    'user submits form and sees verdict panel — requires working backtest API + data files',
    async ({ page, context }) => {
      // NOTE: Skipped because backtest execution (WFA ~30-60s) depends on:
      // 1. Data files present in data/ directory
      // 2. Strategy presets configured with valid symbol/interval combos
      // 3. Backend not returning 500 on backtest endpoint
      // TODO S47: stub /api/backtest endpoint with fixture response for reliable E2E.
      await context.addInitScript(() => {
        window.localStorage.setItem('wfa_fail_ack_v1', WFA_ACK_SEEDED);
      });
      await page.goto('/');

      // Wait for form
      await expect(page.getByText('STRATEGY')).toBeVisible();

      const executeBtn = page.getByRole('button', { name: /EXECUTE/ });
      await executeBtn.click();

      // Wait for FINAL VERDICT (generous timeout — WFA can take 30-60s)
      const verdictHeading = page.getByText('▸ FINAL VERDICT');
      await expect(verdictHeading).toBeVisible({ timeout: 90_000 });

      // Equity chart title confirms result panel rendered
      await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible();
    },
  );
});
