#!/usr/bin/env node
'use strict';
// Dependency-free evidence capture, not aesthetic approval. The caller owns the URL's server.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawn } = require('node:child_process');
const { createHash } = require('node:crypto');

const HELP = `Usage: node capture-ui.cjs --url http://127.0.0.1:3000 --out NEW_OR_EMPTY_DIR --source app.html
  [--width 1440] [--height 960] [--steps steps.json]
Steps: [{"action":"click","selector":"#open"},{"action":"fill","selector":"input","text":"hello"},
        {"action":"key","key":"Enter"},{"action":"viewport","width":390,"height":844},
        {"action":"media","reducedMotion":true},{"action":"capture","name":"mobile"}]
An initial viewport PNG is always captured before steps. Capture names must be unique.
Selectors: type, *, #id, .class, [attribute], [attribute="value"], attribute operators,
           descendant / > / + / ~ combinators and comma groups (no escapes or pseudo-classes).
Keys: Tab, Enter, Escape, Backspace, Delete, arrows, Home, End, PageUp, PageDown, Space,
      or one printable character. Dimensions: integers 1..8192; maximum 200 steps.
Output parent must exist; symlinks in the output path are refused. Never overwrites files.
Only loopback HTTP(S) documents are allowed; subresources are not a network sandbox.
The source hash identifies the supplied HTML, not proof that the server served that file.
Requires installed Chrome/Chromium (CHROME_BIN overrides discovery); uses a temporary profile.
`;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const stamp = () => new Date().toISOString();
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const namedKeys = { Tab: 9, Enter: 13, Escape: 27, Backspace: 8, Delete: 46,
  ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, Home: 36, End: 35,
  PageUp: 33, PageDown: 34, Space: 32 };

function loopbackUrl(value) {
  if (typeof value !== 'string' || !/^https?:\/\//.test(value) || /[\s\x00-\x1f\x7f\\]/.test(value)) {
    throw new Error('--url must be a loopback HTTP(S) URL');
  }
  let url;
  try { url = new URL(value); } catch { throw new Error('Invalid --url'); }
  if (url.username || url.password || !(['localhost', '[::1]'].includes(url.hostname) ||
      /^127(?:\.\d{1,3}){3}$/.test(url.hostname))) {
    throw new Error('--url must use a loopback host without credentials');
  }
  return url.href;
}

function dimension(value) {
  if (!Number.isInteger(value) || value < 1 || value > 8192) throw new Error('Dimensions must be integers 1..8192');
  return value;
}

// A deliberately bounded CSS subset, validated without launching a browser or installing a parser.
const ident = '[A-Za-z_][A-Za-z0-9_-]*';
const attrValue = `(?:${ident}|"[^"\\\\\\r\\n\\x00]*"|'[^'\\\\\\r\\n\\x00]*')`;
const attribute = `\\[\\s*${ident}(?:\\s*[~|^$*]?=\\s*${attrValue}(?:\\s+[iIsS])?)?\\s*\\]`;
const suffix = `(?:[#.]${ident}|${attribute})`;
const compound = `(?:(?:${ident}|\\*)(?:${suffix})*|(?:${suffix})+)`;
const chain = `${compound}(?:(?:\\s*[>+~]\\s*|\\s+)${compound})*`;
const selectorPattern = new RegExp(`^${chain}(?:\\s*,\\s*${chain})*$`);
function selector(value) {
  if (typeof value !== 'string' || value.length > 1024 || /[\x00-\x1f\x7f]/.test(value) ||
      !selectorPattern.test(value)) throw new Error('Invalid selector; use the CSS subset listed in --help');
}

function checkOutput(out) {
  // lstat every component, including dangling links; do not silently resolve a symlink destination.
  let current = path.parse(out).root;
  const parts = out.slice(current.length).split(path.sep).filter(Boolean);
  for (let i = 0; i < parts.length; i++) {
    current = path.join(current, parts[i]);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) {
      if (error.code === 'ENOENT' && i === parts.length - 1) return;
      throw new Error('Output parent must exist: ' + current);
    }
    if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error('Output path must contain only directories, no symlinks: ' + current);
  }
  if (fs.readdirSync(out).length) throw new Error('Output directory must be NEW or empty; refusing overwrite');
}

