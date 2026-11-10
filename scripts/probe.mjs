#!/usr/bin/env node
/**
 * probe.mjs —— 参考页实测器（参考准入的取证工具）
 *
 * 为什么需要它：看截图只能得到"印象"，而印象会被语言模型自动补全成
 * 看起来很专业的假数字。"这个价格 44px""列间距是行距 2.4 倍"这类句子，
 * 只要没量过，基本都是编的。本工具把参考从 R1（截图）抬到 R2（DOM 实测）。
 *
 * 用法：
 *   node scripts/probe.mjs https://linear.app/pricing https://ramp.com/pricing
 *   node scripts/probe.mjs <url> --json out.json
 *   node scripts/probe.mjs <url> --scheme dark      # 强制深色
 *
 * 输出：每个页面一节，含
 *   - scheme / bodyBg / 亮度（判断明暗系统）
 *   - sku: 价格元素（文本、字号、字重、颜色、左偏移、等宽数字）
 *   - tiers: 档位容器的真实盒模型（border / radius / bg / shadow / padding / 列间距）
 *   - hero: 页面最大字号（判断视觉主角是价格还是标题）
 *   - workload: 业务压力痕迹（档数、年付切换、FAQ 条数、最大表行数、页高）
 *
 * ⚠️ 本工具只测"它此刻是什么"。测不出"它好不好"——那是判断，不是测量。
 *    准入判定见 references/reference-intake.md。
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
const port = 9400 + Math.floor(Math.random() * 200);

if (!urls.length) {
  console.error('用法: node scripts/probe.mjs <url> [url...] [--json out.json] [--scheme light|dark]');
  process.exit(1);
}

const chrome = CHROME_CANDIDATES.find(p => fs.existsSync(p));
if (!chrome) {
  console.error('找不到 Chrome/Chromium。装一个，或改用人工测量。');
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
  const depth = e => { let d = 0, n = e; while (n = n.parentElement) d++; return d; };

  const bodyBg = cs(document.body).backgroundColor;
  const out = {
    url: location.href,
    title: document.title,
    scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    bodyBg,
    bodyLum: (l => l == null ? null : +l.toFixed(3))(lum(bodyBg)),
    docH: document.documentElement.scrollHeight,
  };

  // ── 价格元素 ──
  const re = /(US\\$|\\$|€|£|¥)\\s?\\d[\\d,]*/;
  const raw = [];
  document.querySelectorAll('body *').forEach(e => {
    const t = (e.textContent || '').replace(/\\s+/g, ' ').trim();
    if (t.length > 28 || !re.test(t)) return;
    const r = e.getBoundingClientRect();
    if (r.width < 22 || r.height < 12 || r.width > 460) return;
    const s = cs(e);
    raw.push({
      t, size: +px(s.fontSize).toFixed(1), weight: s.fontWeight, color: s.color,
      font: s.fontFamily.split(',')[0].replace(/["']/g, ''),
      tabular: /tabular-nums|mono/i.test(s.fontVariantNumeric + s.fontFamily),
      left: Math.round(r.left), top: Math.round(r.top + scrollY),
      w: Math.round(r.width), h: Math.round(r.height), d: depth(e),
    });
  });
  const uniq = new Map();
  raw.forEach(c => {
    const k = c.left + '|' + c.top + '|' + c.t;
    if (!uniq.has(k) || uniq.get(k).d < c.d) uniq.set(k, c);
  });
  out.prices = [...uniq.values()].sort((a, b) => a.top - b.top || a.left - b.left).slice(0, 18);

  // ── 档位容器：价格元素的最近共同祖先 → 直接子元素盒模型 ──
  if (out.prices.length >= 2) {
    const nodes = [...document.querySelectorAll('body *')].filter(e => {
      const t = (e.textContent || '').replace(/\\s+/g, ' ').trim();
      return t.length <= 28 && re.test(t) && px(cs(e).fontSize) >= 13;
    });
    let anc = nodes[0];
    while (anc && !nodes.every(n => anc.contains(n))) anc = anc.parentElement;
    if (anc) {
      const sa = cs(anc);
      out.tiers = {
        display: sa.display,
        gap: sa.gap,
        gridCols: sa.gridTemplateColumns.slice(0, 90),
        children: [...anc.children].map(ch => {
          const s = cs(ch), r = ch.getBoundingClientRect();
          const bg = s.backgroundColor;
          return {
            cls: (ch.className || '').toString().slice(0, 40),
            border: px(s.borderLeftWidth), borderColor: s.borderLeftColor,
            radius: s.borderRadius,
            bg: (!bg || bg === 'rgba(0, 0, 0, 0)' || /, 0\\)$/.test(bg)) ? 'transparent' : bg,
            shadow: s.boxShadow === 'none' ? 'none' : 'yes',
            pad: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft].join(' '),
            left: Math.round(r.left), top: Math.round(r.top + scrollY),
            w: Math.round(r.width), h: Math.round(r.height),
          };
        }).slice(0, 6),
      };
      const ch = out.tiers.children;
      for (let i = 0; i < ch.length - 1; i++) ch[i].gapToNext = ch[i + 1].left - (ch[i].left + ch[i].w);

      // 区分「列分隔线」与「推荐档强调」——这一步极易误判：
      //   Linear 是「首列无左边框、其余各有 1px」= 分隔线，不是强调
      //   Ramp  是「三档各 1px，只有中间档 3px」= 强调
      // 判据：若除首列外全部相同，且首列不同 → 分隔线；否则偏离多数派的那个才算强调。
      const rest = ch.slice(1);
      const allSame = (arr, k) => arr.every(x => x[k] === arr[0][k]);
      const dividerLike = rest.length >= 2 && allSame(rest, 'border') && rest[0].border > 0;
      if (dividerLike) {
        out.tiers.boundary = {
          kind: 'column-divider',
          detail: '首列无左边框，其余各 ' + rest[0].border + 'px ' + rest[0].borderColor + '；容器高 ' + (ch[0] ? ch[0].h : '?') + 'px（= 整列通高）',
        };
      }
      const mode = k => {
        const vals = ch.map(c => c[k]);
        const counts = {};
        vals.forEach(v => counts[v] = (counts[v] || 0) + 1);
        return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
      };
      const mb = mode('border'), mbg = mode('bg'), mh = mode('h');
      const emph = ch.map((c, i) => {
        const d = [];
        if (c.border !== +mb) d.push('border ' + c.border + 'px（众数 ' + mb + 'px）');
        if (c.bg !== mbg) d.push('bg ' + c.bg);
        if (Math.abs(c.h - mh) > 6) d.push('height ' + c.h + '（众数 ' + mh + '）');
        return { index: i, diffs: d };
      }).filter(x => x.diffs.length);
      out.tiers.recommended = emph;
      if (dividerLike && !emph.length) out.tiers.boundary.kind = 'column-divider-only';
    }
  }

  // ── 视觉主角 ──
  const heads = [];
  document.querySelectorAll('h1,h2,h3,p,div,span').forEach(e => {
    if (e.children.length) return;
    const t = (e.textContent || '').trim();
    if (t.length < 3 || t.length > 70 || re.test(t)) return;
    const r = e.getBoundingClientRect();
    if (r.width < 30 || r.height < 10) return;
    const s = px(cs(e).fontSize);
    if (s >= 26) heads.push({ t: t.slice(0, 44), size: +s.toFixed(0), weight: cs(e).fontWeight, top: Math.round(r.top + scrollY) });
  });
  heads.sort((a, b) => b.size - a.size || a.top - b.top);
  out.hero = heads.slice(0, 8);

  // ── 业务压力痕迹（真实性的可测代理，不是审美判断）──
  const allText = document.body.innerText || '';
  let maxTableRows = 0;
  document.querySelectorAll('table, [role="table"]').forEach(t => {
    const n = t.querySelectorAll('tr, [role="row"]').length;
    if (n > maxTableRows) maxTableRows = n;
  });
  out.workload = {
    priceGroups: new Set(out.prices.map(p => p.left)).size,
    hasAnnualToggle: /billed annually|annual billing|per year|yearly|save \\d+%/i.test(allText),
    hasEnterpriseCustom: /custom|contact (us|sales)|talk to sales/i.test(allText),
    faqToggles: document.querySelectorAll('details, summary, [aria-expanded]').length,
    maxTableRows,
    textLen: allText.length,
    docH: document.documentElement.scrollHeight,
  };
  return out;
})()`;

const pad = (s, n) => String(s).padEnd(n);

function report(name, m) {
  const L = [];
  L.push('');
  L.push('━'.repeat(78));
  L.push(`${name}  ${m.url || ''}`);
  L.push(`  标题: ${m.title || '—'}`);
  L.push(`  明暗: scheme=${m.scheme}  bodyBg=${m.bodyBg}  亮度=${m.bodyLum}  页高=${m.docH}px`);
  const pr = m.prices || [];
  L.push(`  价格元素 (${pr.length}):`);
  pr.slice(0, 8).forEach(p => {
    L.push(`    ${pad(p.size + 'px', 7)} w${pad(p.weight, 4)} L${pad(p.left, 5)} T${pad(p.top, 6)} ${pad(p.tabular ? '等宽' : '比例', 4)} ${p.color.padEnd(20)} ${JSON.stringify(p.t)}`);
  });
  if (m.tiers) {
    const t = m.tiers;
    const neg = (t.children || []).some(c => (c.gapToNext != null && c.gapToNext < 0));
    if (neg) {
      L.push(`  档位容器: ⚠ 共同祖先取到了外层（存在重叠子块），盒模型不可信`);
      L.push(`    价格左偏移序列（可推断列位置）: ${(pr.map(p => p.left).filter((v, i, a) => a.indexOf(v) === i)).join(', ')}`);
    } else {
      L.push(`  档位容器: display=${t.display}  gap=${t.gap}  cols=${(t.gridCols || '').slice(0, 60)}`);
      (t.children || []).forEach((c, i) => {
        L.push(`    [${i}] b${pad(c.border, 2)}px r${pad(c.radius, 6)} ${pad(c.shadow, 4)} bg=${pad(c.bg, 18)} pad[${c.pad}] L${pad(c.left, 5)} W${c.w} H${c.h}` + (c.gapToNext != null ? `  列间距=${c.gapToNext}` : ''));
      });
      if (t.boundary) L.push(`  边界方式: ${t.boundary.kind} — ${t.boundary.detail}`);
      if (t.recommended && t.recommended.length) {
        L.push(`  推荐档强调: ` + t.recommended.map(r => `#${r.index}(${r.diffs.join(', ')})`).join('  '));
      } else {
        L.push('  推荐档强调: 盒模型层面未见差异（可能靠图标/按钮/文字标签，需人工确认）');
      }
    }
  } else {
    L.push('  档位容器: 未检出（价格不在同一容器内，或页面结构非并排档位）');
  }
  const h = m.hero || [];
  L.push(`  视觉主角: ` + (h.length ? h.slice(0, 4).map(x => `${x.size}px ${JSON.stringify(x.t).slice(0, 26)}`).join(' | ') : '除价格外无 ≥26px 文本'));
  if (pr.length) {
    const pMax = Math.max(...pr.map(p => p.size));
    const hMax = h.length ? h[0].size : pMax;
    L.push(`  价格最大 ${pMax}px / 非价格最大 ${h.length ? hMax + 'px' : '（无）'} = ${h.length ? (pMax / hMax).toFixed(2) + '×' : '价格即最大元素'}`);
  }
  const w = m.workload || {};
  L.push(`  业务压力痕迹: 档位组数=${w.priceGroups} 年付切换=${w.hasAnnualToggle ? '有' : '无'} 企业定制=${w.hasEnterpriseCustom ? '有' : '无'} 折叠项=${w.faqToggles} 最大表行=${w.maxTableRows} 正文=${w.textLen}字`);
  return L.join('\n');
}

const main = async () => {
  const udd = path.join(os.tmpdir(), 'probe-' + Date.now());
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
    const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })).json();
    const c = await connect(tab.webSocketDebuggerUrl);
    await c.send('Page.enable');
    await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: forcedScheme }] });
    await sleep(6200);
    const r = await c.send('Runtime.evaluate', { expression: PROBE, returnByValue: true });
    results[name] = r.result?.result?.value || { error: r.result?.exceptionDetails?.text };
    console.log('ok');
    await c.send('Page.close').catch(() => {});
    c.close();
  }

  for (const [name, m] of Object.entries(results)) console.log(report(name, m));
  if (jsonOut) { fs.writeFileSync(jsonOut, JSON.stringify(results, null, 2)); console.log(`\n已写入 ${jsonOut}`); }

  proc.kill();
  await sleep(300);
  process.exit(0);
};

main();
