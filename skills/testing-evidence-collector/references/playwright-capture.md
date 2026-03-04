# Playwright Capture

## Playwright Screenshot Utility (TypeScript)

Use this inline script to capture before/after screenshots at a consistent viewport. Save it as `tests/capture-evidence.ts` in the project.

```ts
import { chromium, type Browser, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const VIEWPORT = { width: 1280, height: 720 };
const OUTPUT_DIR = "qa-evidence";

interface CaptureOptions {
  url: string;
  name: string;
  actions?: (page: Page) => Promise<void>;
  fullPage?: boolean;
}

async function captureEvidence(options: CaptureOptions): Promise<string> {
  const outputDir = path.resolve(OUTPUT_DIR);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const browser: Browser = await chromium.launch();
  const page: Page = await browser.newPage({ viewport: VIEWPORT });
  await page.goto(options.url, { waitUntil: "networkidle" });

  const beforePath = path.join(outputDir, `${options.name}-before.png`);
  await page.screenshot({ path: beforePath, fullPage: options.fullPage ?? false });

  if (options.actions) {
    await options.actions(page);
    await page.waitForTimeout(500); // Allow animations to complete
    const afterPath = path.join(outputDir, `${options.name}-after.png`);
    await page.screenshot({ path: afterPath, fullPage: options.fullPage ?? false });
  }

  await browser.close();
  return beforePath;
}

// Example: capture accordion expand/collapse
captureEvidence({
  url: "http://localhost:3000",
  name: "accordion-faq",
  actions: async (page) => {
    await page.click('[data-testid="accordion-item-0"] button');
    await page.waitForSelector('[data-testid="accordion-item-0"] [data-state="open"]');
  },
});
```

## Playwright Test With Evidence Capture

Save as `tests/accordion.spec.ts`. Each test captures screenshots as evidence artifacts.

```ts
import { test, expect } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 720 } });

test.describe("Accordion Component", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000/faq");
  });

  test("expands first item on click and reveals content", async ({ page }) => {
    const trigger = page.locator('[data-testid="accordion-item-0"] button');
    const content = page.locator('[data-testid="accordion-item-0"] [data-testid="accordion-content"]');
    await expect(content).not.toBeVisible();
    await page.screenshot({ path: "qa-evidence/accordion-collapsed.png" });
    await trigger.click();
    await expect(content).toBeVisible();
    await page.screenshot({ path: "qa-evidence/accordion-expanded.png" });
  });

  test("only one item open at a time", async ({ page }) => {
    await page.click('[data-testid="accordion-item-0"] button');
    await page.click('[data-testid="accordion-item-1"] button');
    await expect(page.locator('[data-testid="accordion-item-0"] [data-testid="accordion-content"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="accordion-item-1"] [data-testid="accordion-content"]')).toBeVisible();
    await page.screenshot({ path: "qa-evidence/accordion-single-open.png" });
  });
});
```
