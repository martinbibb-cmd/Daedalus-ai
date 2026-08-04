'use strict';

const assert = require('node:assert/strict');
const { execFileSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const publisher = path.join(
  __dirname,
  '..',
  'manual-ripper',
  'bin',
  'publish_reviewed_results.py',
);

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'manual-ripper-publish-'));
  const source = path.join(root, 'source');
  const target = path.join(root, 'target');
  fs.mkdirSync(path.join(source, 'reviewed'), { recursive: true });
  fs.mkdirSync(path.join(source, 'output'), { recursive: true });
  fs.writeFileSync(
    path.join(source, 'reviewed', 'manual-derived-van-stock.json'),
    '{"items":[]}\n',
  );
  fs.writeFileSync(
    path.join(source, 'reviewed', 'manual-derived-van-stock.approval.json'),
    '{"approved":true}\n',
  );
  fs.writeFileSync(
    path.join(source, 'output', 'manual-ripper-report.json'),
    '{"status":"synthetic"}\n',
  );
  return { root, source, target };
}

test('publishes only reviewed result artifacts into an immutable run', () => {
  const fixture = makeFixture();
  try {
    execFileSync('python3', [
      publisher,
      '--source-root', fixture.source,
      '--nas-root', fixture.target,
      '--run-id', '20260804T090000Z',
      '--allow-non-mounted-target',
    ]);

    const published = path.join(fixture.target, '20260804T090000Z');
    const manifest = JSON.parse(fs.readFileSync(path.join(published, 'manifest.json')));
    assert.deepEqual(
      manifest.files.map((entry) => entry.path),
      [
        'reviewed/manual-derived-van-stock.json',
        'reviewed/manual-derived-van-stock.approval.json',
        'output/manual-ripper-report.json',
      ],
    );
    assert.equal(manifest.schemaVersion, 1);
    assert.equal(manifest.runId, '20260804T090000Z');
    assert.match(manifest.sourceCommit, /^[0-9a-f]{40}$/);
    assert.equal(fs.statSync(path.join(published, 'manifest.json')).mode & 0o777, 0o644);
    assert.equal(fs.statSync(published).mode & 0o777, 0o755);

    const repeated = spawnSync('python3', [
      publisher,
      '--source-root', fixture.source,
      '--nas-root', fixture.target,
      '--run-id', '20260804T090000Z',
      '--allow-non-mounted-target',
    ], { encoding: 'utf8' });
    assert.equal(repeated.status, 1);
    assert.match(repeated.stderr, /published run already exists/);
  } finally {
    fs.rmSync(fixture.root, { recursive: true, force: true });
  }
});

test('fails closed without reviewed output and approval metadata', () => {
  const fixture = makeFixture();
  try {
    fs.rmSync(path.join(fixture.source, 'reviewed', 'manual-derived-van-stock.approval.json'));
    const result = spawnSync('python3', [
      publisher,
      '--source-root', fixture.source,
      '--nas-root', fixture.target,
      '--run-id', '20260804T090100Z',
      '--allow-non-mounted-target',
    ], { encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /required reviewed result files are missing/);
    assert.equal(fs.existsSync(fixture.target), false);
  } finally {
    fs.rmSync(fixture.root, { recursive: true, force: true });
  }
});
