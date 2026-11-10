#!/usr/bin/env node
/**
 * probe-surface.mjs —— 品类表面与版式实测器
 *
 * probe.mjs 测的是「定价页的档位与价格权重」；本工具测的是用户真正在问的那几件事：
 *   底色是什么、按钮是方是圆、字体是什么族、字多大、行距多松、线有多重、版心多宽。
 *
 * 为什么必须实测：凭印象说「电商多用白底+大图」「美妆爱奶油色」，十次有六次是错的。
 * 品类结论必须落在「某站在 1440px 下的 body 实测值」上，否则就是模型的刻板印象。
 *
 * 用法：
 *   node scripts/probe-surface.mjs https://a.com https://b.com --json out.json
 *   node scripts/probe-surface.mjs <url> --scheme dark
 *
 * ⚠️ 只测「它此刻是什么」。测不出「它适合什么品类」——那是判断，写在 category-prototypes.md。
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME_CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
];

const argv = process.argv.slice(2);
const urls = argv.filter(a => /^https?:\/\//.test(a));
const jsonIdx = argv.indexOf('--json');
const jsonOut = jsonIdx >= 0 ? argv[jsonIdx + 1] : null;
const schemeIdx = argv.indexOf('--scheme');
const forcedScheme = schemeIdx >= 0 ? argv[schemeIdx + 1] : 'light';
const waitIdx = argv.indexOf('--wait');
const waitMs = waitIdx >= 0 ? +argv[waitIdx + 1] : 6500;
const port = 9600 + Math.floor(Math.random() * 200);

if (!urls.length) {
  console.error('用法: node scripts/probe-surface.mjs <url> [url...] [--json out.json] [--scheme light|dark] [--wait ms]');
  process.exit(1);
}

const chrome = CHROME_CANDIDATES.find(p => fs.existsSync(p));
if (!chrome) {
  console.error('找不到 Chrome/Chromium。');
  process.exit(1);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const waits = new Map();
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && waits.has(m.id)) { waits.get(m.id)(m); waits.delete(m.id); }
  };
  const send = (method, params = {}) => new Promise(res => {
    const i = ++id; waits.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  return { send, close: () => ws.close() };
}

const PROBE = `(() => {
  const px = v => parseFloat(v) || 0;
  const cs = e => getComputedStyle(e);
  const lum = c => {
    const m = (c.match(/[\\d.]+/g) || []).map(Number);
    if (m.length < 3) return null;
    const f = x => { x = x / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]);
  };
  const solid = c => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent' && !/, 0\\)$/.test(c);
  const fam = s => (s.split(',')[0] || '').replace(/["']/g, '').trim();
  const mode = arr => {
    const c = {}; arr.forEach(v => c[v] = (c[v] || 0) + 1);
    const e = Object.entries(c).sort((a, b) => b[1] - a[1]);
    return e.length ? { v: e[0][0], n: e[0][1], all: e.slice(0, 5).map(x => x[0] + '×' + x[1]) } : null;
  };
  const vw = innerWidth;

  const bodyBg = cs(document.body).backgroundColor;
  const htmlBg = cs(document.documentElement).backgroundColor;
  const out = {
    url: location.href,
    title: document.title,
    scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    bodyBg: solid(bodyBg) ? bodyBg : 'transparent',
    htmlBg: solid(htmlBg) ? htmlBg : 'transparent',
    bodyLum: (l => l == null ? null : +l.toFixed(3))(lum(solid(bodyBg) ? bodyBg : htmlBg)),
    bgFrom: solid(bodyBg) ? 'body' : 'html',
    docH: document.documentElement.scrollHeight,
    vw,
  };

  // ── 正文基准：取 body 或最像正文的元素 ──
  const bs = cs(document.body);
  out.bodyText = {
    font: fam(bs.fontFamily),
    fullStack: bs.fontFamily.slice(0, 120),
    size: +px(bs.fontSize).toFixed(1),
    lh: bs.lineHeight === 'normal' ? 'normal' : +(px(bs.lineHeight) / px(bs.fontSize)).toFixed(2),
    color: bs.color,
    weight: bs.fontWeight,
  };

  // 第一段真正有正文的 p
  const paras = [...document.querySelectorAll('p, li')].filter(e => {
    const t = (e.textContent || '').trim();
    if (t.length < 40) return false;
    const r = e.getBoundingClientRect();
    return r.width > 160 && r.height > 10;
  }).slice(0, 6);
  if (paras.length) {
    const s = cs(paras[0]);
    out.para = {
      sample: paras[0].textContent.trim().slice(0, 40),
      font: fam(s.fontFamily), size: +px(s.fontSize).toFixed(1),
      lh: s.lineHeight === 'normal' ? 'normal' : +(px(s.lineHeight) / px(s.fontSize)).toFixed(2),
      color: s.color, weight: s.fontWeight,
      w: Math.round(paras[0].getBoundingClientRect().width),
      left: Math.round(paras[0].getBoundingClientRect().left),
    };
  }

  // ── 主标题 ──
  const h1 = document.querySelector('h1') || [...document.querySelectorAll('h2')][0];
  if (h1) {
    const s = cs(h1), r = h1.getBoundingClientRect();
    out.h1 = {
      t: (h1.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 60),
      font: fam(s.fontFamily), size: +px(s.fontSize).toFixed(1), weight: s.fontWeight,
      lh: s.lineHeight === 'normal' ? 'normal' : +(px(s.lineHeight) / px(s.fontSize)).toFixed(2),
      ls: s.letterSpacing, color: s.color,
      transform: s.textTransform,
      w: Math.round(r.width), lines: Math.max(1, Math.round(r.height / Math.max(1, px(s.lineHeight)))),
    };
  }

  // ── 字号阶梯（首屏可见文本）──
  const sizes = [];
  document.querySelectorAll('h1,h2,h3,h4,p,span,a,button,div').forEach(e => {
    if (e.children.length) return;
    const t = (e.textContent || '').trim();
    if (t.length < 2 || t.length > 90) return;
    const r = e.getBoundingClientRect();
    if (r.top > 1400 || r.bottom < 0 || r.width < 12) return;
    const s = px(cs(e).fontSize);
    if (s > 6) sizes.push(Math.round(s * 2) / 2);
  });
  out.sizeScale = mode(sizes);

  // ── 版心：首屏文本块最大宽度与左右留白 ──
  let maxW = 0, minLeft = 1e9, maxRight = 0;
  document.querySelectorAll('h1,h2,p,ul,form').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.top > 1200 || r.width < 200 || r.width > vw - 8 || r.left < -4) return;
    if (r.width > maxW) maxW = Math.round(r.width);
    if (r.left < minLeft) minLeft = Math.round(r.left);
    if (r.right > maxRight && r.right <= vw + 2) maxRight = Math.round(r.right);
  });
  const okGut = minLeft !== 1e9 && minLeft >= 0 && minLeft < vw / 3;
  out.layout = {
    textColMax: maxW || null,
    leftGutter: okGut ? minLeft : null,
    rightGutter: okGut && maxRight ? Math.round(vw - maxRight) : null,
    centered: okGut && maxRight ? Math.abs(minLeft - (vw - maxRight)) < 12 : null,
    overflow: maxRight > vw + 2,
  };

  // 容器的 max-width：找主标题到 body 之间第一个设了 max-width 的祖先
  if (h1) {
    let n = h1, guard = 0, found = null;
    while (n && n !== document.body && guard++ < 12) {
      const s = cs(n);
      if (s.maxWidth && s.maxWidth !== 'none') { found = { maxWidth: s.maxWidth, sel: (n.className || '').toString().slice(0, 40) }; break; }
      n = n.parentElement;
    }
    out.container = found;
  }

  // ── 按钮 / CTA ──
  const ctas = [];
  document.querySelectorAll('a,button,[role="button"]').forEach(e => {
    const t = (e.textContent || '').replace(/\\s+/g, ' ').trim();
    if (t.length < 2 || t.length > 30) return;
    const r = e.getBoundingClientRect();
    if (r.width < 56 || r.height < 26 || r.top > 1200) return;
    const s = cs(e);
    const bg = s.backgroundColor;
    const hasBorder = px(s.borderTopWidth) > 0 && solid(s.borderTopColor);
    if (!solid(bg) && !hasBorder) return;
    ctas.push({
      t, bg: solid(bg) ? bg : 'transparent',
      fg: s.color,
      border: hasBorder ? px(s.borderTopWidth) + 'px ' + s.borderTopColor : 'none',
      radius: px(s.borderTopLeftRadius) > 400 ? 'full' : s.borderTopLeftRadius,
      h: Math.round(r.height), w: Math.round(r.width),
      size: +px(s.fontSize).toFixed(1), weight: s.fontWeight,
      pad: [s.paddingTop, s.paddingRight].join(' '),
      shadow: s.boxShadow === 'none' ? 'none' : 'yes',
      transform: s.textTransform,
      ls: s.letterSpacing,
      top: Math.round(r.top + scrollY),
    });
  });
  const seen = new Set();
  out.ctas = ctas.filter(c => { const k = c.t + '|' + c.h; if (seen.has(k)) return false; seen.add(k); return true; }).slice(0, 8);

  // ── 曲面性格：圆角 / 线宽 / 阴影 的出现次数 ──
  const radii = [], borders = [], shadows = [];
  const nodes = [...document.querySelectorAll('div,section,article,header,nav,a,button,img,ul')].slice(0, 1400);
  nodes.forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 20 || r.top > 2600) return;
    const s = cs(e);
    const rv = s.borderTopLeftRadius;
    if (rv && rv !== '0px') {
      const v = px(rv);
      radii.push(v > 400 ? 'full' : (v + 'px'));
    }
    if (px(s.borderTopWidth) > 0 && solid(s.borderTopColor)) borders.push(s.borderTopWidth);
    if (s.boxShadow !== 'none') shadows.push(s.boxShadow.slice(0, 30));
  });
  out.surface = {
    radii: mode(radii),
    radiusShare: radii.length ? +(radii.length / nodes.length).toFixed(2) : 0,
    borders: mode(borders),
    borderShare: borders.length ? +(borders.length / nodes.length).toFixed(2) : 0,
    shadows: mode(shadows),
    shadowShare: shadows.length ? +(shadows.length / nodes.length).toFixed(2) : 0,
  };

  // ── 导航 ──
  const nav = document.querySelector('header, nav, [role="banner"]');
  if (nav) {
    const s = cs(nav), r = nav.getBoundingClientRect();
    out.nav = {
      h: Math.round(r.height),
      bg: solid(s.backgroundColor) ? s.backgroundColor : 'transparent',
      borderBottom: px(s.borderBottomWidth) > 0 ? s.borderBottomWidth + 'px ' + s.borderBottomColor : 'none',
      radius: px(s.borderTopLeftRadius) > 400 ? 'full' : s.borderTopLeftRadius,
      sticky: /fixed|sticky/.test(s.position),
    };
  }

  // ── 首屏文本量（判断它是"字打头"还是"图打头"）──
  const fold = [...document.querySelectorAll('body *')].filter(e => {
    const r = e.getBoundingClientRect();
    return r.top >= 0 && r.bottom <= 900 && r.width > 40 && !e.children.length;
  });
  out.fold = {
    textLen: fold.reduce((a, e) => a + (e.textContent || '').trim().length, 0),
    imgs: [...document.querySelectorAll('img,video,svg picture')].filter(e => {
      const r = e.getBoundingClientRect();
      return r.top < 900 && r.width > 160 && r.height > 90;
    }).length,
    allTextLen: (document.body.innerText || '').length,
  };

  return out;
})()`;

const pad = (s, n) => String(s).padEnd(n);
const rgbs = c => { const m = (c || '').match(/(\d+)[,\s]+(\d+)[,\s]+(\d+)/); return m ? [+m[1], +m[2], +m[3]] : null; };
const hex = c => { const v = rgbs(c); return v ? '#' + v.map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase() : (c || '—'); };

function report(name, m) {
  if (m.error) return `\n${name}  ✗ ${m.error}`;
  const L = [];
  L.push('');
  L.push('━'.repeat(78));
  L.push(`${name}  ${m.url || ''}`);
  L.push(`  底色 ${m.bodyBg === 'transparent' ? '透明→' + hex(m.htmlBg) : hex(m.bodyBg)}（${m.status ? 'http ' + m.status + ' ' : ''}取色自 ${m.bgFrom}）  亮度 ${m.bodyLum}  scheme=${m.scheme}  页高 ${m.docH}px`);
  if (m.h1) L.push(`  H1  ${m.h1.size}px/${m.h1.weight} lh${m.h1.lh} ls${m.h1.ls} ${m.h1.font}  「${m.h1.t.slice(0, 34)}」`);
  L.push(`  正文 ${m.bodyText.size}px lh${m.bodyText.lh} ${m.bodyText.font}` + (m.para ? `  |  段落 ${m.para.size}px lh${m.para.lh} 宽${m.para.w}` : ''));
  if (m.layout) L.push(`  版心 文本列最大 ${m.layout.textColMax}px  左留白 ${m.layout.leftGutter}  右留白 ${m.layout.rightGutter}  居中=${m.layout.centered}${m.layout.overflow ? ' ⚠有横向溢出' : ''}  容器 ${m.container ? m.container.maxWidth : '无 max-width'}`);
  (m.ctas || []).slice(0, 4).forEach(c => L.push(`  按钮  圆角${pad(c.radius, 8)} 高${pad(c.h, 4)} ${pad(c.size + 'px', 6)} 字重${pad(c.weight, 4)} 底${pad(hex(c.bg), 9)} ${c.border === 'none' ? '无边框' : '边框' + c.border} 「${c.t.slice(0, 16)}」`));
  const s = m.surface || {};
  L.push(`  曲面  圆角 ${s.radii ? s.radii.all.join(' ') : '全 0'} (占比 ${s.radiusShare})  线宽 ${s.borders ? s.borders.all.join(' ') : '无'}  阴影占比 ${s.shadowShare}`);
  if (m.nav) L.push(`  导航  高 ${m.nav.h}px  bg=${hex(m.nav.bg)}  ${m.nav.borderBottom === 'none' ? '无下边框' : m.nav.borderBottom}  ${m.nav.sticky ? 'sticky' : 'static'}`);
  L.push(`  首屏  文本 ${m.fold.textLen} 字  大图 ${m.fold.imgs} 张  全文 ${m.fold.allTextLen} 字`);
  return L.join('\n');
}

const main = async () => {
  const udd = path.join(os.tmpdir(), 'probe-surface-' + Date.now());
  const proc = spawn(chrome, [
    '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
    '--remote-debugging-port=' + port, '--user-data-dir=' + udd,
    '--window-size=1440,1000', 'about:blank',
  ], { stdio: 'ignore' });

  let up = false;
  for (let i = 0; i < 50; i++) {
    await sleep(300);
    try { const r = await fetch(`http://127.0.0.1:${port}/json/version`); if (r.ok) { up = true; break; } } catch {}
  }
  if (!up) { console.error('Chrome 未就绪'); proc.kill(); process.exit(1); }

  const results = {};
  for (const url of urls) {
    const name = new URL(url).hostname.replace(/^www\./, '');
    process.stdout.write(`探测 ${name} … `);
    try {
      const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })).json();
      const c = await connect(tab.webSocketDebuggerUrl);
      await c.send('Page.enable');
      await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: forcedScheme }] });
      await sleep(waitMs);
      const r = await c.send('Runtime.evaluate', { expression: PROBE, returnByValue: true });
      results[name] = r.result?.result?.value || { error: r.result?.exceptionDetails?.text || 'evaluate failed' };
      console.log('ok');
      await c.send('Page.close').catch(() => {});
      c.close();
    } catch (e) {
      results[name] = { error: String(e.message || e) };
      console.log('FAIL');
    }
    await sleep(400);
  }

  for (const [name, m] of Object.entries(results)) console.log(report(name, m));
  if (jsonOut) { fs.writeFileSync(jsonOut, JSON.stringify(results, null, 2)); console.log(`\n已写入 ${jsonOut}`); }

  proc.kill();
  await sleep(300);
  process.exit(0);
};

main();
