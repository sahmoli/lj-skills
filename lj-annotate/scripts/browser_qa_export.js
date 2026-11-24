async page => {
  const fail = message => { throw new Error(message); };
  const digest = await page.evaluate(() => window.__ljAnnotateQA.packetSha256);
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#partial").click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  let text = "";
  for await (const chunk of stream) text += chunk.toString("utf8");
  const returned = JSON.parse(text);
  if (returned.export_kind !== "partial" || returned.records.length !== 1) fail("partial export membership failed");
  if (!returned.packet_sha256 || returned.packet_sha256 !== digest) fail("return lacks packet provenance");
  if (!returned.records[0].human_reviewed || !returned.records[0].reviewed_at) fail("return lacks confirmation stamp");
  if (!returned.records[0].changed_fields.includes("outcome") || !returned.records[0].changed_fields.includes("quality")) fail("changed_fields round-trip failed");
  return {records: returned.records.length, changed: returned.records[0].changed_fields};
}
