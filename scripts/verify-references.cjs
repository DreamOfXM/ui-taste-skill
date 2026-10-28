#!/usr/bin/env node
'use strict';
// Dependency-free, real-browser verification of offline references and the direction study.
// This checks behavior and rendering, not aesthetic quality or native applications.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { EventEmitter } = require('node:events');
const { createHash } = require('node:crypto');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'assets', 'reference-evidence');
const FILES = { '/workbench': 'reference-workbench.html', '/editorial': 'reference-editorial.html', '/studio': 'variant-board.html' };
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const quote = value => JSON.stringify(value);
const attr = (name, value) => `button[${name}=${quote(value)}]`;
const DEADLINE = 20000;

async function main() {
  const report = {
    scope: 'Real Chromium input, layout and screenshots of the offline HTML references and two-direction studio; not aesthetic or native-app approval',
    sources: {}, capturedAt: new Date().toISOString(), browser: null, status: 'failed',
    checks: [], captures: [], errors: [], externalRequests: []
  };
  let browser, server, profile, session, origin, viewport;
  let sequence = 0, buffer = '', shuttingDown = false, childExited = false;
  let childDone = Promise.resolve(), fatalError;
  const pending = new Map(), events = new EventEmitter(), intercepted = new Set();
  const sources = new Map();

  function failPending(error) {
    for (const request of pending.values()) {
      clearTimeout(request.timer);
      request.reject(error);
    }
    pending.clear();
  }
  function call(method, params = {}, sessionId = session) {
    if (!browser || childExited || !browser.stdio[3].writable) {
      return Promise.reject(new Error(`Chrome unavailable: ${method}`));
    }
    const id = ++sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`CDP deadline exceeded: ${method}`));
      }, DEADLINE);
      pending.set(id, { resolve, reject, timer });
      const message = { id, method, params, ...(sessionId ? { sessionId } : {}) };
      browser.stdio[3].write(JSON.stringify(message) + '\0', error => {
        if (error && pending.has(id)) {
          pending.delete(id);
          clearTimeout(timer);
          reject(error);
        }
      });
    });
  }
  function watch(method) {
    let listener, timer;
    const promise = new Promise((resolve, reject) => {
      listener = message => {
        if (message.sessionId === session) { clearTimeout(timer); resolve(message.params); }
      };
      events.on(method, listener);
      timer = setTimeout(() => reject(new Error(`Browser event deadline exceeded: ${method}`)), DEADLINE);
    });
    return { promise, cancel() { clearTimeout(timer); events.off(method, listener); } };
  }
  function isExternal(url) {
    if (/^(data:|about:)/i.test(url)) return false;
    try { return new URL(url).origin !== origin; } catch { return true; }
  }
  function recordExternal(url) {
    if (isExternal(url) && !report.externalRequests.includes(url)) report.externalRequests.push(url);
  }
  function receive(message) {
    if (pending.has(message.id)) {
      const request = pending.get(message.id);
      pending.delete(message.id);
      clearTimeout(request.timer);
      if (message.error) request.reject(new Error(message.error.message));
      else request.resolve(message.result);
    }
    if (message.sessionId === session) {
      const params = message.params || {};
      if (message.method === 'Runtime.exceptionThrown') {
        const detail = params.exceptionDetails;
        report.errors.push(`Uncaught: ${detail.exception?.description || detail.text}`);
      }
      if (message.method === 'Runtime.consoleAPICalled' && params.type === 'error') {
        report.errors.push('console.error: ' + params.args.map(arg => arg.description || String(arg.value)).join(' '));
      }
      if (message.method === 'Network.requestWillBeSent') recordExternal(params.request.url);
      if (message.method === 'Fetch.requestPaused') {
        const external = isExternal(params.request.url);
        recordExternal(params.request.url);
        // Block external page requests before they leave this machine.
        const operation = call(external ? 'Fetch.failRequest' : 'Fetch.continueRequest',
          { requestId: params.requestId, ...(external ? { errorReason: 'BlockedByClient' } : {}) }, message.sessionId)
          .catch(error => { if (!shuttingDown) report.errors.push(`Request interception: ${error.message}`); })
          .finally(() => intercepted.delete(operation));
        intercepted.add(operation);
      }
    }
    if (message.method) events.emit(message.method, message);
  }
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    }
    return result.result.value;
  }
  // Read the rendered DOM only. No app-specific globals or internal store access.
  async function dom(body) {
    return evaluate(`(() => {
      const visible = el => {
        if (!el || !el.getClientRects().length || el.closest('[hidden],[inert]')) return false;
        const style = getComputedStyle(el), rect = el.getBoundingClientRect();
        return style.visibility !== 'hidden' && style.display !== 'none' && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
      };
      const shown = selector => [...document.querySelectorAll(selector)].filter(visible);
      ${body}
    })()`);
  }
  function check(condition, label) {
    if (!condition) throw new Error(label);
    report.checks.push(label);
  }
  async function assertDOM(expression, label) {
    check(await dom(`return !!(${expression});`), label);
  }
  function healthy() {
    if (fatalError) throw fatalError;
    if (report.errors.length) throw new Error(report.errors.join('; '));
    if (report.externalRequests.length) throw new Error('External page requests: ' + report.externalRequests.join('; '));
  }
  async function settle() {
    // Font/image readiness and consecutive stable animation frames, never a sleep.
    await dom(`return (async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map(image => image.decode()));
      let previous = '', stable = 0;
      for (let frame = 0; frame < 120; frame++) {
        await new Promise(resolve => requestAnimationFrame(resolve));
        const layout = JSON.stringify([
          document.documentElement.scrollWidth, document.documentElement.scrollHeight,
          ...shown('main,section,article,button,input,h1,h2,.resource-row,#detail-panel,.specimen,#specimen-detail').map(el => {
            const r = el.getBoundingClientRect();
            return [r.x, r.y, r.width, r.height].map(n => Math.round(n * 100) / 100);
          })
        ]);
        stable = layout === previous ? stable + 1 : 0;
        if (stable >= 2) return true;
        previous = layout;
      }
      throw new Error('Layout did not stabilize within 120 animation frames');
    })();`);
    healthy();
  }
  async function click(selector) {
    await dom(`const el = document.querySelector(${quote(selector)});
      if (!visible(el) || el.disabled) throw new Error('Missing, hidden or disabled control: ' + ${quote(selector)});
      el.scrollIntoView({block:'center', inline:'nearest', behavior:'instant'});`);
    await settle();
    const point = await dom(`const el = document.querySelector(${quote(selector)});
      if (!visible(el) || el.disabled) throw new Error('Control disappeared: ' + ${quote(selector)});
      const r = el.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
      if (!el.contains(document.elementFromPoint(x, y))) throw new Error('Control is obstructed: ' + ${quote(selector)});
      return {x, y};`);
    await call('Input.dispatchMouseEvent', { type: 'mouseMoved', ...point });
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
    await settle();
  }
  async function key(keyName, code, keyCode, modifiers = 0, commands) {
    const params = { key: keyName, code, windowsVirtualKeyCode: keyCode, modifiers };
    // Chromium needs Enter's text event to perform native button activation.
    await call('Input.dispatchKeyEvent', { type: 'keyDown', ...params, ...(keyName === 'Enter' ? { text: '\r' } : {}), ...(commands ? { commands } : {}) });
    await call('Input.dispatchKeyEvent', { type: 'keyUp', ...params });
    await settle();
  }
  async function search(text) {
    await click('#search-input');
    await key('a', 'KeyA', 65, process.platform === 'darwin' ? 4 : 2, ['selectAll']);
    await key('Backspace', 'Backspace', 8);
    if (text) await call('Input.insertText', { text });
    await settle();
    await assertDOM(`document.querySelector('#search-input').value === ${quote(text)}`, 'Search receives the exact CDP keyboard/text input');
  }
  async function size(width, height) {
    viewport = [width, height];
    await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  }
  async function navigate(route) {
    const loaded = watch('Page.loadEventFired');
    try {
      await Promise.all([
        loaded.promise,
        call('Page.navigate', { url: origin + route }).then(result => {
          if (result.errorText) throw new Error('Navigation failed: ' + result.errorText);
        })
      ]);
    } finally { loaded.cancel(); }
    await settle();
    await assertDOM(`location.origin === ${quote(origin)} && document.readyState === 'complete'`, `${route}: local document finished loading`);
  }
  async function noOverflow(label) {
    await assertDOM(`document.documentElement.scrollWidth <= innerWidth + 1 && document.body.scrollWidth <= innerWidth + 1`, `${label}: no horizontal page overflow`);
    await assertDOM(`shown('.resource-row,#detail-panel,#empty-state,#index-view,#article-view,#saved-empty,.specimen,#specimen-detail,#specimen-empty').every(el => el.scrollWidth <= el.clientWidth + 1)`, `${label}: no horizontal content-panel overflow`);
  }
  async function reducedMotion(label) {
    const problems = await dom(`const problems = [];
      const milliseconds = value => value.split(',').map(s => parseFloat(s) * (s.trim().endsWith('ms') ? 1 : 1000));
      for (const el of shown('*')) {
        for (const pseudo of [null, '::before', '::after']) {
          const s = getComputedStyle(el, pseudo);
          if (pseudo && (s.content === 'none' || s.content === 'normal')) continue;
          for (const name of ['animationDuration','animationDelay','transitionDuration','transitionDelay']) {
            if (milliseconds(s[name]).some(value => value > 10)) problems.push(el.tagName + '#' + el.id + (pseudo || '') + ':' + name + '=' + s[name]);
          }
        }
      }
      for (const animation of document.getAnimations()) {
        if (animation.playState === 'running' && animation.effect.getComputedTiming().activeDuration > 10) problems.push('Running animation exceeds 10ms');
      }
      return {matches: matchMedia('(prefers-reduced-motion: reduce)').matches, problems: problems.slice(0, 12)};`);
    check(problems.matches && !problems.problems.length, `${label}: reduced-motion durations/delays <= 10ms${problems.problems.length ? ' (' + problems.problems.join('; ') + ')' : ''}`);
  }
  async function keyboardFocus(label) {
    await key('Tab', 'Tab', 9);
    await assertDOM(`(() => {
      const el = document.activeElement;
      if (!visible(el) || el === document.body || !el.matches(':focus-visible')) return false;
      const style = getComputedStyle(el);
      return (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0 && style.outlineColor !== 'rgba(0, 0, 0, 0)') || style.boxShadow !== 'none';
    })()`, `${label}: real Tab input produces a visible focus indicator`);
  }
  async function capture(file, surface, state, validate, fullPage = false) {
    await evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})");
    await settle();
    await validate();
    await noOverflow(file);
    await reducedMotion(file);
    await assertDOM(`innerWidth === ${viewport[0]} && innerHeight === ${viewport[1]}`, `${file}: expected viewport`);
    healthy();
    const metrics = await call('Page.getLayoutMetrics');
    const image = await call('Page.captureScreenshot', {
      format: 'png', fromSurface: true, captureBeyondViewport: fullPage,
      ...(fullPage ? { clip: { x: 0, y: 0, width: viewport[0], height: Math.max(viewport[1], Math.ceil(metrics.cssContentSize.height)), scale: 1 } } : {})
    });
    const bytes = Buffer.from(image.data, 'base64');
    check(bytes.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex')), `${file}: real PNG returned by Chrome`);
    check(bytes.readUInt32BE(16) === viewport[0] && (fullPage ? bytes.readUInt32BE(20) >= viewport[1] : bytes.readUInt32BE(20) === viewport[1]), `${file}: screenshot dimensions match capture mode`);
    healthy();
    fs.writeFileSync(path.join(OUT, file), bytes);
    report.captures.push({ file, sha256: sha256(bytes), viewport: [...viewport], surface, state });
  }

  async function rows() {
    return dom(`return shown('.resource-row[data-id]').map(row => {
      const id = row.dataset.id;
      const select = [...row.querySelectorAll('button[data-select-id]')].find(el => el.dataset.selectId === id);
      const favorite = [...row.querySelectorAll('button[data-favorite-id]')].find(el => el.dataset.favoriteId === id);
      if (!select || !favorite || !select.textContent.trim() || !['true','false'].includes(favorite.getAttribute('aria-pressed'))) throw new Error('Resource row lacks content, selection or favorite semantics: ' + id);
      return {id, title: select.textContent.trim(), favorite: favorite.getAttribute('aria-pressed') === 'true'};
    });`);
  }
  const ids = records => records.map(record => record.id);
  function sameIds(actual, expected, label) {
    check(new Set(actual).size === actual.length && JSON.stringify([...actual].sort()) === JSON.stringify([...expected].sort()), label);
  }
  async function workbenchList(expected, label, mobile = false) {
    const current = await rows();
    sameIds(ids(current), expected, `${label}: expected resources`);
    await assertDOM(`['#search-input', "button[data-view='all']", "button[data-view='favorites']", "button[data-filter='all']", "button[data-filter='document']", "button[data-filter='link']", '#result-count'].every(s => visible(document.querySelector(s)))`, `${label}: list controls are visible`);
    await assertDOM(`(document.querySelector('#result-count').textContent.match(/[0-9]+/g) || []).some(n => Number(n) === ${expected.length})`, `${label}: result count matches the rendered list`);
    if (expected.length === 0) await assertDOM(`visible(document.querySelector('#empty-state')) && !!document.querySelector('#empty-state').textContent.trim()`, `${label}: informative empty state is visible`);
    else await assertDOM(`!visible(document.querySelector('#empty-state'))`, `${label}: empty state is hidden for results`);
    if (mobile) await assertDOM(`!visible(document.querySelector('#detail-panel'))`, `${label}: narrow list does not show the detail pane`);
  }
  async function detail(id, label, mobile = false) {
    await assertDOM(`visible(document.querySelector('#detail-panel')) && visible(document.querySelector('#close-detail')) && shown('#detail-panel button[data-favorite-id]').some(el => el.dataset.favoriteId === ${quote(id)}) && document.querySelector('#detail-panel').textContent.trim().length > 30`, `${label}: selected resource content and detail controls are visible`);
    if (mobile) await assertDOM(`shown('.resource-row[data-id]').length === 0`, `${label}: narrow details replace the list`);
  }
  async function pressed(selector) {
    const value = await dom(`return document.querySelector(${quote(selector)})?.getAttribute('aria-pressed');`);
    check(value === 'true' || value === 'false', `${selector}: exposes aria-pressed`);
    return value === 'true';
  }
  async function filter(value) {
    const selector = attr('data-filter', value);
    await click(selector);
    check(await pressed(selector), `Workbench ${value} filter is active`);
  }
  async function view(value) {
    const selector = attr('data-view', value);
    await click(selector);
    check(await pressed(selector), `Workbench ${value} view is active`);
  }
  async function favoriteSynced(id, expected, label) {
    check(await pressed('.resource-row ' + attr('data-favorite-id', id)) === expected, `${label}: row favorite state`);
    check(await pressed('#detail-panel ' + attr('data-favorite-id', id)) === expected, `${label}: detail favorite state`);
  }

  async function verifyWorkbench() {
    await size(1440, 960);
    await navigate('/workbench');
    const initial = await rows(), allIds = ids(initial), first = initial[0];
    check(initial.length >= 9, 'Workbench has at least nine default resources');
    await workbenchList(allIds, 'Default workbench');
    await assertDOM(`visible(document.querySelector('#detail-panel')) && shown('#detail-panel button[data-favorite-id]').length > 0`, 'Desktop workbench starts with selected details');
    await keyboardFocus('Desktop workbench');
    await click(attr('data-select-id', first.id));
    await capture('workbench-desktop.png', 'workbench', 'all resources; first resource selected', async () => {
      await workbenchList(allIds, 'Desktop capture');
      await detail(first.id, 'Desktop capture');
    });

    const typeIds = {};
    for (const type of ['document', 'link']) {
      await filter(type);
      typeIds[type] = ids(await rows());
      check(typeIds[type].length > 0 && typeIds[type].length < allIds.length && typeIds[type].every(id => allIds.includes(id)), `Workbench ${type} filter narrows the dataset`);
      await workbenchList(typeIds[type], `${type} filter`);
    }
    check(!typeIds.document.some(id => typeIds.link.includes(id)), 'Document and link filters produce distinct resource types');
    await filter('all');
    await click(attr('data-select-id', first.id));
    const rowFavorite = '.resource-row ' + attr('data-favorite-id', first.id);
    const detailFavorite = '#detail-panel ' + attr('data-favorite-id', first.id);
    const wasFavorite = await pressed(rowFavorite);
    await click(rowFavorite);
    await favoriteSynced(first.id, !wasFavorite, 'Row toggle synchronizes details');
    if (wasFavorite) await click(rowFavorite);
    await favoriteSynced(first.id, true, 'First resource is saved');
    await click(detailFavorite);
    await favoriteSynced(first.id, false, 'Detail toggle removes the favorite');
    await click(detailFavorite);
    await favoriteSynced(first.id, true, 'Detail toggle restores the favorite');
    const favoriteIds = ids((await rows()).filter(row => row.favorite));
    await view('favorites');
    await workbenchList(favoriteIds, 'Favorites view');
    for (const type of ['document', 'link']) {
      await filter(type);
      await workbenchList(favoriteIds.filter(id => typeIds[type].includes(id)), `Favorites combined with ${type}`);
    }
    const firstType = ['document', 'link'].find(type => typeIds[type].includes(first.id));
    check(!!firstType, 'The first resource belongs to a supported document/link filter');
    await filter(firstType);
    const intersection = favoriteIds.filter(id => typeIds[firstType].includes(id));
    const query = Array.from(first.title.replace(/\s+/g, ' ').trim().split(' ')[0]).slice(0, 6).join('');
    check(query.length > 0, 'First resource exposes a searchable title');
    await search(query);
    const matches = ids(await rows());
    check(matches.includes(first.id) && matches.every(id => intersection.includes(id)), 'Favorites, type and positive search combine without leaking other resources');
    await workbenchList(matches, 'Combined positive search');

    await search('<b>不存在</b>');
    const emptyCheck = async () => {
      await workbenchList([], 'Literal HTML search empty state');
      await assertDOM(`document.querySelector('#search-input').value === '<b>不存在</b>' && ![...document.querySelectorAll('b')].some(el => el.textContent.includes('不存在'))`, 'HTML-like search stays text and never becomes a DOM element');
      await assertDOM(`visible(document.querySelector('#clear-search'))`, 'Empty search offers a visible clear control');
    };
    await capture('workbench-empty.png', 'workbench', 'favorites + type + literal HTML search; no results', emptyCheck);
    await click('#clear-search');
    await assertDOM(`document.querySelector('#search-input').value === ''`, 'Clear search resets the input');
    await workbenchList(intersection, 'Clear preserves favorites and type filters');
    await filter('all');
    await view('all');
    await workbenchList(allIds, 'All resources restored');

    // A fresh document navigation, not an app-internal state change.
    await navigate('/workbench?view=favorites');
    check(await pressed(attr('data-view', 'favorites')), 'Favorites URL independently initializes the favorites view');
    const direct = await rows();
    check(direct.every(row => row.favorite), 'Direct favorites URL contains only saved resources');
    await workbenchList(ids(direct), 'Independently loaded favorites');
    await view('all');
    const loadedFavorites = ids((await rows()).filter(row => row.favorite));
    sameIds(ids(direct), loadedFavorites, 'Direct favorites URL matches the newly loaded resource state');

    await size(390, 844);
    await navigate('/workbench');
    if (await dom("return visible(document.querySelector('#detail-panel')) && visible(document.querySelector('#close-detail'));")) await click('#close-detail');
    const mobileRows = await rows(), mobileIds = ids(mobileRows), mobileFirst = mobileRows[0];
    check(mobileRows.length >= 9, 'Mobile list retains the complete resource collection');
    await keyboardFocus('Mobile workbench');
    const longQuery = '很长的资源名称与说明用于验证窄屏换行和边界'.repeat(12);
    await search(longQuery);
    await workbenchList([], 'Long-text mobile search', true);
    await noOverflow('Long-text mobile search');
    await click('#clear-search');
    await capture('workbench-mobile.png', 'workbench', 'narrow list; search cleared', () => workbenchList(mobileIds, 'Mobile list capture', true));
    await click(attr('data-select-id', mobileFirst.id));
    await capture('workbench-detail-mobile.png', 'workbench', 'narrow detail; first resource selected', () => detail(mobileFirst.id, 'Mobile detail capture', true));
    await click('#close-detail');
    await workbenchList(mobileIds, 'Mobile detail returns to list', true);
    const longest = [...mobileRows].sort((a, b) => b.title.length - a.title.length)[0];
    await click(attr('data-select-id', longest.id));
    await detail(longest.id, 'Longest resource title remains usable', true);
    await noOverflow('Longest resource title in mobile details');
    await click('#close-detail');
    await workbenchList(mobileIds, 'Return from longest resource', true);
  }

  async function articles() {
    return dom(`return shown('#article-directory button[data-open-article]').map(el => {
      if (!el.dataset.openArticle || !el.textContent.trim()) throw new Error('Article opener lacks an ID or readable content');
      return el.dataset.openArticle;
    });`);
  }
  async function editorialIndex(expected, label, savedEmpty = false) {
    sameIds(await articles(), expected, `${label}: expected article entries`);
    await assertDOM(`visible(document.querySelector('#index-view')) && !visible(document.querySelector('#article-view'))`, `${label}: index, not article, is visible`);
    await assertDOM(`['all','type','space'].every(topic => visible(document.querySelector('button[data-topic="' + topic + '"]')))`, `${label}: topic controls are visible`);
    if (savedEmpty) await assertDOM(`visible(document.querySelector('#saved-empty')) && !!document.querySelector('#saved-empty').textContent.trim() && visible(document.querySelector('#show-all'))`, `${label}: empty saved collection offers a way back`);
    else if (expected.length) await assertDOM(`!visible(document.querySelector('#saved-empty'))`, `${label}: no stale saved-empty message`);
  }
  async function editorialArticle(id, label) {
    await assertDOM(`visible(document.querySelector('#article-view')) && !visible(document.querySelector('#index-view')) && document.querySelector('#article-view').dataset.articleId === ${quote(id)}`, `${label}: the selected article replaces the index`);
    await assertDOM(`visible(document.querySelector('#back-to-index')) && visible(document.querySelector('#toggle-article-save')) && shown('#article-view h1,#article-view h2').some(el => el.textContent.trim()) && shown('#article-view p').some(el => el.textContent.trim())`, `${label}: article has a heading, readable body and navigation controls`);
  }
  async function backToIndex(id, removed = false) {
    await click('#back-to-index');
    await assertDOM(`visible(document.querySelector('#index-view')) && !visible(document.querySelector('#article-view'))`, 'Back returns from article to index');
    if (!removed) {
      await assertDOM(`visible(document.activeElement) && document.activeElement.closest('button[data-open-article]')?.dataset.openArticle === ${quote(id)}`, 'Back restores focus to the originating article');
    } else {
      await assertDOM(`visible(document.activeElement) && document.activeElement !== document.body && document.activeElement !== document.documentElement && !document.activeElement.closest('#article-view')`, 'Removing a saved opener leaves focus on a visible index control or fallback');
    }
  }
  async function verifyEditorial() {
    await size(1440, 1000);
    await navigate('/editorial');
    const all = await articles();
    check(all.length === 3 && new Set(all).size === 3, 'Editorial index has three distinct default articles');
    await editorialIndex(all, 'Default editorial index');
    await keyboardFocus('Desktop editorial');
    const topics = {};
    for (const topic of ['type', 'space']) {
      await click(attr('data-topic', topic));
      topics[topic] = await articles();
      check(topics[topic].length > 0 && topics[topic].length < all.length && topics[topic].every(id => all.includes(id)), `Editorial ${topic} filter narrows the index`);
      await editorialIndex(topics[topic], `${topic} topic`);
    }
    check(JSON.stringify([...topics.type].sort()) !== JSON.stringify([...topics.space].sort()), 'Editorial topics have distinct results');
    await click(attr('data-topic', 'all'));
    await capture('editorial-desktop.png', 'editorial', 'complete article index', () => editorialIndex(all, 'Desktop editorial capture'), true);
    const first = all[0];
    await click(attr('data-open-article', first));
    await capture('editorial-article.png', 'editorial', 'first article; reading view', () => editorialArticle(first, 'Desktop article capture'), true);
    if (await pressed('#toggle-article-save')) await click('#toggle-article-save');
    check(!(await pressed('#toggle-article-save')), 'Article can be unsaved');
    await click('#toggle-article-save');
    check(await pressed('#toggle-article-save'), 'Article can be saved');
    await backToIndex(first);
    await click('#show-saved');
    const saved = await articles();
    check(saved.includes(first) && saved.every(id => all.includes(id)), 'Saved index includes the newly saved article');
    await editorialIndex(saved, 'Saved articles');
    for (const topic of ['type', 'space']) {
      await click(attr('data-topic', topic));
      sameIds(await articles(), saved.filter(id => topics[topic].includes(id)), `Saved articles combine with ${topic} topic`);
    }
    await click(attr('data-topic', 'all'));
    sameIds(await articles(), saved, 'All topics restores the saved collection');
    let remaining = [...saved];
    for (const id of saved) {
      await click('#article-directory ' + attr('data-open-article', id));
      await editorialArticle(id, 'Saved article opens');
      check(await pressed('#toggle-article-save'), 'Saved article exposes its saved state');
      await click('#toggle-article-save');
      check(!(await pressed('#toggle-article-save')), 'Removing a saved article updates its control');
      await backToIndex(id, true);
      remaining = remaining.filter(value => value !== id);
      sameIds(await articles(), remaining, 'Unsaving removes only that article from the saved index');
    }
    await editorialIndex([], 'All saved articles removed', true);
    await noOverflow('Editorial saved empty state');
    await click('#show-all');
    await editorialIndex(all, 'Show all restores the three articles');

    await size(390, 844);
    await navigate('/editorial');
    const mobile = await articles();
    sameIds(mobile, all, 'Mobile editorial retains all articles');
    await keyboardFocus('Mobile editorial');
    await capture('editorial-mobile.png', 'editorial', 'narrow article index', () => editorialIndex(mobile, 'Mobile editorial capture'), true);
    await click(attr('data-open-article', mobile[0]));
    await editorialArticle(mobile[0], 'Mobile article opens');
    await assertDOM(`shown('#article-view p').some(el => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return new Set([...range.getClientRects()].map(rect => Math.round(rect.y))).size > 1;
    })`, 'Mobile long-form article text wraps onto multiple lines');
    await noOverflow('Mobile long-form article');
    const savedBefore = await pressed('#toggle-article-save');
    await click('#toggle-article-save');
    check(await pressed('#toggle-article-save') === !savedBefore, 'Mobile article save button changes state');
    await click('#toggle-article-save');
    check(await pressed('#toggle-article-save') === savedBefore, 'Mobile article save toggle is reversible');
    await backToIndex(mobile[0]);
    await key('Enter', 'Enter', 13);
    await capture('editorial-article-mobile.png', 'editorial', 'narrow long-form article; opened with keyboard', () => editorialArticle(mobile[0], 'Mobile article capture'), true);
    await backToIndex(mobile[0]);
    await editorialIndex(mobile, 'Mobile article returns to complete index');
  }

  async function studioRows() {
    return dom(`return shown('.specimen[data-id]').map(row => {
      const opener = row.querySelector('button[data-open-specimen]');
      const save = row.querySelector('button[data-save-specimen]');
      if (!opener || !save || !['true','false'].includes(save.getAttribute('aria-pressed'))) throw new Error('Specimen lacks native controls or save state');
      return {id: row.dataset.id, saved: save.getAttribute('aria-pressed') === 'true'};
    });`);
  }
  async function studioIndex(expected, label) {
    sameIds(ids(await studioRows()), expected, `${label}: expected specimens`);
    await assertDOM(`visible(document.querySelector('#specimen-search')) && visible(document.querySelector('#specimen-count'))`, `${label}: search and count are visible`);
    await assertDOM(`Number(document.querySelector('#specimen-count').textContent.match(/^[0-9]+/)?.[0]) === ${expected.length}`, `${label}: count matches records`);
    await assertDOM(`visible(document.querySelector('#specimen-empty')) === ${expected.length === 0}`, `${label}: empty state matches results`);
  }
  async function studioDetail(id, label, mobile = false) {
    await assertDOM(`visible(document.querySelector('#specimen-detail')) && document.querySelector('#specimen-detail').dataset.id === ${quote(id)} && visible(document.querySelector('#detail-save')) && document.querySelector('#specimen-detail').textContent.trim().length > 60`, `${label}: selected specimen and details are visible`);
    if (mobile) await assertDOM(`shown('.specimen[data-id]').length === 0 && visible(document.querySelector('#close-specimen'))`, `${label}: details replace the narrow list and offer return`);
  }
  async function studioDirection(direction) {
    await click(attr('data-direction', direction));
    check(await pressed(attr('data-direction', direction)), `${direction}: active direction is exposed`);
    await assertDOM(`document.querySelector('#type-app').dataset.direction === ${quote(direction)}`, `${direction}: rendered app uses the chosen direction`);
  }
  async function studioSearch(text) {
    await click('#specimen-search');
    await key('a', 'KeyA', 65, process.platform === 'darwin' ? 4 : 2, ['selectAll']);
    await key('Backspace', 'Backspace', 8);
    if (text) await call('Input.insertText', { text });
    await settle();
    await assertDOM(`document.querySelector('#specimen-search').value === ${quote(text)}`, 'Studio receives literal search text');
  }
  async function studioProof(text) {
    await click('#specimen-custom-text');
    await key('a', 'KeyA', 65, process.platform === 'darwin' ? 4 : 2, ['selectAll']);
    await key('Backspace', 'Backspace', 8);
    await call('Input.insertText', { text });
    await settle();
    await assertDOM(`document.querySelector('#specimen-custom-text').value === ${quote(text)} && document.querySelector('#proof-text').textContent === ${quote(text)} && !document.querySelector('#proof-text').children.length`, 'Custom specimen text is rendered literally and matches the input');
  }
  async function verifyStudio() {
    await size(1440, 960);
    await navigate('/studio');
    const all = ids(await studioRows()), first = all[0];
    check(all.length === 6, 'Studio has six complete specimen records');
    await studioIndex(all, 'Default studio');
    await click(attr('data-open-specimen', first));
    await studioDetail(first, 'Gallery selected specimen');
    await keyboardFocus('Gallery studio');
    const geometry = () => dom(`const r = shown('.specimen[data-id]')[0].getBoundingClientRect(); return {width:r.width,height:r.height};`);
    const gallery = await geometry();
    await capture('studio-gallery-desktop.png', 'studio-gallery', 'gallery composition; first specimen selected', async () => {
      await studioIndex(all, 'Gallery desktop');
      await studioDetail(first, 'Gallery desktop');
    }, true);
    await studioDirection('instrument');
    await studioIndex(all, 'Direction switch preserves records');
    await studioDetail(first, 'Direction switch preserves selection');
    const instrument = await geometry();
    check(Math.abs(gallery.width - instrument.width) > 100 || Math.abs(gallery.height - instrument.height) > 50, 'Directions change object geometry, not just colors');
    await capture('studio-instrument-desktop.png', 'studio-instrument', 'instrument composition; same specimen selected', async () => {
      await studioIndex(all, 'Instrument desktop');
      await studioDetail(first, 'Instrument desktop');
    }, true);
    const categories = {};
    for (const category of ['serif','sans','mono']) {
      await click(attr('data-category', category));
      check(await pressed(attr('data-category', category)), `${category}: active studio category`);
      categories[category] = ids(await studioRows());
      check(categories[category].length > 0 && categories[category].length < all.length, `${category}: category narrows the studio`);
      await studioIndex(categories[category], category);
    }
    sameIds(Object.values(categories).flat(), all, 'Studio categories partition the same six records');
    await click(attr('data-category', 'all'));
    for (const id of all) {
      await click(attr('data-open-specimen', id));
      await studioDetail(id, 'Each font opens its own details');
      await assertDOM(`document.querySelector('#proof-text').textContent === document.querySelector('.specimen[data-id=${quote(id)}] .specimen-sample').textContent`, `${id}: detail shows the selected specimen's actual text`);
      await noOverflow(`${id}: instrument detail`);
    }
    await click(attr('data-open-specimen', first));
    const rowSave = attr('data-save-specimen', first);
    if (await pressed(rowSave)) await click(rowSave);
    await click('#detail-save');
    check(await pressed(rowSave) && await pressed('#detail-save'), 'Saving a specimen synchronizes row and details');
    const saved = ids((await studioRows()).filter(row => row.saved));
    await click(attr('data-collection', 'saved'));
    await studioIndex(saved, 'Saved studio collection');
    const category = Object.keys(categories).find(value => categories[value].includes(first));
    await click(attr('data-category', category));
    const intersection = saved.filter(id => categories[category].includes(id));
    await studioIndex(intersection, 'Saved and category intersection');
    const query = await dom(`return document.querySelector('.specimen[data-id=${quote(first)}] .font-name').textContent;`);
    await studioSearch(query);
    await studioIndex([first], 'Positive search combines with saved and category filters');
    await studioSearch('<b>不存在</b>');
    await studioIndex([], 'Literal unmatched studio search');
    await assertDOM(`![...document.querySelectorAll('b')].some(el => el.textContent.includes('不存在'))`, 'HTML-like studio search never becomes markup');
    await studioDirection('gallery');
    await studioIndex([], 'Direction switch preserves search and filters');
    await assertDOM(`document.querySelector('#specimen-search').value === '<b>不存在</b>' && document.querySelector('button[data-category=${quote(category)}]').getAttribute('aria-pressed') === 'true' && document.querySelector('button[data-collection="saved"]').getAttribute('aria-pressed') === 'true'`, 'Direction switch keeps the full filter state');
    await click('#clear-specimen-filters');
    await assertDOM(`document.querySelector('#specimen-search').value === ''`, 'Studio clear control clears the query');
    check(await pressed(attr('data-category', 'all')) && await pressed(attr('data-collection', 'all')), 'Studio clear control resets both filters');
    await studioIndex(all, 'Studio resets without losing records');
    const originalProof = await dom(`return document.querySelector('#proof-text').textContent;`);
    const draft = '<b>字间 & space</b>\n保持同一句试样';
    await studioProof(draft);
    await studioDirection('instrument');
    await assertDOM(`document.querySelector('#proof-text').textContent === ${quote(draft)}`, 'Direction switch preserves custom specimen text');
    await click(attr('data-open-specimen', all[1]));
    await assertDOM(`document.querySelector('#specimen-custom-text').value === ''`, 'Specimens keep separate drafts');
    await click(attr('data-open-specimen', first));
    await assertDOM(`document.querySelector('#proof-text').textContent === ${quote(draft)}`, 'Returning to a specimen restores its draft');
    await click('#reset-proof');
    await assertDOM(`document.querySelector('#proof-text').textContent === ${quote(originalProof)} && document.querySelector('#reset-proof').disabled`, 'Reset restores the original specimen');
    await navigate('/studio?direction=instrument');
    check(await pressed(rowSave), 'Studio favorites survive navigation');
    await assertDOM(`document.querySelector('#type-app').dataset.direction === 'instrument'`, 'Direction query opens the intended composition');
    for (const direction of ['gallery','instrument']) {
      await size(390, 844);
      await navigate('/studio?direction=' + direction);
      await studioIndex(all, `${direction} mobile`);
      await keyboardFocus(`${direction} mobile`);
      await capture(`studio-${direction}-mobile.png`, `studio-${direction}`, 'narrow collection; all six specimens', () => studioIndex(all, `${direction} narrow capture`), true);
      await click(attr('data-open-specimen', first));
      await studioDetail(first, `${direction} mobile selection`, true);
      await studioProof('窄屏长句与 <b>符号</b> ABC 0123 '.repeat(5));
      await noOverflow(`${direction}: long custom specimen on mobile`);
      await click('#reset-proof');
      const wasSaved = await pressed('#detail-save');
      await click('#detail-save');
      check(await pressed('#detail-save') === !wasSaved, `${direction}: mobile save changes state`);
      await click('#detail-save');
      check(await pressed('#detail-save') === wasSaved, `${direction}: mobile save is reversible`);
      await click('#close-specimen');
      await studioIndex(all, `${direction} returns to collection`);
      await assertDOM(`document.activeElement.closest('button[data-open-specimen]')?.dataset.openSpecimen === ${quote(first)}`, `${direction}: returning restores the specimen focus`);
      await key('Enter', 'Enter', 13);
      await capture(`studio-${direction}-detail-mobile.png`, `studio-${direction}`, 'narrow selected specimen; keyboard activation', () => studioDetail(first, `${direction} narrow detail capture`, true), true);
      await key('Escape', 'Escape', 27);
      await studioIndex(all, `${direction}: Escape returns to specimens`);
    }
    await size(1440, 960);
    await navigate('/studio');
    await click(attr('data-collection', 'saved'));
    for (const row of await studioRows()) await click(attr('data-save-specimen', row.id));
    await studioIndex([], 'Removing all saved specimens');
    await assertDOM(`document.activeElement.id === 'clear-specimen-filters' && visible(document.activeElement)`, 'Removing the last saved row moves focus to the recovery control');
    await click('#clear-specimen-filters');
    await studioIndex(all, 'Empty saved collection offers a working recovery');
    for (const direction of ['gallery','instrument']) {
      for (const width of [320, 768, 1024]) {
        await size(width, 844);
        await navigate('/studio?direction=' + direction);
        await studioIndex(all, `${direction} at ${width}px`);
        await noOverflow(`${direction} collection at ${width}px`);
        await click(attr('data-open-specimen', 'menlo'));
        await studioDetail('menlo', `${direction} code specimen at ${width}px`, width <= 760);
        await noOverflow(`${direction} code specimen at ${width}px`);
      }
    }
    await size(1440, 960);
    const storageBlock = await call('Page.addScriptToEvaluateOnNewDocument', {
      source: "Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('Storage blocked for verification', 'SecurityError');}});"
    });
    try {
      await navigate('/studio');
      await studioIndex(all, 'Storage-blocked studio loads');
      await click('#detail-save');
      check(await pressed(rowSave) && await pressed('#detail-save'), 'Storage-blocked studio can still save in memory');
      await assertDOM(`document.querySelector('#storage-note').textContent.includes('本次页面')`, 'Unavailable storage is described honestly');
    } finally { await call('Page.removeScriptToEvaluateOnNewDocument', {identifier: storageBlock.identifier}); }
  }

  function noteFailure(error) {
    report.status = 'failed';
    const message = error instanceof Error ? error.message : String(error);
    report.error = report.error ? report.error + '; ' + message : message;
    process.exitCode = 1;
  }
  function deadline(promise, milliseconds, label) {
    let timer;
    return Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(label)), milliseconds);
    })]).finally(() => clearTimeout(timer));
  }
  const interrupt = signal => {
    fatalError = new Error(`Interrupted by ${signal}`);
    failPending(fatalError);
    // Kill only the child spawned by this run, never a user browser/process group.
    if (browser && !childExited) browser.kill('SIGTERM');
  };
  const onSigint = () => interrupt('SIGINT'), onSigterm = () => interrupt('SIGTERM');
  process.on('SIGINT', onSigint);
  process.on('SIGTERM', onSigterm);
  try {
    fs.mkdirSync(OUT, { recursive: true });
    for (const [route, file] of Object.entries(FILES)) {
      const bytes = fs.readFileSync(path.join(ROOT, 'assets', file));
      report.sources[file] = sha256(bytes);
      sources.set(route, bytes);
    }
    const executable = [process.env.CHROME_BIN,
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Chromium.app/Contents/MacOS/Chromium',
      '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
      process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google/Chrome/Application/chrome.exe')
    ].find(candidate => candidate && fs.existsSync(candidate));
    if (!executable) throw new Error('Chrome/Chromium was not found. Set CHROME_BIN to an installed executable.');
    profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ui-taste-skill-references-'));
    server = http.createServer((req, res) => {
      // Named routes only; no static directory, path traversal or proxying.
      if (!['GET', 'HEAD'].includes(req.method) || !/^\/(?:workbench|editorial|studio)(?:\?[^\r\n]*)?$/.test(req.url)) {
        res.writeHead(404); res.end(); return;
      }
      const source = sources.get(req.url.split('?')[0]);
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
      res.end(req.method === 'HEAD' ? undefined : source);
    });
    server.on('error', error => { fatalError = error; failPending(error); });
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', () => { server.off('error', reject); resolve(); });
    });
    origin = `http://127.0.0.1:${server.address().port}`;
    browser = spawn(executable, [
      '--headless=new', '--remote-debugging-pipe', '--no-first-run', '--no-default-browser-check',
      '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-default-apps',
      '--disable-domain-reliability', '--disable-client-side-phishing-detection', '--metrics-recording-only',
      '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
      `--user-data-dir=${profile}`
    ], { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
    childDone = new Promise(resolve => {
      browser.once('exit', (code, signal) => {
        childExited = true;
        if (!shuttingDown) fatalError = new Error(`Chrome exited unexpectedly (${code ?? signal})`);
        failPending(fatalError || new Error('Chrome closed'));
        resolve();
      });
      browser.once('error', error => { childExited = true; fatalError = error; failPending(error); resolve(); });
    });
    browser.stderr.resume();
    browser.stdio[3].on('error', error => { if (!shuttingDown) fatalError = error; failPending(error); });
    browser.stdio[4].setEncoding('utf8');
    browser.stdio[4].on('error', error => { if (!shuttingDown) fatalError = error; failPending(error); });
    browser.stdio[4].on('data', data => {
      buffer += data;
      let end;
      while ((end = buffer.indexOf('\0')) >= 0) {
        const packet = buffer.slice(0, end);
        buffer = buffer.slice(end + 1);
        try { receive(JSON.parse(packet)); }
        catch (error) { fatalError = error; failPending(error); }
      }
    });
    report.browser = await call('Browser.getVersion', {}, null);
    const { targetId } = await call('Target.createTarget', { url: 'about:blank' }, null);
    session = (await call('Target.attachToTarget', { targetId, flatten: true }, null)).sessionId;
    await call('Page.enable');
    await call('Runtime.enable');
    await call('Network.enable');
    await call('Network.setCacheDisabled', { cacheDisabled: true });
    await call('Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }] });
    await call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    await verifyWorkbench();
    await verifyEditorial();
    await verifyStudio();
    await settle();
    await Promise.all([...intercepted]);
    healthy();
    for (const file of Object.values(FILES)) {
      check(sha256(fs.readFileSync(path.join(ROOT, 'assets', file))) === report.sources[file], `${file}: source did not change during verification`);
    }
    report.checks.push('No uncaught exceptions, console.error or external page requests');
    report.status = 'passed';
  } catch (error) {
    noteFailure(error);
  } finally {
    shuttingDown = true;
    if (browser && !childExited) {
      try { await deadline(call('Browser.close', {}, null), 3000, 'Chrome close deadline exceeded'); }
      catch { if (!childExited) browser.kill('SIGTERM'); }
      try { await deadline(childDone, 3000, 'Chrome exit deadline exceeded'); }
      catch {
        if (!childExited) browser.kill('SIGKILL');
        try { await deadline(childDone, 3000, 'Chrome did not exit after SIGKILL'); }
        catch (error) { noteFailure(error); }
      }
    }
    failPending(new Error('Verification finished'));
    if (server?.listening) {
      try {
        const closed = new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
        server.closeAllConnections();
        await deadline(closed, 3000, 'Local HTTP server did not close');
      } catch (error) { noteFailure(error); }
    }
    if (profile) {
      // The path is only ever assigned from this run's mkdtemp; never delete user profiles.
      if (!browser || childExited) {
        try { fs.rmSync(profile, { recursive: true, force: true }); }
        catch (error) { noteFailure(new Error(`Could not remove temporary profile ${profile}: ${error.message}`)); }
      } else noteFailure(new Error(`Chrome is still running; temporary profile retained: ${profile}`));
    }
    try { healthy(); } catch (error) { if (!report.error?.includes(error.message)) noteFailure(error); }
    report.capturedAt = new Date().toISOString();
    process.off('SIGINT', onSigint);
    process.off('SIGTERM', onSigterm);
    fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(`${report.status.toUpperCase()}: ${report.checks.length} checks; ${report.captures.length} real screenshots. Browser behavior evidence, not aesthetic approval.`);
    if (report.error) console.error(report.error);
    console.log('Report: ' + path.join(OUT, 'report.json'));
  }
}

main().catch(error => { console.error('Verification/report write failed: ' + error.message); process.exitCode = 1; });
