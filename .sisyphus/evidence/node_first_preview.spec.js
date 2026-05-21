const fs = require('fs');
const { test, expect } = require('@playwright/test');

const url = process.env.NW_PREVIEW_URL || 'http://10.192.20.70:8088/preview.revised.html';
const evidenceDir = '/home/tjwocjf0915/workspace/NW_project/.sisyphus/evidence';
const nodeIds = ['host-simulator', 'local-agent', 'r1', 'r2', 'monitor'];

function assertStableBox(before, after) {
  expect(Math.abs(before.width - after.width)).toBeLessThanOrEqual(2);
  expect(Math.abs(before.height - after.height)).toBeLessThanOrEqual(2);
}

test('reported-state card overlay preview contract', async ({ page }) => {
  const consoleMessages = [];
  page.on('console', (message) => consoleMessages.push(`${message.type()}: ${message.text()}`));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(url, { waitUntil: 'networkidle' });

  await expect(page.locator('[data-testid="node-detail-inspector"]')).toHaveCount(0);
  const diagramBefore = await page.locator('[data-testid="diagram-overlay-host"]').boundingBox();
  expect(diagramBefore.width).toBeGreaterThanOrEqual(1230);
  expect(diagramBefore.width).toBeLessThanOrEqual(1250);
  expect(diagramBefore.height).toBeGreaterThanOrEqual(650);
  expect(diagramBefore.height).toBeLessThanOrEqual(670);

  for (const nodeId of nodeIds) {
    await expect(page.locator(`[data-testid="node-card-${nodeId}"]`)).toHaveCount(1);
    await expect(page.locator(`[data-testid="node-card-rows-${nodeId}"]`)).toHaveCount(1);
    for (const row of ['node-id', 'role', 'observed-liveness', 'reported-state']) {
      await expect(page.locator(`[data-testid="node-info-row-${nodeId}-${row}"]`)).toHaveCount(1);
    }
    await expect(page.locator(`[data-testid="liveness-lamp-${nodeId}"]`)).toHaveCount(1);
    await expect(page.locator(`[data-testid="reported-state-${nodeId}"]`)).toHaveAttribute('data-reported-state-tone', 'running');
    await expect(page.locator(`[data-testid^="activity-chip-${nodeId}-"]`).first()).toBeVisible();
  }

  expect(await page.locator('[data-testid="liveness-lamp-r2"]').getAttribute('data-liveness-tone')).toBe('gray');
  expect(await page.locator('[data-testid="reported-state-r2"]').getAttribute('data-reported-state-tone')).toBe('running');

  await page.locator('[data-testid="node-card-r1"]').click();
  await expect(page.locator('[data-testid="node-detail-inspector"]')).toHaveAttribute('data-overlay', 'diagram');
  await expect(page.locator('[data-testid="node-detail-inspector"]')).toHaveAttribute('data-detail-state', 'open');
  const openAnimation = await page.locator('[data-testid="node-detail-inspector"]').evaluate((el) => getComputedStyle(el).animationName);
  expect(openAnimation).toBe('detailInspectorIn');
  await expect(page.locator('[data-testid="detail-inspector-overlay"]')).toBeVisible();
  const overlayOverflowY = await page.locator('[data-testid="detail-inspector-overlay"]').evaluate((el) => getComputedStyle(el).overflowY);
  expect(overlayOverflowY).toBe('auto');
  const overlayBox = await page.locator('[data-testid="node-detail-inspector"]').boundingBox();
  expect(overlayBox.height).toBeGreaterThanOrEqual(610);
  expect(overlayBox.height).toBeLessThanOrEqual(640);
  assertStableBox(diagramBefore, await page.locator('[data-testid="diagram-overlay-host"]').boundingBox());

  const expectedDetails = [
    ['host-simulator', 'host-detail'],
    ['local-agent', 'agent-detail'],
    ['r1', 'relay-detail-r1'],
    ['r2', 'relay-detail-r2'],
    ['monitor', 'monitor-detail'],
  ];
  for (const [nodeId, detailId] of expectedDetails) {
    if (await page.locator('[data-testid="node-detail-inspector"]').count()) {
      await page.locator('[data-testid="detail-close-button"]').click();
      await page.waitForTimeout(260);
    }
    await page.locator(`[data-testid="node-card-${nodeId}"]`).click();
    await expect(page.locator('[data-testid="node-detail-inspector"]')).toBeVisible();
    await expect(page.locator(`[data-testid="${detailId}"]`)).toBeVisible();
    assertStableBox(diagramBefore, await page.locator('[data-testid="diagram-overlay-host"]').boundingBox());
  }

  const inspectorBox = await page.locator('[data-testid="node-detail-inspector"]').boundingBox();
  const widthRatio = inspectorBox.width / 1440;
  expect(widthRatio).toBeGreaterThanOrEqual(0.28);
  expect(widthRatio).toBeLessThanOrEqual(0.38);

  const bodyText = await page.locator('body').innerText();
  const forbidden = ['비고', '설명', 'activityLogs', 'description', 'state=', 'state =', 'attempt=', 'attempt =', 'queue=', 'pending=', 'retries=', 'dup=', 'Controller/UI', 'Reporting Hub', 'Control Hub', 'Management Node'];
  expect(forbidden.filter((token) => bodyText.includes(token))).toEqual([]);

  await page.locator('[data-testid="detail-close-button"]').click();
  await expect(page.locator('[data-testid="node-detail-inspector"]')).toHaveAttribute('data-detail-state', 'closing');
  await page.waitForTimeout(260);
  await expect(page.locator('[data-testid="node-detail-inspector"]')).toHaveCount(0);
  assertStableBox(diagramBefore, await page.locator('[data-testid="diagram-overlay-host"]').boundingBox());

  fs.writeFileSync(`${evidenceDir}/task-4-reported-card-overlay-dom.html`, await page.content());
  fs.writeFileSync(`${evidenceDir}/task-4-reported-card-overlay-browser-check.txt`, [`PASS reported-state card overlay browser contract`, `url=${url}`, `inspector_width_ratio=${widthRatio.toFixed(3)}`, `open_animation=${openAnimation}`, `overlay_overflow_y=${overlayOverflowY}`, `overlay_height=${overlayBox.height.toFixed(1)}`, ...consoleMessages].join('\n'));
  await page.screenshot({ path: `${evidenceDir}/task-4-reported-card-overlay-preview.png`, fullPage: true });
});