function parseArgs(args) {
  const allowed = new Set(['url', 'out', 'source', 'width', 'height', 'steps']);
  const options = Object.create(null);
  for (let i = 0; i < args.length; i += 2) {
    const name = args[i].startsWith('--') ? args[i].slice(2) : '';
    if (!allowed.has(name) || Object.hasOwn(options, name)) throw new Error('Unknown or duplicate argument: ' + args[i]);
    if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error('Missing value for ' + args[i]);
    options[name] = args[i + 1];
  }
  for (const name of ['url', 'out', 'source']) if (!options[name]) throw new Error('Required: --' + name);
  options.url = loopbackUrl(options.url);
  for (const [name, fallback] of [['width', 1440], ['height', 960]]) {
    if (options[name] !== undefined && !/^\d+$/.test(options[name])) throw new Error('Invalid dimension: --' + name);
    options[name] = dimension(options[name] === undefined ? fallback : Number(options[name]));
  }
  options.source = path.resolve(options.source);
  if (!/\.html?$/i.test(options.source) || !fs.statSync(options.source).isFile()) throw new Error('--source must be one HTML file');
  options.sourceBytes = fs.readFileSync(options.source);
  let steps = [];
  if (options.steps) {
    if (!fs.statSync(path.resolve(options.steps)).isFile()) throw new Error('--steps must be a JSON file');
    try { steps = JSON.parse(fs.readFileSync(path.resolve(options.steps), 'utf8')); }
    catch { throw new Error('--steps must contain valid JSON'); }
  }
  if (!Array.isArray(steps) || steps.length > 200) throw new Error('--steps must be an array of at most 200 steps');
  const fields = { click: ['selector'], fill: ['selector', 'text'], key: ['key'],
    viewport: ['width', 'height'], media: ['reducedMotion'], capture: ['name'] };
  const names = new Set(['initial']);
  for (const [index, step] of steps.entries()) {
    if (!step || typeof step !== 'object' || Array.isArray(step) || !Object.hasOwn(fields, step.action)) throw new Error('Invalid action at step ' + (index + 1));
    const required = ['action', ...fields[step.action]];
    if (Object.keys(step).length !== required.length || !required.every(key => Object.hasOwn(step, key))) throw new Error('Invalid fields at step ' + (index + 1));
    if (Object.hasOwn(step, 'selector')) selector(step.selector);
    if (step.action === 'fill' && (typeof step.text !== 'string' || step.text.length > 100000 || step.text.includes('\0'))) throw new Error('Invalid fill text');
    if (step.action === 'key' && (typeof step.key !== 'string' || !(Object.hasOwn(namedKeys, step.key) ||
        (Array.from(step.key).length === 1 && !/[\p{C}\p{Zl}\p{Zp}]/u.test(step.key))))) throw new Error('Invalid key');
    if (step.action === 'viewport') { dimension(step.width); dimension(step.height); }
    if (step.action === 'media' && typeof step.reducedMotion !== 'boolean') throw new Error('reducedMotion must be boolean');
    if (step.action === 'capture') {
      if (typeof step.name !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(step.name) ||
          /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(step.name) || names.has(step.name.toLowerCase())) throw new Error('Invalid or duplicate capture name');
      names.add(step.name.toLowerCase());
    }
  }
  options.steps = steps;
  options.out = path.resolve(options.out);
  checkOutput(options.out);
  return options;
}

function findChrome() {
  const candidates = process.env.CHROME_BIN ? [process.env.CHROME_BIN] : [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    path.join(os.homedir(), 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium',
    '/usr/bin/chromium-browser', '/opt/google/chrome/chrome', '/snap/bin/chromium',
    ...['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'].flatMap(key => process.env[key] ? [
      path.join(process.env[key], 'Google/Chrome/Application/chrome.exe'),
      path.join(process.env[key], 'Chromium/Application/chrome.exe')] : [])
  ];
  for (const candidate of candidates) {
    try {
      const file = path.resolve(candidate);
      fs.accessSync(file, fs.constants.X_OK);
      if (fs.statSync(file).isFile()) return file;
    } catch { /* Try the next standard installation. */ }
  }
  throw new Error('Chrome/Chromium not found; set CHROME_BIN to an installed executable');
}

function connectPipe(browser, onEvent) {
  let sequence = 0, buffer = '', failure;
  const pending = new Map();
  function fail(error) {
    if (!failure) failure = error;
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(failure); }
    pending.clear();
  }
  browser.on('error', fail);
  browser.on('exit', (code, signal) => fail(new Error(`Browser exited (code ${code}, signal ${signal})`)));
  browser.stdio[3].on('error', fail);
  const input = browser.stdio[4];
  input.setEncoding('utf8'); // StringDecoder preserves characters split across pipe chunks.
  input.on('error', fail);
  input.on('end', () => fail(new Error('Browser CDP pipe closed')));
  input.on('data', chunk => {
    buffer += chunk;
    try {
      let end;
      while ((end = buffer.indexOf('\0')) !== -1) {
        const message = JSON.parse(buffer.slice(0, end));
        buffer = buffer.slice(end + 1);
        const request = pending.get(message.id);
        if (request) {
          pending.delete(message.id); clearTimeout(request.timer);
          if (message.error) request.reject(new Error(request.method + ': ' + message.error.message));
          else request.resolve(message.result);
        } else if (message.method) onEvent(message);
      }
      if (buffer.length > 128 * 1024 * 1024) fail(new Error('Oversized CDP message'));
    } catch (error) { fail(error); }
  });
  function call(method, params = {}, sessionId, timeout = 15000) {
    if (failure) return Promise.reject(failure);
    const id = ++sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => fail(new Error('Timed out: ' + method)), timeout);
      pending.set(id, { resolve, reject, timer, method });
      browser.stdio[3].write(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }) + '\0', error => { if (error) fail(error); });
    });
  }
  return { call, fail, check() { if (failure) throw failure; } };
}

