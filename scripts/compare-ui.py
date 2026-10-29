#!/usr/bin/env python3
"""Build a local, source-blinded screenshot comparison; no aesthetic scoring."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import secrets
import struct
import sys
import zlib


PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 128 * 1024 * 1024
DISPLAY_CHUNKS = {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND',
                  b'sRGB', b'gAMA', b'cHRM', b'bKGD'}


PAGE = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>界面对照</title><style>
:root{font-family:system-ui,sans-serif;color:#202329;background:#eceef0}*{box-sizing:border-box}
body{margin:0}header{padding:16px 24px;background:#fff;border-bottom:1px solid #cbd0d6}
h1{font-size:20px;margin:0 0 8px}p{margin:8px 0;line-height:1.6}nav,.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
nav label{display:flex;gap:8px;align-items:center;min-width:0;max-width:100%}nav select{flex:1;min-width:0;max-width:100%}
button,select,textarea{font:inherit}button,select{padding:8px 12px;background:#fff;color:#202329;border:1px solid #8b929b;border-radius:4px;cursor:pointer}
button[aria-pressed=true]{background:#202329;color:#fff}button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #1261c4;outline-offset:2px}
main{padding:16px 24px}figure{margin:16px 0;background:#d7dade;overflow:auto}img{display:block;max-width:100%;height:auto;margin:auto}
figure.actual img{max-width:none}figcaption{padding:8px;background:#fff;font-size:13px}.review{max-width:960px;margin:auto;padding:16px;background:#fff}
textarea{display:block;width:100%;min-height:100px;padding:12px;margin:10px 0}small{display:block;line-height:1.6;color:#4c5560}.status{min-height:24px}
@media(max-width:600px){header,main{padding:12px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style><header><h1>界面对照</h1><p id="task"></p><small>先看画面，再写位置与理由。版本来源不在本页；这是视觉偏好记录，不是功能验证或自动美感分数。</small></header>
<main><nav aria-label="比较任务"><label>任务 <select id="case"></select></label><label>状态 <select id="state"></select></label></nav>
<div class="controls" id="variants" aria-label="候选" style="margin-top:12px"></div>
<figure id="frame"><figcaption id="caption"></figcaption><img id="shot" alt="当前候选的实际界面截图"></figure>
<section class="review"><label><input id="actual" type="checkbox"> 原始像素尺寸（可滚动）</label>
<p>整屏吸引力、产品适配、排印与材料、内页/窄屏是否成立？功能是否可用请另行操作检查。</p>
<label>综合选择 <select id="vote" disabled><option value="unreviewed">尚未判断</option><option value="tie">打平 / 各有优势</option><option value="neither">都不满意</option></select></label>
<label for="notes"><p>具体位置 → 关系 → 选择理由 / 最大差距</p></label><textarea id="notes" placeholder="不要只写高级、整齐或测试通过"></textarea>
<button id="export" disabled>下载本次判断</button><p class="status" id="status" role="status"></p><small>记录只在当前页面内存，刷新会清空；下载后保留。来源映射单独保存在 reveal.json，请评完再查看，并核对 comparisonId 一致。</small></section></main>
<script>
const comparisonId=__COMPARISON_ID__;
const cases=__DATA__, votes={}, el=id=>document.getElementById(id);
let ci=0,si=0,vi=0,checked=false,shotReady=false;
const failedImages=new Set();
function readiness(){
  const disabled=!checked||!shotReady||failedImages.size>0;
  el('vote').disabled=disabled;el('export').disabled=disabled;
  el('status').textContent=failedImages.size?'截图加载失败，无法投票或导出。请重新生成比较页面。':disabled?'正在检查截图，请稍候。':'';
}
function loaded(image,state){return image.naturalWidth===state.width&&image.naturalHeight===state.height}
async function checkImages(){
  // Check even unvisited screenshots, sequentially to avoid decoding them all at once.
  for(const c of cases)for(const v of c.candidates)for(const s of v.states){
    await new Promise(resolve=>{
      const image=new Image();
      image.onload=()=>{if(!loaded(image,s))failedImages.add(s);resolve()};
      image.onerror=()=>{failedImages.add(s);resolve()};
      image.src=s.image;
    });
    readiness();
  }
  checked=true;readiness();
}
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o}
cases.forEach((c,i)=>el('case').append(option(i,c.title)));
function save(){if(el('vote').disabled)return;votes[cases[ci].key]={choice:el('vote').value,notes:el('notes').value}}
function show(){
  const c=cases[ci],v=c.candidates[vi],s=v.states[si],image=new Image();
  shotReady=false;readiness();image.id='shot';image.alt=`候选 ${v.label} · ${s.label}`;
  image.onload=()=>{if(!loaded(image,s))failedImages.add(s);if(el('shot')===image)shotReady=loaded(image,s);readiness()};
  image.onerror=()=>{failedImages.add(s);if(el('shot')===image)shotReady=false;readiness()};
  el('shot').replaceWith(image);image.src=s.image;
  el('caption').textContent=`${v.label} / ${s.label} / ${s.width} × ${s.height}`;
  [...el('variants').children].forEach((b,i)=>b.setAttribute('aria-pressed',String(i===vi)));
}
function setup(){const c=cases[ci];el('task').textContent=c.title;el('state').replaceChildren(...c.candidates[0].states.map((s,i)=>option(i,s.label)));el('variants').replaceChildren();el('vote').replaceChildren(option('unreviewed','尚未判断'),option('tie','打平 / 各有优势'),option('neither','都不满意'));c.candidates.forEach((v,i)=>{const b=document.createElement('button');b.textContent=v.label;b.onclick=()=>{vi=i;show()};el('variants').append(b);el('vote').append(option(v.label,v.label))});const record=votes[c.key];el('vote').value=record?.choice||'unreviewed';el('notes').value=record?.notes||'';show()}
el('case').onchange=()=>{save();ci=Number(el('case').value);si=0;vi=0;setup()};el('state').onchange=()=>{si=Number(el('state').value);show()};el('notes').oninput=save;el('vote').onchange=save;
el('actual').onchange=()=>el('frame').classList.toggle('actual',el('actual').checked);
el('export').onclick=()=>{if(el('export').disabled)return;save();const blob=new Blob([JSON.stringify({comparisonId,reviewer:'unspecified',createdAt:new Date().toISOString(),votes},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`visual-preferences-${comparisonId}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);el('status').textContent='已生成下载；这份记录不包含来源映射。'};
setup();checkImages();
</script></html>'''


def validate_pixels(idat, row_bytes, height):
    """Validate the zlib stream without retaining the decompressed image."""
    stride = row_bytes + 1
    expected = stride * height
    if expected > MAX_DECOMPRESSED_BYTES:
        raise ValueError('PNG decompressed pixels exceed the 128 MB limit')
    decoder, total = zlib.decompressobj(), 0
    try:
        for start in range(0, len(idat), 65536):
            pending = memoryview(idat)[start:start + 65536]
            while True:
                limit = min(65536, expected - total + 1)
                block = decoder.decompress(pending, limit)
                if total + len(block) > expected:
                    raise ValueError('Invalid PNG decompressed scanline length')
                # Every row starts with one filter byte, even across decode blocks.
                if any(block[i] > 4 for i in range((-total) % stride, len(block), stride)):
                    raise ValueError('Invalid PNG scanline filter')
                total += len(block)
                if decoder.unused_data:
                    raise ValueError('Invalid PNG trailing compressed data')
                pending = decoder.unconsumed_tail
                if not pending and len(block) < limit:
                    break
        if not decoder.eof or total != expected:
            raise ValueError('Invalid PNG incomplete pixels or scanline length')
    except zlib.error as error:
        raise ValueError('Invalid PNG zlib pixel data') from error


def sanitize_png(data):
    """Validate a static PNG, then retain only explicitly allowed visual chunks."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError('Invalid PNG signature')
    # Byte buffers, rather than per-chunk objects, bound memory even with many tiny chunks.
    offset, seen, retained, idat = 8, set(), bytearray(PNG_SIGNATURE), bytearray()
    palette_size, idat_ended = 0, False
    width = height = depth = color = row_bytes = 0
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError('Invalid PNG truncated chunk')
        length, kind = struct.unpack_from('>I4s', data, offset)
        end = offset + length + 12
        if end > len(data):
            raise ValueError('Invalid PNG truncated chunk data')
        if (any(not (65 <= c <= 90 or 97 <= c <= 122) for c in kind)
                or kind[2] & 32):
            raise ValueError('Invalid PNG chunk type')
        body = memoryview(data)[offset + 8:end - 4]
        crc = zlib.crc32(body, zlib.crc32(kind)) & 0xffffffff
        if crc != struct.unpack_from('>I', data, end - 4)[0]:
            raise ValueError('Invalid PNG chunk CRC')
        if not seen and kind != b'IHDR':
            raise ValueError('Invalid PNG: IHDR must be first')
        if kind in {b'acTL', b'fcTL', b'fdAT'}:
            raise ValueError('Animated PNG is unsupported; re-export as a static PNG')
        if kind in {b'iCCP', b'cICP', b'mDCV', b'cLLI'}:
            raise ValueError('Profiled/HDR PNG requires color conversion to sRGB before comparison')
        if not kind[0] & 32 and kind not in {b'IHDR', b'PLTE', b'IDAT', b'IEND'}:
            raise ValueError('Unsupported critical PNG chunk; re-export as a static PNG')
        if kind in DISPLAY_CHUNKS and kind != b'IDAT' and kind in seen:
            raise ValueError('Invalid PNG duplicate chunk')
        if kind == b'IHDR':
            if length != 13:
                raise ValueError('Invalid PNG IHDR length')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8},
                      4: {8, 16}, 6: {8, 16}}
            if color not in depths or depth not in depths[color] or compression or filtering:
                raise ValueError('Invalid PNG IHDR color type, bit depth or method')
            if interlace == 1:
                raise ValueError('Interlaced PNG is unsupported; re-export as a non-interlaced PNG')
            if interlace:
                raise ValueError('Invalid PNG interlace method')
            if not width or not height or width * height > 32_000_000:
                raise ValueError('Invalid or oversized PNG dimensions')
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
            row_bytes = (width * channels * depth + 7) // 8
            if (row_bytes + 1) * height > MAX_DECOMPRESSED_BYTES:
                raise ValueError('PNG decompressed pixels exceed the 128 MB limit')
        elif kind == b'PLTE':
            if (b'IDAT' in seen or b'tRNS' in seen or b'bKGD' in seen
                    or color in {0, 4} or not length or length % 3 or length > 768):
                raise ValueError('Invalid PNG palette length or order')
            palette_size = length // 3
            if color == 3 and palette_size > 2 ** depth:
                raise ValueError('Invalid PNG palette for bit depth')
        elif kind in {b'sRGB', b'gAMA', b'cHRM'}:
            if b'PLTE' in seen or b'IDAT' in seen:
                raise ValueError('Invalid PNG color chunk order')
            if ((kind == b'sRGB' and (length != 1 or body[0] > 3))
                    or (kind == b'gAMA' and (length != 4 or not int.from_bytes(body, 'big')))
                    or (kind == b'cHRM' and length != 32)):
                raise ValueError('Invalid PNG color chunk')
        elif kind in {b'tRNS', b'bKGD'}:
            if b'IDAT' in seen or (color == 3 and not palette_size):
                raise ValueError('Invalid PNG transparency/background order')
            if color == 3:
                valid = (0 < length <= palette_size if kind == b'tRNS'
                         else length == 1 and body[0] < palette_size)
            else:
                samples = 1 if color in {0, 4} else 3
                valid = length == samples * 2
                if kind == b'tRNS' and color in {4, 6}:
                    valid = False
                if valid:
                    valid = all(sample[0] < 2 ** depth for sample in struct.iter_unpack('>H', body))
            if not valid:
                raise ValueError('Invalid PNG transparency/background chunk')
        elif kind == b'IDAT':
            if idat_ended or (color == 3 and not palette_size):
                raise ValueError('Invalid PNG IDAT order or missing palette')
            idat.extend(body)
        elif kind == b'IEND':
            if length or b'IDAT' not in seen or end != len(data):
                raise ValueError('Invalid PNG IEND or trailing data')
        if b'IDAT' in seen and kind != b'IDAT':
            idat_ended = True
        if kind in DISPLAY_CHUNKS:
            retained.extend(memoryview(data)[offset:end])
            seen.add(kind)
        offset = end
    if b'IEND' not in seen:
        raise ValueError('Invalid PNG missing IDAT or IEND')
    validate_pixels(idat, row_bytes, height)
    return bytes(retained), width, height


