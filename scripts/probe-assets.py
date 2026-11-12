#!/usr/bin/env python3
"""probe-assets.py —— 页面里的图片是不是真的加载出来了。

用法：
    python3 scripts/probe-assets.py <page.html> [page2.html ...] [--viewport 1440,900]

为什么需要它：实跑里出现过「hero 图相对路径写错，页面显示 alt 文本，
而执行者仍然声称已经截图自查过」。图没加载不是小事，它会让整轮的
视觉判断建立在一张不存在的画面上。这一项能机械判定，就不该靠自觉。

退出码：0 = 全部加载成功；1 = 有图没加载；2 = 探测本身没跑成。
只依赖 python3 标准库 + 本机 Chrome/Chromium，不需要 Node。
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
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

PROBE_JS = r"""
(function(){
  var emit = function(o){ window.__probeDone(o); };
  function label(el){
    var t = (el.getAttribute('alt') || el.textContent || '').trim().replace(/\s+/g,' ').slice(0,48);
    var c = (typeof el.className === 'string') ? el.className.trim().split(/\s+/)[0] : '';
    return el.tagName.toLowerCase() + (c ? '.' + c : '') + (t ? ' 「' + t + '」' : '');
  }
  function inFirst(el, vh){
    var r = el.getBoundingClientRect();
    return r.top < vh && r.bottom > 0 && r.width > 0 && r.height > 0;
  }
  function snap(el){
    var r = el.getBoundingClientRect();
    return {label: label(el), src: el.getAttribute('src') || '', complete: el.complete,
            nw: el.naturalWidth, w: Math.round(r.width), h: Math.round(r.height),
            first: inFirst(el, window.innerHeight)};
  }
  // DOMContentLoaded 时 complete 还是 false，必须等图片各自 settle 才能区分「坏了」和「还没好」。
  var nodes = [];
  document.querySelectorAll('img').forEach(function(el){ nodes.push(el); });
  var settled = new Array(nodes.length);
  function finish(){
    var imgs = [], broken = [], unresolved = [];
    nodes.forEach(function(el, i){
      var rec = snap(el);
      rec.settled = !!settled[i];
      imgs.push(rec);
      if (rec.settled === 'error' || (rec.complete && rec.nw === 0)) broken.push(rec);
      else if (!rec.complete || rec.nw === 0) unresolved.push(rec);
    });
    var cssUrls = {};
    document.querySelectorAll('*').forEach(function(el){
      var bi = getComputedStyle(el).backgroundImage;
      if (!bi || bi === 'none') return;
      var m = bi.match(/url\((['\"]?)(.*?)\1\)/g);
      if (!m) return;
      m.forEach(function(u){
        var raw = u.replace(/^url\((['\"]?)/,'').replace(/(['\"]?)\)$/,'');
        if (raw.indexOf('data:') === 0) return;
        cssUrls[raw] = label(el);
      });
    });
    var keys = Object.keys(cssUrls);
    function withCss(cssBroken){
      return {viewport: [window.innerWidth, window.innerHeight], imgTotal: imgs.length,
              imgs: imgs, broken: broken, unresolved: unresolved,
              cssTotal: keys.length, cssBroken: cssBroken};
    }
    if (!keys.length) { emit(withCss([])); return; }
    var res = [], n = 0;
    keys.forEach(function(u){
      var t = new Image();
      t.onload = function(){ if (++n === keys.length) emit(withCss(res)); };
      t.onerror = function(){ res.push({url: u, label: cssUrls[u]}); if (++n === keys.length) emit(withCss(res)); };
      t.src = u;
    });
    setTimeout(function(){ emit(withCss(res)); }, 4000);
  }
  var remaining = nodes.length;
  if (!remaining) { finish(); }
  nodes.forEach(function(el, i){
    if (el.complete) { settled[i] = (el.naturalWidth === 0 ? 'error' : 'load'); if (--remaining === 0) finish(); return; }
    el.addEventListener('load', function(){ settled[i] = 'load'; if (--remaining === 0) finish(); });
    el.addEventListener('error', function(){ settled[i] = 'error'; if (--remaining === 0) finish(); });
  });
  setTimeout(function(){ if (remaining > 0) finish(); }, 5000);
})()
"""


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到本机 Chrome/Chromium；这一档验收未运行，请如实标明未测。")


def measure(target, vw, vh):
    src = open(target, encoding="utf-8").read()
    # 探针副本写在临时目录里，相对路径会全部指不到素材 —— 必须用 <base> 把基准钉回原文件所在目录，
    # 否则「图坏了」和「副本换了目录」两种情况分不开，报出来的全是假阳性。
    base = "file://" + os.path.dirname(os.path.abspath(target)) + "/"
    inject = ("<script>document.addEventListener('DOMContentLoaded',function(){var d=document.createElement('pre');"
              "d.id='probe-out';window.__probeDone=function(o){d.textContent=JSON.stringify(o);"
              "document.documentElement.appendChild(d);};%s});</script>" % PROBE_JS.strip())
    if re.search(r"<head[^>]*>", src):
        page = re.sub(r"(<head[^>]*>)", r'\1<base href="%s">' % base, src, count=1)
    else:
        page = '<base href="%s">' % base + src
    if "</body>" in page:
        page = page.replace("</body>", inject + "</body>", 1)
    else:
        page = page + inject
    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(page)
    tmp.close()
    try:
        out = subprocess.run(
            [chrome_path(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=%d,%d" % (vw, vh),
             "--virtual-time-budget=12000", "--dump-dom", "file://" + os.path.abspath(tmp.name)],
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


def report(name, r):
    if "error" in r:
        print("%s: 探测失败 —— %s" % (name, r["error"]))
        return 2
    bad = r["broken"] + r["cssBroken"]
    print(name)
    print("  视口 %s · <img> %d 个 · CSS 背景图 %d 个" % ("×".join(map(str, r["viewport"])), r["imgTotal"], r["cssTotal"]))
    if not bad:
        print("  加载失败的图：0 处")
    else:
        print("  加载失败的 %d 处（不过）：" % len(bad))
        for b in r["broken"]:
            print("     · <img> %s src=%s naturalWidth=%d 尺寸=%d×%d%s" % (
                b["label"], b["src"] or "(空)", b["nw"], b["w"], b["h"], " 【首屏】" if b["first"] else ""))
        for b in r["cssBroken"]:
            print("     · 背景图 %s url=%s" % (b["label"], b["url"]))
    if r["unresolved"]:
        print("  超时仍未确认加载完成的 %d 处（按未验证处理，逐张人工核对，不得当作通过）：" % len(r["unresolved"]))
        for b in r["unresolved"]:
            print("     · %s src=%s complete=%s naturalWidth=%d" % (b["label"], b["src"], b["complete"], b["nw"]))
    if not bad and not r["unresolved"]:
        print("  全部加载成功：过")
        return 0
    if not bad and r["unresolved"]:
        print("  提示：图显示成 alt 文本时，页面看起来像「有图」，截图里却是空白块——本轮所有视觉判断都会失真。")
        return 1
    print("  提示：图显示成 alt 文本时，页面看起来像「有图」，截图里却是空白块——本轮所有视觉判断都会失真。")
    return 1


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    vw, vh = 1440, 900
    for flag in ("--viewport",):
        if flag in argv:
            vw, vh = map(int, argv[argv.index(flag) + 1].split(","))
    skip = {argv.index("--viewport") + 1} if "--viewport" in argv else set()
    targets = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in skip]
    code = 0
    for t in targets:
        if not os.path.exists(t):
            print("%s: 文件不存在" % t)
            code = max(code, 2)
            continue
        code = max(code, report(t, measure(t, vw, vh)))
    return code


if __name__ == "__main__":
    sys.exit(main())