async function stopBrowser(browser, cdp) {
  if (!browser || browser.pid === undefined) return;
  let exited = browser.exitCode !== null || browser.signalCode !== null;
  const exit = new Promise(resolve => {
    if (exited) resolve();
    else browser.once('exit', () => { exited = true; resolve(); });
  });
  async function wait(ms) {
    let timer;
    await Promise.race([exit, new Promise(resolve => { timer = setTimeout(resolve, ms); })]);
    clearTimeout(timer);
  }
  if (!exited) {
    try { await cdp.call('Browser.close', {}, undefined, 2000); } catch { /* Escalate below. */ }
    await wait(2000);
  }
  if (!exited) { browser.kill('SIGTERM'); await wait(2000); }
  if (!exited) { browser.kill('SIGKILL'); await wait(2000); }
  cdp.fail(new Error('Capture session closed'));
  for (const stream of browser.stdio) if (stream) stream.destroy();
  if (!exited) throw new Error('Owned browser did not exit; temporary profile retained');
}

async function captureUI(options) {
  // Reserve only after every argument/step has been validated; use exclusive creation for artifacts.
  if (!fs.existsSync(options.out)) fs.mkdirSync(options.out);
  checkOutput(options.out);
  const owner = fs.lstatSync(options.out);
  function write(file, bytes) {
    const current = fs.lstatSync(options.out);
    if (current.isSymbolicLink() || current.dev !== owner.dev || current.ino !== owner.ino ||
        fs.realpathSync(options.out) !== options.out) throw new Error('Output directory changed; refusing write');
    fs.writeFileSync(path.join(options.out, file), bytes, { flag: 'wx' });
  }
  const report = { status: 'failed', timestamp: stamp(), url: options.url,
    scope: 'Viewport evidence and measured overflow only; no aesthetic assessment or served-source identity check.',
    source: { path: options.source, sha256: sha256(options.sourceBytes), bytes: options.sourceBytes.length },
    viewport: { width: options.width, height: options.height, deviceScaleFactor: 1 },
    browserVersion: null, steps: options.steps, captures: [], errors: [] };
  let browser, cdp, profile, session, step = 0, stderr = '', cleanupSafe = true;
  let viewport = { ...report.viewport }, reducedMotion = false;
  const loaded = new Set();
  function error(kind, message) { report.errors.push({ kind, message, step, timestamp: stamp() }); }
  const interrupted = signal => { if (cdp) cdp.fail(new Error('Interrupted: ' + signal)); };
  const onInt = () => interrupted('SIGINT'), onTerm = () => interrupted('SIGTERM');
  process.on('SIGINT', onInt); process.on('SIGTERM', onTerm);
  try {
    const executable = findChrome();
    profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ui-capture-'));
    browser = spawn(executable, ['--headless=new', '--remote-debugging-pipe', '--no-first-run',
      '--no-default-browser-check', '--disable-background-networking', '--disable-component-update',
      '--disable-sync', '--disable-extensions', '--force-device-scale-factor=1',
      '--host-resolver-rules=MAP localhost 127.0.0.1', `--user-data-dir=${profile}`],
    { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
    browser.stderr.setEncoding('utf8');
    browser.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-6000); });
    cdp = connectPipe(browser, message => {
      const p = message.params || {};
      if (message.method === 'Inspector.targetCrashed' || message.method === 'Target.targetCrashed') cdp.fail(new Error('Browser target crashed'));
      if (message.sessionId !== session) return;
      if (message.method === 'Page.lifecycleEvent' && p.name === 'load') loaded.add(p.loaderId);
      if (message.method === 'Runtime.exceptionThrown') error('exception', p.exceptionDetails.exception?.description || p.exceptionDetails.text);
      if (message.method === 'Runtime.consoleAPICalled' && p.type === 'error') error('console', p.args.map(arg => arg.description ?? JSON.stringify(arg.value) ?? arg.type).join(' '));
      if (message.method === 'Log.entryAdded' && p.entry.level === 'error') error('browser-log', p.entry.text);
      if (message.method === 'Fetch.requestPaused') {
        let allowed = true;
        try { loopbackUrl(p.request.url); } catch { allowed = false; }
        const request = allowed ? cdp.call('Fetch.continueRequest', { requestId: p.requestId }, session) :
          cdp.call('Fetch.failRequest', { requestId: p.requestId, errorReason: 'BlockedByClient' }, session);
        if (!allowed) error('navigation', 'Blocked non-loopback document: ' + p.request.url);
        request.catch(cdp.fail);
      }
    });
    const call = (method, params) => cdp.call(method, params, session);
    async function evaluate(expression) {
      const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result.value;
    }
    async function ready() {
      // Bound font/image readiness, including broken images. No app methods or DOM state mutation.
      await evaluate(`(async () => {
        let timer;
        try {
          await Promise.race([
            (async () => {
              if (document.readyState !== 'complete') await new Promise(resolve => window.addEventListener('load', resolve, {once:true}));
              await document.fonts.ready;
              await Promise.all(Array.from(document.images, image => image.decode()));
              await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            })(),
            new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Document/font/image readiness timed out')), 8000); })
          ]);
        } finally { clearTimeout(timer); }
      })()`);
    }
    async function key(keyName, modifiers = 0, commands = []) {
      const named = Object.hasOwn(namedKeys, keyName);
      const key = keyName === 'Space' ? ' ' : keyName;
      const code = named ? keyName : /^[a-z]$/i.test(key) ? 'Key' + key.toUpperCase() : /^\d$/.test(key) ? 'Digit' + key : '';
      const windowsVirtualKeyCode = named ? namedKeys[keyName] : /^[a-z0-9]$/i.test(key) ? key.toUpperCase().charCodeAt(0) : 0;
      const params = { key, code, windowsVirtualKeyCode, modifiers };
      const text = keyName === 'Enter' ? '\r' : !named || keyName === 'Space' ? key : undefined;
      await call('Input.dispatchKeyEvent', { type: 'keyDown', ...params, commands, ...(!modifiers && text ? { text, unmodifiedText: text } : {}) });
      await call('Input.dispatchKeyEvent', { type: 'keyUp', ...params });
    }
    async function click(css, fill = false) {
      const point = await evaluate(`(() => {
        const matches = document.querySelectorAll(${JSON.stringify(css)});
        if (matches.length !== 1) throw new Error('Selector must match exactly one element');
        const el = matches[0];
        if (!el.getClientRects().length || el.matches(':disabled') || el.closest('[inert]')) throw new Error('Control is hidden or disabled');
        if (${JSON.stringify(fill)} && (el.readOnly || !(el.isContentEditable || el.tagName === 'TEXTAREA' ||
            (el.tagName === 'INPUT' && ['text','search','email','url','tel','password','number'].includes(el.type))))) throw new Error('Fill requires an editable text control');
        el.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
        const r = el.getBoundingClientRect();
        const x = (Math.max(0,r.left) + Math.min(innerWidth,r.right))/2;
        const y = (Math.max(0,r.top) + Math.min(innerHeight,r.bottom))/2;
        const hit = document.elementFromPoint(x,y);
        if (r.width <= 0 || r.height <= 0 || !hit || !el.contains(hit)) throw new Error('Control is obscured or outside viewport');
        return {x,y};
      })()`);
      await call('Input.dispatchMouseEvent', { type: 'mouseMoved', ...point });
      await call('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
      await call('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
    }
    async function resize(width, height) {
      await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
      viewport = { width, height, deviceScaleFactor: 1 };
    }
    async function capture(name) {
      await ready();
      const measured = await evaluate(`({width:innerWidth,height:innerHeight,scrollX,scrollY,url:location.href,
        clientWidth:document.documentElement.clientWidth,
        scrollWidth:Math.max(document.documentElement.scrollWidth,document.body?.scrollWidth || 0)})`);
      loopbackUrl(measured.url);
      if (measured.width !== viewport.width || measured.height !== viewport.height) throw new Error('Browser viewport differs from requested dimensions');
      const overflow = { scrollWidth: measured.scrollWidth, viewportWidth: measured.width, clientWidth: measured.clientWidth,
        pixels: Math.max(0, measured.scrollWidth - measured.clientWidth) };
      const image = await call('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
      const bytes = Buffer.from(image.data, 'base64');
      if (bytes.length < 24 || bytes.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a' ||
          bytes.readUInt32BE(16) !== viewport.width || bytes.readUInt32BE(20) !== viewport.height) throw new Error('Screenshot PNG dimensions differ from viewport');
      const file = name + '.png';
      write(file, bytes);
      report.captures.push({ name, file, sha256: sha256(bytes), viewport: { ...viewport }, step,
        timestamp: stamp(), url: measured.url, scroll: { x: measured.scrollX, y: measured.scrollY }, reducedMotion, overflow });
      if (overflow.pixels > 0) error('overflow', `${name}: horizontal page overflow ${overflow.pixels}px`);
    }
    report.browserVersion = await cdp.call('Browser.getVersion');
    const { targetId } = await cdp.call('Target.createTarget', { url: 'about:blank' });
    session = (await cdp.call('Target.attachToTarget', { targetId, flatten: true })).sessionId;
    for (const domain of ['Page', 'Runtime', 'Log', 'Inspector']) await call(domain + '.enable');
    await call('Page.setLifecycleEventsEnabled', { enabled: true });
    await call('Fetch.enable', { patterns: [{ urlPattern: '*', resourceType: 'Document', requestStage: 'Request' }] });
    await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });
    await resize(options.width, options.height);
    const navigation = await call('Page.navigate', { url: options.url });
    if (navigation.errorText || !navigation.loaderId) throw new Error('Navigation failed: ' + (navigation.errorText || 'no document loader'));
    const deadline = Date.now() + 15000;
    while (!loaded.has(navigation.loaderId)) {
      cdp.check();
      if (Date.now() > deadline) throw new Error('Navigation load timed out');
      await pause(25);
    }
    await capture('initial');
    for (const instruction of options.steps) {
      step++;
      await ready();
      switch (instruction.action) {
        case 'click': await click(instruction.selector); break;
        case 'fill':
          await click(instruction.selector, true);
          // CDP's native editing command supplies macOS's missing platform key binding.
          await key('a', process.platform === 'darwin' ? 4 : 2, ['selectAll']);
          await key('Backspace');
          if (instruction.text) await call('Input.insertText', { text: instruction.text });
          break;
        case 'key': await key(instruction.key); break;
        case 'viewport': await resize(instruction.width, instruction.height); break;
        case 'media':
          reducedMotion = instruction.reducedMotion;
          await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: reducedMotion ? 'reduce' : 'no-preference' }] });
          break;
        case 'capture': await capture(instruction.name); break;
      }
    }
    await ready(); // Include errors from the final interaction even without a final capture.
    report.finalUrl = await evaluate('location.href');
    loopbackUrl(report.finalUrl);
    cdp.check();
  } catch (failure) {
    error('capture', failure.message);
    if (stderr) report.browserStderr = stderr;
  } finally {
    try { await stopBrowser(browser, cdp); }
    catch (failure) { cleanupSafe = false; error('cleanup', failure.message); }
    if (profile && cleanupSafe) {
      try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 }); }
      catch (failure) { error('cleanup', failure.message); }
    }
    process.off('SIGINT', onInt); process.off('SIGTERM', onTerm);
    report.finishedAt = stamp();
    report.status = report.errors.length ? 'failed' : 'passed';
    write('report.json', JSON.stringify(report, null, 2) + '\n');
  }
  console.log(`${report.status.toUpperCase()}: ${report.captures.length} viewport PNG(s), ${report.errors.length} error(s). Report: ${path.join(options.out, 'report.json')}`);
  if (report.errors.length) {
    console.error(report.errors[0].message.split('\n')[0]);
    process.exitCode = 1;
  }
}

if (process.argv.length === 3 && process.argv[2] === '--help') process.stdout.write(HELP);
else {
  Promise.resolve().then(() => parseArgs(process.argv.slice(2))).then(captureUI).catch(error => {
    console.error('FAILED: ' + error.message);
    process.exitCode = 1;
  });
}
