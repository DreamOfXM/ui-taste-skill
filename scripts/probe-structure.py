#!/usr/bin/env python3
"""量首屏的结构，不量颜色。用法：probe-structure.py <页面.html> [更多页面...] [--vw 1440 --vh 900]

配合 critique.md 第十问第 5 步：首屏最大的那块图是「对象」还是「界面」。
只摆数字，不代判——图元多少不是判据（赢的稿 81 > 输的稿 62），
要读的是「有坐标轴/网格」「有图例」「工具控件 N 个」这三项，以及人看图。
文字块数与字号档只作参考：实测赢的稿块数反而更多，不能用它判优劣。
"""
import json, os, re, subprocess, sys, tempfile, html as H

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
JS = r"""
(function(){
  var VW=innerWidth, VH=innerHeight;
  function own(e){return Array.prototype.filter.call(e.childNodes,function(n){return n.nodeType===3;})
    .map(function(n){return n.textContent;}).join("").replace(/\s+/g," ").trim();}
  var blocks=[];
  document.querySelectorAll("body *").forEach(function(e){
    var r=e.getBoundingClientRect();
    if(r.bottom<=0||r.top>=VH||r.width<4||r.height<4) return;
    var s=getComputedStyle(e);
    if(s.visibility==="hidden"||s.display==="none"||parseFloat(s.opacity)<0.15) return;
    if(e.closest("[aria-hidden=true]")) return;
    var t=own(e); if(!t) return;
    blocks.push({t:t.slice(0,40),fs:parseFloat(s.fontSize),y:Math.round(r.top),x:Math.round(r.left),
      w:Math.round(r.width),tag:e.tagName.toLowerCase()});
  });
  blocks.sort(function(a,b){return a.y-b.y||a.x-b.x;});
  // 图形复杂度：首屏里最大的那个 svg / canvas
  var figs=[];
  document.querySelectorAll("svg").forEach(function(e){
    var r=e.getBoundingClientRect();
    if(r.bottom<=0||r.top>=VH||r.width<120||r.height<120) return;
    var marks=e.querySelectorAll("rect,circle,ellipse,line,path,polygon,polyline").length;
    var texts=e.querySelectorAll("text,tspan").length;
    // 类名子串匹配会误伤：键帽上的字母叫 cap-legend，不是图表图例。
    // 所以只报「匹配到了什么类名」，是不是图表交给人看图判。
    function hits(sel){
      var out=[];
      e.querySelectorAll(sel).forEach(function(n){
        var c=(typeof n.className==="string"?n.className:(n.className.baseVal||"")).trim();
        if(c&&out.indexOf(c)<0) out.push(c);
      });
      return out.slice(0,4);
    }
    figs.push({w:Math.round(r.width),h:Math.round(r.height),area:Math.round(r.width*r.height),
      marks:marks,texts:texts,
      axisHits:hits("[class*=axis],[class*=tick],[class*=grid]"),
      legendHits:hits("[class*=legend]")});
  });
  figs.sort(function(a,b){return b.area-a.area;});
  // 首屏里的「工具控件」：滑块、开关、下拉、导出/重置一类按钮
  var ctrls=[], btns=[];
  document.querySelectorAll("input,select,button,[role=slider],[role=switch]").forEach(function(e){
    var r=e.getBoundingClientRect();
    if(r.bottom<=0||r.top>=VH||r.width<4||r.height<4) return;
    var s=getComputedStyle(e);
    if(s.visibility==="hidden"||s.display==="none") return;
    var ty=(e.getAttribute("type")||"").toLowerCase();
    if(e.tagName==="INPUT"&&["range","checkbox","radio","number"].indexOf(ty)>=0) ctrls.push(ty);
    else if(e.tagName==="SELECT"||e.getAttribute("role")==="slider"||e.getAttribute("role")==="switch") ctrls.push(e.tagName.toLowerCase());
    else {
      var t=(e.textContent||"").replace(/\s+/g," ").trim();
      if(t) btns.push(t.slice(0,12));
    }
  });
  return {viewport:[VW,VH],blocks:blocks,figs:figs.slice(0,3),ctrls:ctrls,btns:btns};
})();
"""

def run(path, vw=1440, vh=900):
    src = open(path, encoding="utf-8").read()
    expr = JS.strip().rstrip(";")
    inj = ("<script>document.addEventListener('DOMContentLoaded',function(){"
           "setTimeout(function(){var d=document.createElement('pre');d.id='__p';"
           "d.textContent=JSON.stringify(" + expr + ");document.body.appendChild(d);},250);});</script>")
    src = src.replace("</body>", inj + "</body>") if "</body>" in src else src + inj
    d = os.path.dirname(os.path.abspath(path))
    f = tempfile.NamedTemporaryFile("w", suffix=".html", dir=d, delete=False, encoding="utf-8")
    f.write(src); f.close()
    try:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--force-prefers-reduced-motion", "--window-size=%d,%d" % (vw, vh),
            "--virtual-time-budget=4000", "--dump-dom", "file://" + f.name],
            capture_output=True, text=True, timeout=90).stdout
        m = re.search(r'<pre id="__p">(.*?)</pre>', out, re.S)
        return json.loads(H.unescape(m.group(1))) if m else {"error": "no output"}
    finally:
        os.unlink(f.name)

args = sys.argv[1:]
vw, vh, paths = 1440, 900, []
i = 0
while i < len(args):
    if args[i] == "--vw": vw = int(args[i + 1]); i += 2
    elif args[i] == "--vh": vh = int(args[i + 1]); i += 2
    else: paths.append(args[i]); i += 1
if not paths:
    print("用法：probe-structure.py <页面.html> [更多页面...] [--vw 1440 --vh 900]"); sys.exit(1)

for p in paths:
    r = run(p, vw, vh)
    print("#" * 12, p, "(%d×%d)" % (vw, vh))
    if "error" in r:
        print(" ", r["error"]); continue
    b = r["blocks"]
    sizes = {}
    for x in b:
        sizes[x["fs"]] = sizes.get(x["fs"], 0) + 1
    print("  首屏独立文字块 %d 个；字号档 %d 档：%s" % (
        len(b), len(sizes), " / ".join("%gpx×%d" % (k, v) for k, v in sorted(sizes.items(), reverse=True))))
    small = [x for x in b if x["fs"] <= 17]
    print("  ≤17px 的小字块 %d 个（占 %.0f%%）" % (len(small), 100 * len(small) / max(1, len(b))))
    for f in r["figs"]:
        print("  主图形 %d×%d：图元 %d 个、图内文字 %d 个%s%s" % (
            f["w"], f["h"], f["marks"], f["texts"],
            "、疑似坐标轴/网格(%s)" % ",".join(f["axisHits"]) if f.get("axisHits") else "",
            "、疑似图例(%s)" % ",".join(f["legendHits"]) if f.get("legendHits") else ""))
    if r["figs"] and any(f.get("axisHits") or f.get("legendHits") for f in r["figs"]):
        print("     ↑ 只是类名命中，不是判定：键帽字母 cap-legend、装饰网格都会命中。看图确认是不是真要读轴的图表。")
    if not r["figs"]:
        print("  首屏无 ≥120×120 的 SVG")
    print("  首屏工具控件（滑块/开关/下拉）%d 个；按钮 %d 个：%s" % (
        len(r["ctrls"]), len(r["btns"]), " / ".join(r["btns"][:8]) or "无"))