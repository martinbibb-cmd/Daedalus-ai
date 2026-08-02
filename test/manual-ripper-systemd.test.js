const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');

test('manual ripper systemd unit only requires Ubuntu VM storage paths', () => {
  const unit = readFileSync('manual-ripper/systemd/daedalus-manual-ripper.service', 'utf8');

  assert.match(unit, /ReadWritePaths=\/srv\/daedalus\/manuals\b/);
  assert.doesNotMatch(unit, /\/mnt\/user\/ai-support/);
});
