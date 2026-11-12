#!/usr/bin/env python3
"""probe-energy.py —— 第十一问「这一屏值不值得看」实测器

只依赖本机 Chrome 与 python3 标准库（无 npm、无 Node）。
原理：把测量脚本注入页面副本，用 headless Chrome 的 --dump-dom 取回 DOM 实测值。

用法：
    python3 scripts/probe-energy.py <page.html> [page2.html ...] [--viewport 838,1060] [--json out.json]

输出四项：① 强调落点 ② 尺度跨度 ③ 材质类数 ④（判断项，不代答）
第 ④ 项「为什么是它」是判断，脚本量不出来，不许由脚本冒充。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import html as htmllib

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

PROBE_JS = r"""
(function () {
  var VH = innerHeight, VW = innerWidth;
  function px(v) { return parseFloat(v) || 0; }
  function rgb(c) {
    var m = (String(c).match(/[\d.]+/g) || []).map(Number);
    if (m.length < 3) return null;
    return { r: m[0], g: m[1], b: m[2], a: m.length > 3 ? m[3] : 1 };
  }
  function hex(c) { var p = rgb(c); return p ? "#" + [p.r, p.g, p.b].map(function (x) { return ("0" + x.toString(16)).slice(-2); }).join("").toUpperCase() : null; }
  function sat(c) {
    var p = rgb(c); if (!p || p.a < 0.35) return 0;
    var mx = Math.max(p.r, p.g, p.b) / 255, mn = Math.min(p.r, p.g, p.b) / 255;
    if (mx - mn < 0.008) return 0;
    var l = (mx + mn) / 2, d = mx - mn;
    return d / (l > 0.5 ? (2 - mx - mn) : (mx + mn));
  }
  function chroma(c) {
    var p = rgb(c); if (!p || p.a < 0.35) return 0;
    return (Math.max(p.r, p.g, p.b) - Math.min(p.r, p.g, p.b)) / 255;
  }
  // 强调色门槛：HSL 饱和度 ≥0.40 且绝对彩度 ≥0.18。
  // 少了这道门槛，深色页的蓝灰正文（#7E8CA6，S 0.28 / chroma 0.22）会被当成主强调族，
  // 落点数会虚高到几十处，把「灰稿」误判成「强调充足」。
  function isAccent(c) { return sat(c) >= 0.40 && chroma(c) >= 0.18; }
  function lum(c) {
    var p = rgb(c); if (!p) return null;
    var f = function (x) { x = x / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(p.r) + 0.7152 * f(p.g) + 0.0722 * f(p.b);
  }
  function hue(c) {
    var p = rgb(c); if (!p) return null;
    var r = p.r / 255, g = p.g / 255, b = p.b / 255;
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if (d < 0.008) return null;
    var h = mx === r ? ((g - b) / d + 6) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return h * 60;
  }
  function ownText(e) {
    return Array.prototype.filter.call(e.childNodes, function (n) { return n.nodeType === 3; })
      .map(function (n) { return n.textContent; }).join("").replace(/\s+/g, " ").trim();
  }
  var bodyBg = getComputedStyle(document.body).backgroundColor;
  var bodyL = lum(bodyBg) || 0;
  var seen = [];
  document.querySelectorAll("body *").forEach(function (e) {
    var r = e.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= VH || r.width < 6 || r.height < 6) return;
    var s = getComputedStyle(e);
    if (s.visibility === "hidden" || s.display === "none" || parseFloat(s.opacity) < 0.15) return;
    if (e.closest("[aria-hidden=true]")) return;
    seen.push({ e: e, s: s, t: ownText(e), tag: e.tagName });
  });

  // ① 强调落点
  var uses = [];
  seen.forEach(function (o) {
    var s = o.s;
    if (o.t && isAccent(s.color)) uses.push({ role: "文字", c: s.color, o: o });
    if (isAccent(s.backgroundColor)) uses.push({ role: "色块", c: s.backgroundColor, o: o });
    ["Top", "Right", "Bottom", "Left"].forEach(function (d) {
      if (px(s["border" + d + "Width"]) > 0 && isAccent(s["border" + d + "Color"]))
        uses.push({ role: "线", c: s["border" + d + "Color"], o: o });
    });
    if ((o.tag === "SVG" || o.tag === "PATH") && s.fill && s.fill !== "none" && isAccent(s.fill))
      uses.push({ role: "图形", c: s.fill, o: o });
  });
  function blockOf(e) {
    var n = e;
    while (n.parentElement && n.parentElement !== document.body) {
      var r = n.getBoundingClientRect();
      if (r.height >= 120 && r.width >= VW * 0.6) return n;
      n = n.parentElement;
    }
    return n;
  }
  var groups = {};
  uses.forEach(function (u) {
    var h = hue(u.c); if (h == null) return;
    var k = (Math.round(h / 30) * 30) % 360;
    (groups[k] = groups[k] || []).push(u);
  });
  // 主强调族 = 首屏落点最多的一族；同时报告最高饱和值落在哪一族
  var accentHue = null, bestHits = -1, best = -1, topSatHue = null;
  Object.keys(groups).forEach(function (k) {
    if (groups[k].length > bestHits) { bestHits = groups[k].length; accentHue = k; }
    groups[k].forEach(function (u) { var s = sat(u.c); if (s > best) { best = s; topSatHue = k; } });
  });
  var acc = groups[accentHue] || [];
  var blockSet = new Set(acc.map(function (u) { return blockOf(u.o.e); }));
  var roles = {};
  acc.forEach(function (u) { roles[u.role] = (roles[u.role] || 0) + 1; });
  var hexes = Array.from(new Set(acc.map(function (u) { return hex(u.c); })));
  var others = Object.keys(groups).filter(function (k) { return k !== accentHue; })
    .map(function (k) { return k + "°×" + groups[k].length; }).slice(0, 4);
  var tintHues = {};
  seen.forEach(function (o) {
    ["color", "backgroundColor"].forEach(function (p) {
      var c = o.s[p]; if (sat(c) > 0.10 && !isAccent(c)) { var h = hue(c); if (h != null) { var k = (Math.round(h / 30) * 30) % 360; tintHues[k] = (tintHues[k] || 0) + 1; } }
    });
  });
  var tints = Object.keys(tintHues).sort(function (a, b) { return tintHues[b] - tintHues[a]; })
    .slice(0, 2).map(function (k) { return k + "°×" + tintHues[k]; });

  // ② 尺度跨度
  var textEls = seen.filter(function (o) { return o.t.length > 0; });
  var sizes = textEls.map(function (o) { return px(o.s.fontSize); });
  var maxFs = sizes.length ? Math.max.apply(null, sizes) : 0;
  var sentSizes = textEls.filter(function (o) { return o.t.length >= 8; }).map(function (o) { return px(o.s.fontSize); });
  var bodyMin = sentSizes.length ? Math.min.apply(null, sentSizes) : null;
  var allMin = sizes.length ? Math.min.apply(null, sizes) : null;
  var biggest = textEls.slice().sort(function (a, b) { return px(b.s.fontSize) - px(a.s.fontSize); })[0];

  // ③ 材质
  var mat = {
    "投影": seen.filter(function (o) { return o.s.boxShadow && o.s.boxShadow !== "none"; }).length,
    "描边": seen.filter(function (o) {
      return ["Top", "Right", "Bottom", "Left"].some(function (d) {
        var p = rgb(o.s["border" + d + "Color"]);
        return px(o.s["border" + d + "Width"]) > 0 && p && p.a > 0.2;
      });
    }).length,
    "色块底": seen.filter(function (o) {
      var p = rgb(o.s.backgroundColor); if (!p || p.a < 0.2) return false;
      var l = lum(o.s.backgroundColor); return l != null && Math.abs(l - bodyL) > 0.012;
    }).length,
    "渐变": seen.filter(function (o) { return /gradient/.test(o.s.backgroundImage); }).length,
    "图像": document.querySelectorAll("img,svg,canvas,video").length
  };
  var kinds = Object.keys(mat).filter(function (k) { return mat[k] > 0; }).length;

  // ③b 体积载体：单色 path 图标与平涂矢量不算体积。明暗连续变化只能来自渐变/滤镜/ raster。
  var screenArea = VW * VH;
  function carriesVolume(e) {
    var t = e.tagName.toLowerCase(), r = e.getBoundingClientRect();
    if (t === "svg") return !!e.querySelector("linearGradient,radialGradient,filter");
    if (t === "img" || t === "canvas" || t === "video") return r.width * r.height >= screenArea * 0.06;
    return false;
  }
  var volCarriers = Array.prototype.filter.call(document.querySelectorAll("img,svg,canvas,video"), carriesVolume);
  mat["体积图"] = volCarriers.length;
  var volume = (mat["投影"] > 0 ? 1 : 0) + (mat["渐变"] > 0 ? 1 : 0) + (mat["体积图"] > 0 ? 1 : 0);

  // ④ 首屏空洞：8px 网格占用，找每个顶层区块里最长的空横带
  var CELL = 8, GW = Math.ceil(VW / CELL), GH = Math.ceil(VH / CELL);
  var grid = new Uint8Array(GW * GH);
  seen.forEach(function (o) {
    var s = o.s, e = o.e, r = e.getBoundingClientRect(), t = e.tagName.toLowerCase();
    var bg = rgb(s.backgroundColor);
    var hasInk = o.t.length > 0 || t === "svg" || t === "img" || t === "canvas" ||
      /gradient/.test(s.backgroundImage) ||
      (bg && bg.a > 0.2 && r.width * r.height <= screenArea * 0.2) ||
      ["Top", "Right", "Bottom", "Left"].some(function (d) { return px(s["border" + d + "Width"]) > 0; });
    if (!hasInk) return;
    var x0 = Math.max(0, Math.floor(r.left / CELL)), x1 = Math.min(GW - 1, Math.floor(r.right / CELL));
    var y0 = Math.max(0, Math.floor(r.top / CELL)), y1 = Math.min(GH - 1, Math.floor(r.bottom / CELL));
    for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) grid[y * GW + x] = 1;
  });
  // 区域 = 首屏里的整块 + 它内部任何深度的栏；只留最内层，两栏的空洞才量得到
  var cand = [];
  document.querySelectorAll("body *").forEach(function (e) {
    var r = e.getBoundingClientRect();
    if (r.height < 240 || r.top >= VH || r.bottom <= 0) return;
    if (r.width < VW * 0.18 || r.width > VW * 0.8) return;
    if (r.left >= VW || r.right <= 0) return;
    cand.push(e);
  });
  var roots = cand.filter(function (e) {
    return !cand.some(function (o) { return o !== e && e.contains(o); });
  });
  Array.prototype.forEach.call(document.body.children, function (e) {
    var r = e.getBoundingClientRect();
    if (r.height >= 240 && r.width >= VW * 0.8 && r.top < VH && r.bottom > 0) roots.push(e);
  });
  var holes = [];
  roots.forEach(function (e) {
    var r = e.getBoundingClientRect();
    var x0 = Math.max(0, Math.floor(r.left / CELL)), x1 = Math.min(GW - 1, Math.floor(r.right / CELL));
    var y0 = Math.max(0, Math.floor(r.top / CELL)), y1 = Math.min(GH - 1, Math.floor(r.bottom / CELL));
    if (x1 <= x0 || y1 <= y0) return;
    var run = 0, worst = 0, at = 0, filled = 0, total = 0;
    for (var y = y0; y <= y1; y++) {
      var any = 0;
      for (var x = x0; x <= x1; x++) { total++; if (grid[y * GW + x]) { any = 1; filled++; } }
      if (any) { run = 0; } else { run++; if (run > worst) { worst = run; at = y * CELL; } }
    }
    if (!total) return;
    holes.push({ tag: e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") + (e.className && typeof e.className === "string" ? "." + e.className.trim().split(/\s+/)[0] : ""),
      h: Math.round(r.height), w: Math.round(r.width), fill: +(filled / total).toFixed(2), band: worst * CELL, bandY: at });
  });
  holes.sort(function (a, b) { return b.band - a.band; });

  var fsSet = Array.from(new Set(sizes)).sort(function (a, b) { return b - a; });

  // ⑥ 首屏实际主底色：按网格取每个点最上层的实心背景，按面积统计。
  // 量 body 的声明值量不出用户看到的东西——body 写浅色、首屏整块铺深色渐变，
  // 旧判据据 bodyBg 判过，用户判「颜色太深」。这里量渲染结果。
  var GCELL = 24, gw = Math.ceil(VW / GCELL), gh = Math.ceil(VH / GCELL);
  var tally = {}, darkCells = 0, lightCells = 0, gradCells = 0, gradDarkCells = 0, totalCells = 0;
  // 渐变取不到渲染像素，退而取其色标的平均亮度——这是近似，输出里标明。
  function gradLum(bgImage) {
    var stops = String(bgImage).match(/rgba?\([^)]+\)/g);
    if (!stops || !stops.length) return null;
    var sum = 0, n = 0;
    stops.forEach(function (c) { var v = lum(c); if (v != null) { sum += v; n++; } });
    return n ? sum / n : null;
  }
  for (var gy = 0; gy < gh; gy++) {
    for (var gx = 0; gx < gw; gx++) {
      var cx = Math.min(VW - 1, gx * GCELL + GCELL / 2), cy = Math.min(VH - 1, gy * GCELL + GCELL / 2);
      var stack = document.elementsFromPoint(cx, cy), paint = null, gLum = null;
      for (var i = 0; i < stack.length; i++) {
        var st = getComputedStyle(stack[i]);
        if (st.visibility === "hidden" || parseFloat(st.opacity) < 0.15) continue;
        if (st.backgroundImage && st.backgroundImage !== "none") { paint = "image"; gLum = gradLum(st.backgroundImage); break; }
        var bc = rgb(st.backgroundColor);
        if (bc && bc.a >= 0.9) { paint = st.backgroundColor; break; }
      }
      totalCells++;
      if (paint === "image") {
        gradCells++; tally["渐变/图像"] = (tally["渐变/图像"] || 0) + 1;
        if (gLum != null && gLum < 0.18) { gradDarkCells++; darkCells++; }
        else if (gLum != null && gLum > 0.55) { lightCells++; }
        continue;
      }
      if (!paint) { paint = bodyBg; }
      var k = hex(paint) || paint;
      tally[k] = (tally[k] || 0) + 1;
      var lv = lum(paint);
      if (lv != null) { if (lv < 0.18) darkCells++; else if (lv > 0.55) lightCells++; }
    }
  }
  var groundTop = Object.keys(tally).sort(function (a, b) { return tally[b] - tally[a]; })
    .slice(0, 5).map(function (k) { return { c: k, share: +(tally[k] / totalCells).toFixed(3) }; });

  return {
    viewport: [VW, VH], bodyBg: bodyBg, bodyLum: +bodyL.toFixed(3),
    ground: { top: groundTop, darkShare: +(darkCells / totalCells).toFixed(3),
      lightShare: +(lightCells / totalCells).toFixed(3), gradientShare: +(gradCells / totalCells).toFixed(3),
      gradientDarkShare: +(gradDarkCells / totalCells).toFixed(3) },
    accent: { hue: +(accentHue || 0), topSatHue: +(topSatHue || 0), sat: +best.toFixed(3), hits: acc.length, blocks: blockSet.size, roles: roles,
      hexes: hexes, others: others, tints: tints,
      samples: acc.slice(0, 8).map(function (u) { return u.role + ":" + (u.o.t || u.o.tag).slice(0, 16); }) },
    scale: { maxFs: maxFs, bodyMin: bodyMin, allMin: allMin,
      spanBody: bodyMin ? +(maxFs / bodyMin).toFixed(2) : null,
      spanAll: allMin ? +(maxFs / allMin).toFixed(2) : null,
      biggestText: biggest ? (biggest.t || biggest.tag).slice(0, 60) : null,
      biggestTag: biggest ? biggest.tag : null,
      biggestSel: biggest ? (biggest.tag.toLowerCase()
        + (biggest.e.id ? "#" + biggest.e.id : "")
        + (typeof biggest.e.className === "string" && biggest.e.className.trim()
           ? "." + biggest.e.className.trim().split(/\s+/)[0] : "")) : null,
      biggestContext: biggest && biggest.e.parentElement
        ? biggest.e.parentElement.textContent.replace(/\s+/g, " ").trim().slice(0, 60) : null },
    materials: mat, materialKinds: kinds, volumeKinds: volume,
    holes: holes,
    fontSizes: fsSet, firstScreenEls: seen.length
  };
})();
"""


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到本机 Chrome/Chromium；这一档验收未运行，退回人工测量并如实标明。")


def measure(target, vw, vh):
    src = open(target, encoding="utf-8").read()
    probe_expr = PROBE_JS.strip().rstrip(";")
    inject = "<script>document.addEventListener('DOMContentLoaded',function(){var d=document.createElement('pre');" \
             "d.id='probe-out';d.textContent=JSON.stringify(%s);document.documentElement.appendChild(d);});</script>" % probe_expr
    if "</body>" in src:
        page = src.replace("</body>", inject + "</body>", 1)
    else:
        page = src + inject
    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(page)
    tmp.close()
    try:
        out = subprocess.run(
            [chrome_path(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=%d,%d" % (vw, vh),
             "--virtual-time-budget=8000", "--dump-dom", "file://" + os.path.abspath(tmp.name)],
            capture_output=True, text=True, timeout=120).stdout
    finally:
        os.unlink(tmp.name)
    m = re.search(r'<pre id="probe-out">(.*?)</pre>', out, re.S)
    if not m:
        return {"error": "探针未执行（页面可能有致命 JS 错误，或 Chrome 未渲染）"}
    try:
        return json.loads(htmllib.unescape(m.group(1)))
    except Exception as e:
        return {"error": "JSON 解析失败: %s" % e}


def verdict(name, r):
    if "error" in r:
        return "%s: 探测失败 —— %s" % (name, r["error"])
    a, s = r["accent"], r["scale"]
    ok = lambda b: "过" if b else "不过"
    L = [name]
    L.append("  底 %s（亮度 %.3f）· 首屏可见元素 %d · 视口 %s" % (r["bodyBg"], r["bodyLum"], r["firstScreenEls"], "×".join(map(str, r["viewport"]))))
    L.append("  ① 强调落点：主强调色族 %d°（最高 S %.2f · %s）在首屏出现 %d 处 / %d 个顶层区块 —— %s" % (
        a["hue"], a["sat"], ", ".join(a["hexes"][:4]) or "—", a["hits"], a["blocks"],
        "、".join("%s×%d" % (k, v) for k, v in a["roles"].items()) or "无"))
    L.append("     判据 ≥3 处且 ≥2 区块：%s" % ok(a["hits"] >= 3 and a["blocks"] >= 2))
    L.append("     ①b 其中作为**文字色**的落点 %d 处（判据 ≥1，且必须落在承担论断的数字或标签上）：%s" % (
        a["roles"].get("文字", 0), ok(a["roles"].get("文字", 0) >= 1)))
    if a.get("tints"):
        L.append("     底色族（S 0.10–0.40，不计入落点）：%s——深色页的蓝灰正文常在这一族，别把它当强调" % " ".join(a["tints"]))
    L.append("     最高饱和值落在 %d° 族，与主强调族%s——它是不是「最重要的东西」仍要人判（第 2 问）" % (
        a["topSatHue"], "一致" if a["topSatHue"] == a["hue"] else "不一致"))
    if a["others"]:
        L.append("     其他高饱和色相族：%s（「强调色只用一个色相」若被破坏，看这一行）" % " ".join(a["others"]))
    if a["samples"]:
        L.append("     样本：%s" % " | ".join(a["samples"]))
    L.append("  ② 尺度跨度：首屏最大 %spx（「%s」）÷ 正文最小 %spx = %s" % (s["maxFs"], s["biggestText"], s["bodyMin"], s["spanBody"]))
    L.append("     判据 ≥2.6：%s（按标签算的话是 %s，用正文算才诚实）" % (ok((s["spanBody"] or 0) >= 2.6), s["spanAll"]))
    L.append("     ②b 首屏最大的那个字属于谁：%s%s" % (
        s.get("biggestSel") or "—",
        ("，整块读作「%s」" % s["biggestContext"]) if s.get("biggestContext") and s["biggestContext"] != s["biggestText"] else ""))
    L.append("        判断项，本工具不代答：它必须是**用户能带走的东西**——可核对的数字 / 结果 / 画面 / 动作 / 对象身份。")
    L.append("        若它是立场句、免责声明、否定句、定位宣言或区块标签 → 不过，回 S1.5 重选 P0（content-architecture.md 规则 1b）。")
    mk = "、".join("%s×%d" % (k, v) for k, v in r["materials"].items() if v)
    L.append("  ③ 材质：%d 类 —— %s" % (r["materialKinds"], mk or "无"))
    L.append("     判据 ≥2 类：%s" % ok(r["materialKinds"] >= 2))
    L.append("     ③b 体积载体（投影 / 渐变 / 体积图，三者至少一类）：%d 类 —— %s" % (
        r["volumeKinds"], ok(r["volumeKinds"] >= 1)))
    L.append("        体积图只数含渐变或滤镜的 SVG、以及占首屏 ≥6%% 的 img/canvas/video；"
             "单色图标与平涂矢量不计入（图像×%d 里只有 %d 个承担体积）" % (
                 r["materials"].get("图像", 0), r["materials"].get("体积图", 0)))
    L.append("  ④ 首屏空洞（首屏整块与内部各栏的最长空横带 / 网格填充率）：")
    for h in r.get("holes", [])[:5]:
        L.append("     %-26s %4d×%4d  最长空横带 %4dpx @y=%4d  填充率 %.2f" % (
            h["tag"], h["w"], h["h"], h["band"], h["bandY"], h["fill"]))
    low = [h for h in r.get("holes", []) if h["fill"] < 0.5]
    L.append("     判断项，不代答：填充率 <0.50 的栏有 %d 个%s。每一块都要能说出「这块空白在干什么」；"
             "说不出就回 S3 改密度契约，不是回 S4 加装饰。数字只负责把空洞摆到眼前，不负责判好坏。" % (
                 len(low), ("（" + "、".join(h["tag"] for h in low[:3]) + "）") if low else ""))
    L.append("  ⑤ 「为什么是它」：判断项，本工具不代答。")
    g = r.get("ground") or {}
    if g:
        L.append("  ⑥ 首屏实际主底色（按 24px 网格取每点最上层实心背景，量渲染结果不量 body 声明）：")
        L.append("     面积占比：%s" % (" ".join("%s %.0f%%" % (t["c"], t["share"] * 100) for t in g["top"]) or "—"))
        L.append("     深色域 %.0f%%（其中渐变里的深色 %.0f%%）· 浅色域 %.0f%% · 渐变/图像域 %.0f%%" % (
            g["darkShare"] * 100, g.get("gradientDarkShare", 0) * 100,
            g["lightShare"] * 100, g["gradientShare"] * 100))
        L.append("     渐变取不到渲染像素，其明暗按色标平均亮度近似；实心背景是实测值。")
        L.append("     body 声明 %s（亮度 %.3f）——与上面的主底色不一致时，以主底色为准。" % (r["bodyBg"], r["bodyLum"]))
        L.append("     判据（第四轮修订）：明暗不限；色相与产品界面同族；地面要托住对象——有层次或对象自身有体积；平涂+平对象=不过。")
        L.append("     本工具只量面积占比，量不出「对象是否清楚、内容是否说得准」——那要人看首屏截图（critique.md 第十问第 6、7 步）。")
    L.append("  首屏字号去重：%s" % " / ".join(str(x) for x in r["fontSizes"]))
    return "\n".join(L)


def main():
    argv = sys.argv[1:]
    skip = set()
    for flag in ("--viewport", "--json"):
        if flag in argv:
            skip.add(argv.index(flag) + 1)
    targets = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in skip]
    vw, vh = 838, 1060
    if "--viewport" in argv:
        vw, vh = map(int, argv[argv.index("--viewport") + 1].split(","))
    json_out = argv[argv.index("--json") + 1] if "--json" in argv else None
    if not targets:
        raise SystemExit(__doc__)
    results = {}
    for t in targets:
        parent = os.path.basename(os.path.dirname(t.rstrip("/")))
        name = os.path.basename(t.rstrip("/"))
        results[(parent + "/" + name) if parent else name] = measure(t, vw, vh)
    for name, r in results.items():
        print(verdict(name, r) + "\n")
    if json_out:
        open(json_out, "w", encoding="utf-8").write(json.dumps(results, ensure_ascii=False, indent=2))
        print("已写入 %s" % json_out)


main()
