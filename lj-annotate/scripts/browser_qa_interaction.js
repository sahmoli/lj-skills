async page => {
  const fail = message => { throw new Error(message); };
  await page.setViewportSize({width: 1440, height: 900});
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.keyboard.press("ArrowRight");
  let state = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (state.reviewed !== 1 || state.index !== 1) fail("ArrowRight did not confirm exactly one record");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("2");
  state = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (state.reviewed !== 0 || state.index !== 0) fail("editing did not clear confirmation");
  await page.reload();
  const restored = await page.evaluate(() => {
    const selected = document.querySelector(".field[data-field=scope] .choice[aria-pressed=true]");
    return {
      reviewed: window.__ljAnnotateQA.snapshot().reviewed,
      selected: selected && selected.dataset.value,
      key: window.__ljAnnotateQA.storageKey,
      digest: window.__ljAnnotateQA.packetSha256,
    };
  });
  if (restored.selected !== "no" || restored.reviewed !== 0) fail("edited state did not survive reload");
  if (!restored.key.includes(restored.digest.slice(0, 16))) fail("storage namespace lacks packet digest");

  await page.keyboard.press("1");
  const dependent = await page.evaluate(() => {
    const field = document.querySelector(".field[data-field=outcome]");
    return {
      pressed: field.querySelectorAll(".choice[aria-pressed=true]").length,
      disabled: [...field.querySelectorAll("button")].every(button => button.disabled),
    };
  });
  if (dependent.pressed !== 0 || dependent.disabled) fail("structural value did not clear on unlock");
  await page.keyboard.press("s");
  await page.keyboard.press("x");
  if (!(await page.locator("#confirm").isDisabled())) fail("required note did not block confirmation");
  const note = page.locator(".field[data-field=quality] .note");
  await note.fill("fixture note supplied by browser QA");
  if (await page.locator("#confirm").isDisabled()) fail("valid note did not release confirmation gate");
  const scopeValue = await page.locator(".field[data-field=scope] .choice[aria-pressed=true]").getAttribute("data-value");
  if (scopeValue !== "yes") fail("typing in note hijacked a global shortcut");
  await note.press("Enter");
  state = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (state.reviewed !== 1 || state.index !== 1) fail("Enter in a valid note did not confirm exactly one record");

  return {packetSha256: restored.digest};
}
