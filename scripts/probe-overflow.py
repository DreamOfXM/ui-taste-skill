#!/usr/bin/env python3
"""probe-overflow.py —— 内容被容器裁掉了没有（尤其是安装命令与长 URL）。

用法：
    python3 scripts/probe-overflow.py <page.html> [page2.html ...] [--viewport 1440,900]

为什么需要它：实跑里出现过命令卡把 `brew tap … https://github.com/…/agent-ping`
裁成 `…/agent-pin`。读者复制到的是断掉的命令，而页面上看不出来——它不是「不好看」，
是「这条承诺没兑现」。这一项能机械判定。

退出码：0 = 无溢出；1 = 有溢出；2 = 探测本身没跑成。
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
  function text(el){ return (el.innerText || el.textContent || '').trim().replace(/\s+/g,' ').slice(0,60); }
  function label(el){
    var c = (typeof el.className === 'string') ? el.className.trim().split(/\s+/)[0] : '';
    return el.tagName.toLowerCase() + (c ? '.' + c : '');
  }
  function rendered(el, st){
    if (!el.getClientRects().length) return false;
    if (st.display === 'none' || st.visibility === 'hidden') return false;
    if (parseFloat(st.opacity) === 0) return false;
    if (el.offsetWidth === 0 || el.clientHeight === 0) return false;
    if (el.clientWidth === 0) return false;          // 零宽容器谈不上「被裁」
    if (!el.offsetParent && st.position !== 'fixed') return false;
    return true;
  }
  function absOnly(el){
    // 只有绝对/固定定位的后代越界时，越界的是装饰层，不是读者要读的内容。
    var inflow = false, any = false;
    el.querySelectorAll('*').forEach(function(c){
      var r = c.getBoundingClientRect();
      if (r.right <= el.getBoundingClientRect().right + 1) return;
      any = true;
      var p = getComputedStyle(c).position;
      if (p !== 'absolute' && p !== 'fixed') inflow = true;
    });
    return any && !inflow;
  }
  var hits = [], seen = {};
  document.querySelectorAll('*').forEach(function(el){
    if (hits.length >= 40) return;
    var st = getComputedStyle(el);
    if (!rendered(el, st)) return;                       // 隐藏的抽屉/浮层 clientWidth=0，不是裁切
    var clip = st.overflowX === 'hidden' || st.overflowX === 'clip';
    var scrollx = st.overflowX === 'auto' || st.overflowX === 'scroll';
    var nowrap = st.whiteSpace === 'nowrap' || st.whiteSpace === 'pre';
    if (!clip && !scrollx && !nowrap) return;
    var txt = text(el);
    if (!txt) return;
    var over = el.scrollWidth - el.clientWidth;
    if (over <= 1) return;
    var isCmd = /https?:\/\//.test(txt) || /^(brew|sudo|cmake|ninja|apt|sh |python|node|go |cargo)/.test(txt)
                || /^(pre|code|kbd|samp)$/i.test(el.tagName);
    var key = label(el) + '|' + txt;
    if (seen[key]) return;
    seen[key] = 1;
    var r = el.getBoundingClientRect();
    hits.push({label: label(el), txt: txt, over: over, sw: el.scrollWidth, cw: el.clientWidth,
               mode: scrollx ? '需横向滚动' : '被裁断', cmd: isCmd, deco: absOnly(el),
               first: r.top < window.innerHeight && r.bottom > 0});
  });
  var docOver = document.documentElement.scrollWidth - window.innerWidth;
  return {viewport: [window.innerWidth, window.innerHeight], hits: hits, docOverflow: docOver};
})()
"""


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到本机 Chrome/Chromium；这一档验收未运行，请如实标明未测。")


def measure(target, vw, vh):
    src = open(target, encoding="utf-8").read()
    inject = ("<script>document.addEventListener('DOMContentLoaded',function(){var d=document.createElement('pre');"
              "d.id='probe-out';d.textContent=JSON.stringify(%s);document.documentElement.appendChild(d);});</script>" % PROBE_JS.strip())
    page = src.replace("</body>", inject + "</body>", 1) if "</body>" in src else src + inject
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
    print(name)
    print("  视口 %s · 溢出元素 %d 个 · 整页横向溢出 %dpx" % (
        "×".join(map(str, r["viewport"])), len(r["hits"]), max(0, r["docOverflow"])))
    hard = [h for h in r["hits"] if (h["cmd"] or h["mode"] == "被裁断") and not h["deco"]]
    deco = [h for h in r["hits"] if h["deco"]]
    for h in r["hits"]:
        print("  · %s 溢出 %dpx（scrollWidth %d / client %d）【%s%s%s%s】" % (
            h["label"], h["over"], h["sw"], h["cw"], h["mode"],
            " 命令/URL" if h["cmd"] else "", " 仅装饰层越界" if h["deco"] else "", " 首屏" if h["first"] else ""))
        print("      内容：%s" % h["txt"])
    if deco:
        print("  其中 %d 处只有绝对/固定定位的后代越界（装饰层），不计入判定，但仍建议确认是不是画歪了。" % len(deco))
    if not hard and r["docOverflow"] <= 1:
        print("  无内容被裁、无命令需滚动：过")
        return 0
    if hard:
        print("  不过：%d 处读者要读/要复制的内容超出容器。命令或 URL 被裁、要横移才能看全，等于这条承诺没兑现 —— 改整宽、允许换行，或把命令折行显示。" % len(hard))
    if r["docOverflow"] > 1:
        print("  不过：整页横向溢出 %dpx（出现横向滚动条，说明某块宽度算错了）。" % r["docOverflow"])
    return 1


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    vw, vh = 1440, 900
    skip = set()
    if "--viewport" in argv:
        vw, vh = map(int, argv[argv.index("--viewport") + 1].split(","))
        skip.add(argv.index("--viewport") + 1)
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