def load_image(root, value):
    if not isinstance(value, str):
        raise ValueError('image must be a relative PNG path')
    relative = Path(value)
    source = (root / relative).resolve()
    if relative.is_absolute() or not source.is_relative_to(root):
        raise ValueError('Images must stay inside the manifest directory')
    if source.suffix.lower() != '.png' or source.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('Each image must be a PNG no larger than 16 MB')
    with source.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('Each image must be a PNG no larger than 16 MB')
    displayed, width, height = sanitize_png(data)
    return displayed, width, height, hashlib.sha256(data).hexdigest()


def build(manifest, output):
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('Manifest must be an object with cases')
    cases = payload.get('cases')
    if not isinstance(cases, list) or not cases or len(cases) > 20:
        raise ValueError('Manifest needs 1–20 cases')
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError('Output must be a new or empty non-symlink directory')
    comparison_id = secrets.token_hex(16)
    public, reveal, keys = [], [], set()
    for case in cases:
        key, title, candidates = case['id'], case['title'], case['candidates']
        if not isinstance(key, str) or not key or key in keys or not isinstance(title, str):
            raise ValueError('Each case needs a unique nonempty id and a title')
        keys.add(key)
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 4:
            raise ValueError('Each case needs 2–4 candidates')
        candidates = list(candidates)
        secrets.SystemRandom().shuffle(candidates)
        rendered, mapping, expected, identities = [], {}, None, set()
        for index, candidate in enumerate(candidates):
            identity = candidate['id']
            if not isinstance(identity, str) or not identity or identity in identities:
                raise ValueError('Candidate IDs must be unique within a case')
            identities.add(identity)
            label = chr(65 + index)
            states = candidate['states']
            if not isinstance(states, list) or not states or len(states) > 12:
                raise ValueError('Each candidate needs 1–12 screenshot states')
            images, dimensions, hashes, displayed_hashes = [], [], [], []
            for state in states:
                if not isinstance(state['label'], str) or not state['label']:
                    raise ValueError('State labels must be nonempty strings')
                data, width, height, original_hash = load_image(manifest.parent, state['image'])
                full_page = state.get('fullPage', False)
                if not isinstance(full_page, bool):
                    raise ValueError('fullPage must be a boolean')
                if full_page and 'viewport' not in state:
                    raise ValueError('fullPage requires an explicit viewport [width, height]')
                viewport = state.get('viewport', [width, height])
                if (not isinstance(viewport, list) or len(viewport) != 2
                        or any(type(size) is not int or size <= 0 for size in viewport)):
                    raise ValueError('viewport must be [width, height] with positive integers')
                if width != viewport[0] or (height < viewport[1] if full_page else height != viewport[1]):
                    raise ValueError('PNG dimensions must match viewport width and '
                                     'height (at least viewport height for fullPage)')
                dimensions.append((state['label'], viewport, full_page))
                images.append({'label': state['label'], 'width': width, 'height': height,
                               'viewport': viewport, 'fullPage': full_page,
                               'image': 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')})
                hashes.append(original_hash)
                displayed_hashes.append(hashlib.sha256(data).hexdigest())
            if expected is not None and dimensions != expected:
                raise ValueError('Candidates must have identical state labels, order, viewport '
                                 'dimensions and fullPage settings')
            expected = dimensions
            rendered.append({'label': label, 'states': images})
            mapping[label] = {'candidate': identity, 'sha256': hashes,
                              'displayedSha256': displayed_hashes}
        public.append({'key': key, 'title': title, 'candidates': rendered})
        reveal.append({'case': key, 'mapping': mapping})
    encoded = json.dumps(public, ensure_ascii=True).replace('<', '\\u003c')
    document = PAGE.replace('__COMPARISON_ID__', json.dumps(comparison_id)).replace('__DATA__', encoded)
    private = {'comparisonId': comparison_id, 'cases': reveal}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(document, encoding='utf-8')
    (output / 'reveal.json').write_text(json.dumps(private, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Created {len(public)} blinded comparisons: {output / "index.html"}')
    print('Keep reveal.json separate until review is complete. No preference has been collected.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.manifest, args.out)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(f'Not built: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
