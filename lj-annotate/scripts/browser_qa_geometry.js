async page => {
  const fail = message => { throw new Error(message); };
  await page.setViewportSize({width: 1440, height: 900});
  await page.reload();
  const packet = JSON.parse(await page.locator("#packet").textContent());
  const first = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  const firstButtons = await page.locator(".choice").evaluateAll(buttons => buttons.map(button => {
    const rect = button.getBoundingClientRect();
    return [rect.x, rect.y, rect.width, rect.height];
  }));
  let longest = 0;
  packet.records.forEach((record, index) => {
    if (record.primary_text.length > packet.records[longest].primary_text.length) longest = index;
  });
  await page.evaluate(index => window.__ljAnnotateQA.setIndex(index), longest);
  await page.waitForTimeout(50);
  const last = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  const lastButtons = await page.locator(".choice").evaluateAll(buttons => buttons.map(button => {
    const rect = button.getBoundingClientRect();
    return [rect.x, rect.y, rect.width, rect.height];
  }));
  if (first.document.horizontalOverflow || first.document.verticalOverflow) fail("first record overflows desktop");
  if (last.document.horizontalOverflow || last.document.verticalOverflow) fail("longest record overflows desktop");
  if (JSON.stringify(first.fieldRects) !== JSON.stringify(last.fieldRects)) fail("field geometry moved across records");
  if (JSON.stringify(firstButtons) !== JSON.stringify(lastButtons)) fail("option-button geometry moved across records");
  if (JSON.stringify(first.footer) !== JSON.stringify(last.footer)) fail("footer geometry moved across records");
  if (first.capacityOverflow || last.capacityOverflow) fail("declared decision capacity exceeded");
  if (first.unselectedBackgrounds.length !== 1) fail("unselected controls are not neutral");
  if (!first.selectedHaveCheck) fail("selected controls lack check marks");

  await page.setViewportSize({width: 1280, height: 720});
  const compact = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  const floor = packet.layout.evidence_min_font_px;
  if (compact.document.horizontalOverflow || compact.document.verticalOverflow || compact.capacityOverflow) fail("compact desktop overflow");
  if (parseFloat(compact.evidence.fontSize) < floor) fail("evidence font below declared floor");
  if (parseFloat(compact.evidence.fontSize) === floor && compact.evidence.scrollHeight > compact.evidence.clientHeight && compact.evidence.overflowY !== "auto") fail("long evidence does not scroll internally");

  await page.setViewportSize({width: 861, height: 700});
  const edge = await page.evaluate(() => window.__ljAnnotateQA.snapshot());
  if (edge.document.horizontalOverflow || edge.document.verticalOverflow || edge.capacityOverflow) fail("desktop side of breakpoint failed");
  for (const viewport of [{width: 860, height: 700}, {width: 375, height: 667}]) {
    await page.setViewportSize(viewport);
    const narrow = await page.evaluate(() => {
      const snapshot = window.__ljAnnotateQA.snapshot();
      const confirm = document.querySelector("#confirm");
      confirm.scrollIntoView({block: "center"});
      const rect = confirm.getBoundingClientRect();
      return {snapshot, top: rect.top, bottom: rect.bottom};
    });
    if (narrow.snapshot.document.horizontalOverflow) fail("narrow horizontal overflow");
    if (narrow.top < 0 || narrow.bottom > viewport.height) fail("narrow confirm unreachable");
  }
  return {first, last, longest};
}
