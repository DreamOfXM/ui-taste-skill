#!/usr/bin/env node
'use strict';
// Local teaching-demo verification, not an aesthetic score or a native-app test.
// Requires Node.js and an installed Chrome/Chromium. No npm packages or user profile.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { createHash } = require('node:crypto');
const ROOT = path.resolve(__dirname, '..');
const SOURCE = path.join(ROOT, 'assets/app-craft-lab.html');
const OUT = path.join(ROOT, 'assets/app-craft-evidence');
const candidates = [process.env.CHROME_BIN,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google/Chrome/Application/chrome.exe')];
const executable = candidates.find(p => p && fs.existsSync(p));
if (!executable) {
  console.error('Not run: Chrome/Chromium was not found. Set CHROME_BIN to an existing executable.');
  process.exit(1);
}

async function main() {
  const source = fs.readFileSync(SOURCE);
  fs.mkdirSync(OUT, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ui-taste-skill-lab-'));
  const server = http.createServer((req, res) => {
    if (new URL(req.url, 'http://localhost').pathname !== '/lab') {
      res.writeHead(404); res.end(); return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(source);
  });
  let browser, session, sequence = 0, buffer = '';
  const pending = new Map(), errors = [], externalRequests = [], checks = [], captures = [];
  const report = {
    scope: 'Real Chromium layout, input and screenshots of the HTML teaching demo; not native-app or aesthetic approval',
    sourceSha256: createHash('sha256').update(source).digest('hex'),
    capturedAt: new Date().toISOString(), status: 'failed', checks, captures
  };
  function call(method, params = {}, sessionId = session) {
    const id = ++sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 15000);
      pending.set(id, { resolve, reject, timer });
      browser.stdio[3].write(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }) + '\0');
    });
  }
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' + (result.exceptionDetails.exception?.description || ''));
    return result.result.value;
  }
  async function settle() {
    await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
  }
  async function assert(expression, label) {
    if (!(await evaluate(expression))) throw new Error(label);
    checks.push(label);
  }
  async function click(selector) {
    const box = await evaluate(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el || !el.getClientRects().length) throw new Error('Missing or hidden control: ' + ${JSON.stringify(selector)});
      el.scrollIntoView({block:'center', inline:'nearest'});
      const r = el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
    })()`);
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...box });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...box });
    await settle();
  }
  async function size(width, height) {
    await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    await settle();
  }
  async function capture(name) {
    await evaluate('window.scrollTo(0,0)');
    await settle();
    await assert('document.documentElement.scrollWidth <= innerWidth', `${name}: no horizontal page overflow`);
    await assert('[...document.querySelectorAll(".list-pane,.inspector,.settings-pane")].filter(e=>e.getClientRects().length).every(e=>e.scrollWidth<=e.clientWidth+1)', `${name}: no horizontal work-pane overflow`);
    const metrics = await call('Page.getLayoutMetrics');
    const image = await call('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: metrics.cssContentSize.width, height: metrics.cssContentSize.height, scale: 1 }
    });
    const file = name + '.png';
    const bytes = Buffer.from(image.data, 'base64');
    fs.writeFileSync(path.join(OUT, file), bytes);
    captures.push({ file, sha256: createHash('sha256').update(bytes).digest('hex'),
      state: await evaluate('({viewport:[innerWidth,innerHeight],...document.documentElement.dataset,selected:document.querySelector("#inspector")?.dataset.assetId || null})') });
  }
  try {
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    browser = spawn(executable, ['--headless=new', '--remote-debugging-pipe', '--no-first-run',
      '--no-default-browser-check', '--disable-background-networking', `--user-data-dir=${profile}`],
      { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
    browser.stderr.resume();
    browser.stdio[4].on('data', data => {
      buffer += data;
      let end;
      while ((end = buffer.indexOf('\0')) >= 0) {
        const message = JSON.parse(buffer.slice(0, end)); buffer = buffer.slice(end + 1);
        if (message.id && pending.has(message.id)) {
          const request = pending.get(message.id); pending.delete(message.id); clearTimeout(request.timer);
          if (message.error) request.reject(new Error(message.error.message)); else request.resolve(message.result);
        }
        if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
        if (message.method === 'Network.requestWillBeSent') {
          const url = message.params.request.url;
          if (/^https?:/.test(url) && new URL(url).hostname !== '127.0.0.1') externalRequests.push(url);
        }
      }
    });
    browser.on('error', error => {
      for (const request of pending.values()) { clearTimeout(request.timer); request.reject(error); }
      pending.clear();
    });
    report.browser = await call('Browser.getVersion', {}, null);
    const { targetId } = await call('Target.createTarget', { url: 'about:blank' }, null);
    session = (await call('Target.attachToTarget', { targetId, flatten: true }, null)).sessionId;
    await call('Page.enable'); await call('Runtime.enable'); await call('Network.enable');
    await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    await size(1440, 1080);
    const ready = new Promise(resolve => {
      const listener = data => {
        if (String(data).includes('Page.loadEventFired')) { browser.stdio[4].off('data', listener); resolve(); }
      };
      browser.stdio[4].on('data', listener);
      const timer = setTimeout(() => { browser.stdio[4].off('data', listener); resolve(); }, 3000);
      timer.unref();
    });
    await call('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/lab` });
    await ready; await settle();
    await assert('document.querySelectorAll(".asset-row").length === 7', 'Default view has seven example records');
    await capture('refined-light');
    await click('[data-layout-choice="standard"]');
    await assert('document.querySelector("#inspector").dataset.assetId === "fold-guide"', 'Layout switch preserves selected object');
    await capture('standard-light');
    await click('[data-layout-choice="refined"]');
    await click('[data-page-target="favorites"]');
    await assert('document.querySelectorAll(".asset-row").length === 3', 'Favorites page filters the shared record set');
    await capture('favorites-light');
    await click('.asset-row[data-asset-id="fold-guide"] [data-action="favorite"]');
    await assert('document.querySelectorAll(".asset-row").length === 2 && document.querySelector("[data-count=favorites]").textContent === "2"', 'Removing a favorite updates page and navigation count');
    await click('[data-action="undo"]');
    await assert('document.querySelectorAll(".asset-row").length === 3', 'Undo restores the favorite');
    await click('[data-action="dismiss-feedback"]');
    await click('[data-page-target="all"]');
    await click('#asset-search'); await call('Input.insertText', { text: '<b>不存在</b>' });
    await assert('!!document.querySelector("[data-empty-state]") && !document.querySelector("[data-empty-state] b")', 'Search empty state escapes input and preserves real markup');
    await click('[data-action="clear-search"]');
    await assert('document.querySelectorAll(".asset-row").length === 7 && document.activeElement.id === "asset-search"', 'Clear search restores records and input focus');
    await click('.asset-row[data-asset-id="type-rules"] [data-action="select"]');
    await assert('document.querySelector("#inspector").dataset.assetId === "type-rules"', 'Selecting another object updates its inspector');
    await call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await assert('document.querySelector("#inspector").hidden && document.activeElement.dataset.assetId === "type-rules"', 'Escape closes inspector and returns focus to the object');
    await click('[data-page-target="settings"]');
    await click('[data-action="toggle-theme"]'); await click('[data-action="toggle-density"]');
    await assert('document.documentElement.dataset.theme === "dark" && document.documentElement.dataset.density === "compact"', 'Preferences apply theme and density');
    await capture('settings-dark');
    await click('[data-page-target="all"]');
    await click('.asset-row[data-asset-id="fold-guide"] [data-action="select"]');
    await size(1120, 900); await capture('compact-dark-1120');
    await size(390, 844);
    await click('[data-action="close-inspector"].back-button');
    await capture('narrow-list');
    await click('.asset-row[data-asset-id="fold-guide"] [data-action="select"]');
    await assert('document.activeElement.id === "inspector-title"', 'Narrow object view receives focus');
    await capture('narrow-detail');
    await click('[data-action="close-inspector"].back-button');
    await assert('document.activeElement.dataset.assetId === "fold-guide"', 'Narrow return preserves the selected object and focus');
    await click('[data-layout-choice="standard"]');
    await assert('document.documentElement.dataset.theme === "dark" && document.documentElement.dataset.density === "compact" && document.querySelectorAll(".asset-row").length === 7', 'Layout changes preserve theme, density and dataset');
    await capture('standard-narrow');
    if (errors.length) throw new Error('Uncaught page errors: ' + errors.join('; '));
    if (externalRequests.length) throw new Error('External requests: ' + externalRequests.join('; '));
    checks.push('No uncaught page errors or external page requests');
    report.status = 'passed';
  } catch (error) {
    report.error = error.message;
    process.exitCode = 1;
  } finally {
    if (browser && browser.exitCode === null) {
      try { await call('Browser.close', {}, null); } catch { browser.kill(); }
      if (browser.exitCode === null) await once(browser, 'exit');
    }
    for (const request of pending.values()) clearTimeout(request.timer);
    server.close();
    fs.rmSync(profile, { recursive: true, force: true });
    fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(`${report.status.toUpperCase()}: ${checks.length} checks; ${captures.length} real screenshots. No aesthetic approval implied.`);
    if (report.error) console.error(report.error);
    console.log('Report: ' + path.join(OUT, 'report.json'));
  }
}
main().catch(error => { console.error('Verification could not start: ' + error.message); process.exitCode = 1; });
