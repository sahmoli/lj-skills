async page => {
  const fail = message => { throw new Error(message); };
  await page.setViewportSize({width: 1440, height: 900});
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  const before = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  const fields = page.locator(".field");
  for (let index = 0; index < await fields.count(); index += 1) {
    const field = fields.nth(index);
    if (await field.locator('.choice[aria-pressed="true"]').count() === 0) {
      const first = field.locator(".choice:not([disabled])").first();
      if (await first.count()) await first.click();
    }
    const note = field.locator(".note");
    if (await note.count() && await note.getAttribute("required") !== null) {
      await note.fill("browser QA evidence note");
    }
  }
  if (await page.locator("#confirm").isDisabled()) fail("generic completion could not release confirmation gate");
  await page.locator("#confirm").click();
  const after = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (after.reviewed !== before.reviewed + 1) fail("confirmation did not add exactly one reviewed record");

  await page.reload();
  const restored = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (restored.reviewed !== after.reviewed) fail("reviewed state did not persist after reload");
  return {before, after, restored};
}
