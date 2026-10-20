// DOM behavior only. This does not check browser layout, native dialog behavior or taste.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const modulePath = process.env.RADAR_JSDOM_PATH || 'jsdom';
const {JSDOM, VirtualConsole} = require(modulePath);
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', error => errors.push(error.message));
const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const dom = new JSDOM(html, {
  runScripts: 'dangerously', url: 'http://localhost:8788/examples/project-radar/index.html?theme=dark',
  virtualConsole, pretendToBeVisual: true,
  beforeParse(window) {
    window.HTMLElement.prototype.scrollIntoView = function() {};
    window.HTMLDialogElement.prototype.showModal = function() { this.open = true; };
    window.HTMLDialogElement.prototype.close = function() { this.open = false; this.dispatchEvent(new window.Event('close')); };
  }
});
const {document, Event} = dom.window;
const $ = s => document.querySelector(s);
const all = s => [...document.querySelectorAll(s)];
const click = s => {assert.ok($(s),s);$(s).click();};
const snapshot = JSON.parse($('#snapshot').textContent);
const input = text => {$('#search').value=text;$('#search').dispatchEvent(new Event('input',{bubbles:true}));};
const checks = [];
function test(name, fn) { fn(); checks.push(name); console.log('PASS',name); }
test('1208 original records and three curated objects are present', () => {
  assert.equal(snapshot.projects.length,1208);assert.equal(all('.product-card').length,3);
  assert.equal(all('.result').length,12);assert.ok($('#result-count').textContent.includes('1,208'));
});
test('search finds the real Shaders record and renders escaped query text',()=>{
  input('shader-effects-inc/shaders');assert.equal(all('.result').length,1);assert.equal($('.result-title').textContent,'Shaders');
  input('<img src=x onerror=alert(1)>');assert.equal(all('#results img').length,0);assert.ok($('.empty'));click('[data-reset]');
});
test('payment filter uses checkout evidence rather than sales assumptions',()=>{
  click('[data-filter="payment"]');
  const count=snapshot.projects.filter(p=>p.mechanisms.some(m=>m.kind==='checkout_present')).length;
  assert.ok($('#result-count').textContent.startsWith(String(count)));assert.ok(all('.result-meta').every(x=>x.textContent.includes('采集到支付入口')));
});
test('commercial entry includes pricing, ads and donations without treating them as checkout',()=>{
  click('#commercial-start');
  const expected=snapshot.projects.filter(p=>p.mechanisms.some(m=>['checkout_present','pricing_present','ads_active','donation_present'].includes(m.kind)));
  assert.ok($('#result-count').textContent.startsWith(String(expected.length)));
  assert.equal(document.activeElement,$('#library-title'));
  const donationOnly=expected.find(p=>p.mechanisms.some(m=>m.kind==='donation_present')&&!p.mechanisms.some(m=>m.kind==='checkout_present'));
  input(donationOnly.originalName);assert.ok(all('#results [data-open]').some(b=>b.dataset.open===donationOnly.id));
  click('[data-filter="payment"]');assert.ok(!all('#results [data-open]').some(b=>b.dataset.open===donationOnly.id));click('#reset');
});
test('source and category filters intersect and reset pagination',()=>{
  click('[data-filter="github"]');$('#category').value='开发工具';$('#category').dispatchEvent(new Event('change'));
  const count=snapshot.projects.filter(p=>p.sources.includes('github')&&p.category==='开发工具').length;
  assert.ok($('#result-count').textContent.startsWith(String(count)));click('#reset');
});
test('pagination exposes additional records without unbounded lists',()=>{
  const first=$('.result-title').textContent;click('[data-page="next"]');assert.notEqual($('.result-title').textContent,first);assert.ok($('#pagination').textContent.includes('第 2 /'));click('#reset');
});
test('detail contains full original description, source and unknowns',()=>{
  click('#feature [data-open]');assert.equal($('#detail').open,true);assert.equal($('#detail-title').textContent,'Shaders');
  assert.ok($('#detail-content').textContent.includes('WebGPU components'));
  assert.ok($('#detail-content').textContent.includes('5,068'));assert.ok($('#detail-content').textContent.includes('是否有真实付费客户'));
  assert.ok($('#detail-content').textContent.includes('5,003 → 5,068'));
  assert.ok($('#detail-content').textContent.includes('stripe'));assert.ok($('#detail-content').textContent.includes('pricing page'));
  assert.ok($('#detail-content').textContent.includes('快照未保留具体命中页面'));
  assert.ok($('#detail-content a[href="https://shaders.com"]'));click('.close-detail');assert.equal($('#detail').open,false);
});
test('saving persists locally, saved filter finds it, removal returns empty state',()=>{
  click('#feature [data-save]');assert.equal($('#saved-count').textContent,'1');assert.equal(JSON.parse(dom.window.localStorage.getItem('radar-saved')).length,1);
  click('#nav-saved');assert.equal(all('.result').length,1);assert.equal($('.result-title').textContent,'Shaders');
  click('#results [data-save]');assert.ok($('.empty'));assert.equal($('#saved-count').textContent,'0');click('#reset');
});
test('theme toggles and methods are accessible actions',()=>{
  click('#theme');assert.equal(document.documentElement.dataset.theme,'light');assert.equal(dom.window.localStorage.getItem('radar-theme'),'light');
  click('#method-open');assert.ok($('#method').open);click('#method .close-method');assert.equal($('#method').open,false);
});
test('removing a saved object in its detail keeps feedback and a focus return target',()=>{
  click('#feature [data-save]');click('#nav-saved');click('#results [data-open]');
  click('#detail [data-save]');assert.ok($('#detail-status').textContent.includes('已取消收藏'));
  click('.close-detail');assert.equal(document.activeElement,$('#library-title'));click('#reset');
});
test('pagination moves keyboard focus into the newly rendered results',()=>{
  click('[data-page="next"]');assert.equal(document.activeElement,$('#results'));click('#reset');
});
test('dataset URLs parse and content has no unexpected script errors',()=>{
  snapshot.projects.forEach(p=>p.urls.forEach(u=>assert.ok(['http:','https:'].includes(new URL(u).protocol))));
  assert.deepEqual(errors,[]);
});
console.log(JSON.stringify({scope:'DOM only; dialogs and scrolling shimmed; no visual validation',passed:checks.length}));
dom.window.close();
