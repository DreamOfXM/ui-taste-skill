(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('snapshot').textContent);
  const projects = data.projects;
  const byId = new Map(projects.map(p => [p.id, p]));
  const $ = selector => document.querySelector(selector);
  const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sourceNames = {github:'GitHub',hackernews:'Hacker News',producthunt:'Product Hunt',appstore:'App Store',devto:'dev.to',huggingface_model:'Hugging Face',huggingface_space:'Hugging Face',umbrella:'种子目录'};
  const sourceText = p => p.sources.map(s => sourceNames[s] || s).join(' · ') || '来源待补充';
  const hasPayment = p => p.mechanisms.some(m => m.kind === 'checkout_present');
  const statusText = p => hasPayment(p) ? '采集到支付入口' : ({not_checked:'尚未探测',unknown_incomplete:'探测不完整',checked_no_evidence:'未发现收费证据',positive_evidence:'有其他商业线索'}[p.moneyStatus] || '收费状态待核实');
  const bookmark = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h12v17l-6-4-6 4Z"/></svg>';
  let saved;
  try { const values = JSON.parse(localStorage.getItem('radar-saved') || '[]'); saved = new Set(Array.isArray(values) ? values.filter(id => byId.has(id)) : []); } catch { saved = new Set(); }
  const state = {query:'', filter:'all', category:'all', page:1};
  const size = 12;
  let toastTimer;
  function toast(message) { if($('#detail').open){$('#detail-status').textContent=message;return;} $('#toast').textContent = message; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('show'), 2800); }
  function saveButton(p, extra = '', text = false) {
    return `<button class="save-button ${extra}" data-save="${esc(p.id)}" aria-pressed="${saved.has(p.id)}" aria-label="${saved.has(p.id)?'取消收藏':'收藏'} ${esc(p.name)}">${bookmark}${text?'<span class="save-text">'+(saved.has(p.id)?'已收藏':'收藏项目')+'</span>':''}</button>`;
  }
  function syncSaved() {
    $('#saved-count').textContent = saved.size;
    document.querySelectorAll('[data-save]').forEach(b => { const p=byId.get(b.dataset.save); const active=saved.has(p.id); b.setAttribute('aria-pressed',String(active)); b.setAttribute('aria-label',`${active?'取消收藏':'收藏'} ${p.name}`); const text=b.querySelector('.save-text'); if(text) text.textContent=active?'已收藏':'收藏项目'; });
  }
  function toggleSave(id) {
    if (saved.has(id)) saved.delete(id); else saved.add(id);
    let persisted=true; try { localStorage.setItem('radar-saved',JSON.stringify([...saved])); } catch { persisted=false; }
    syncSaved();
    if(state.filter==='saved') renderResults();
    toast(persisted?(saved.has(id)?'已收藏，可在“我的收藏”中继续查看':'已取消收藏'):'浏览器未允许保存，收藏仅在本次页面有效');
  }
  function shaderArt() {
    let paths='';
    for(let i=0;i<63;i++) {
      let d='';
      for(let x=260;x<=900;x+=7) {
        const y=205+(i-31)*4.8+Math.sin(x/105+i*.045)*67+Math.cos(x/58+i*.065)*25;
        d+=(x===260?'M':'L')+x.toFixed(1)+' '+y.toFixed(1)+' ';
      }
      paths+=`<path d="${d}" stroke="hsl(${105+i*.9} 34% ${43+i*.38}%)" opacity="${.5+i*.007}"/>`;
    }
    return `<svg viewBox="0 0 850 380" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${paths}</svg>`;
  }
  function art(kind) {
    if(kind==='shader') return shaderArt();
    if(kind==='atelier') return '<svg viewBox="0 0 220 110" aria-hidden="true"><rect x="40" y="17" width="140" height="78" rx="8" opacity=".5"/><path d="M40 37h140M85 38v56" opacity=".35"/><circle cx="51" cy="27" r="1.5"/><circle cx="58" cy="27" r="1.5"/><path d="M51 50h21m-21 11h17m27-11h64m-64 12h43m-43 12h54" opacity=".55"/><path d="m151 79 5 6 13-15" stroke-width="2"/></svg>';
    if(kind==='crew'||kind==='standup') return '<svg viewBox="0 0 220 110" aria-hidden="true"><path d="M36 34h148M75 34v12q0 10 10 10h50q10 0 10-10V34" stroke-width="2"/><circle cx="92" cy="45" r="3"/><circle cx="110" cy="45" r="3"/><circle cx="128" cy="45" r="3"/><path d="M110 66v14m-30 0h60" opacity=".4"/><circle cx="80" cy="85" r="6" opacity=".6"/><circle cx="110" cy="85" r="6" opacity=".6"/><circle cx="140" cy="85" r="6" opacity=".6"/></svg>';
    return '<svg viewBox="0 0 220 110" aria-hidden="true"><rect x="45" y="19" width="130" height="76" rx="5" opacity=".6"/><path d="M45 34h130M57 47h40m-40 8h27m-27 8h31m-31 16h27" opacity=".6"/><rect x="111" y="46" width="51" height="35" rx="3" opacity=".4"/><path d="m125 56-6 7 6 7m23-14 6 7-6 7m-10-17-4 21" stroke-width="2"/></svg>';
  }
  const feature=projects.find(p=>p.art==='shader') || projects[0];
  $('#feature').innerHTML=`<div class="feature-art">${shaderArt()}</div><div class="feature-content"><p class="eyebrow">本期关注 <span>／ ${esc(feature.category)}</span></p><h2>${esc(feature.name)}</h2><h3>${esc(feature.headline)}</h3><p class="feature-description">${esc(feature.description)}</p><div class="feature-actions"><button class="primary" data-open="${esc(feature.id)}">打开项目观察 <span>↗</span></button>${saveButton(feature,'icon-button feature-save')}</div></div><span class="art-caption">WebGPU 视觉语言 · 概念示意</span>`;
  const picks=['atelier','standup','themes'].map(key=>projects.find(p=>p.art===key)).filter(Boolean);
  $('#curated-grid').innerHTML=picks.map(p=>`<article class="product-card"><div class="card-art art-${p.art}">${art(p.art)}</div><div class="card-body"><div class="card-top"><h3><button data-open="${esc(p.id)}">${esc(p.name)}</button></h3>${saveButton(p,'icon-button card-save')}</div><p class="card-description">${esc(p.description)}</p><div class="card-meta"><span><i class="tiny-dot"></i>${esc(p.category)}</span><span>${esc(statusText(p))}</span></div></div></article>`).join('');
  $('#total-count').textContent=projects.length.toLocaleString('en-US');
  const categories=[...new Set(projects.map(p=>p.category))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
  $('#category').innerHTML+=[...categories].map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  function matches(p) {
    if(state.filter==='payment'&&!hasPayment(p)) return false;
    if(state.filter==='github'&&!p.sources.includes('github')) return false;
    if(state.filter==='saved'&&!saved.has(p.id)) return false;
    if(state.category!=='all'&&p.category!==state.category) return false;
    const haystack=[p.name,p.originalName,p.description,p.originalDescription,p.category].join(' ').toLocaleLowerCase();
    return state.query.toLocaleLowerCase().trim().split(/\s+/).every(word=>haystack.includes(word));
  }
  function metricLabel(p) {
    if(p.metrics.github_stars!=null) return Number(p.metrics.github_stars).toLocaleString('en-US')+' GitHub stars';
    if(p.metrics.hn_points!=null) return p.metrics.hn_points+' HN points';
    if(p.metrics.hf_downloads!=null) return Number(p.metrics.hf_downloads).toLocaleString('en-US')+' 下载/月';
    return sourceText(p);
  }
  function renderResults() {
    const list=projects.filter(matches);
    const pages=Math.max(1,Math.ceil(list.length/size)); state.page=Math.min(state.page,pages);
    document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter)));
    $('#result-count').textContent=`${list.length.toLocaleString('en-US')} 个项目${state.query?' · 搜索“'+state.query+'”':''}`;
    const slice=list.slice((state.page-1)*size,state.page*size);
    $('#results').innerHTML=slice.length?slice.map(p=>`<article class="result"><div class="initial" aria-hidden="true">${esc(p.name.replace(/[^\p{L}\p{N}]/gu,'').slice(0,1).toUpperCase()||'·')}</div><div class="result-main"><button class="result-title" data-open="${esc(p.id)}">${esc(p.name)}</button><p>${esc(p.description||'当前采集记录没有用途介绍，可打开来源继续了解。')}</p><div class="result-meta"><span>${esc(metricLabel(p))}</span><span>${esc(statusText(p))}</span></div></div>${saveButton(p,'icon-button card-save')}</article>`).join(''):`<div class="empty"><h3>${state.filter==='saved'?'这里还没有匹配的收藏':'没有找到匹配的项目'}</h3><p>试试更短的关键词，或清除当前筛选。</p><button class="primary" data-reset>浏览全部项目</button></div>`;
    $('#pagination').innerHTML=list.length?`<button data-page="prev" ${state.page===1?'disabled':''}>← 上一页</button><span>第 ${state.page} / ${pages} 页</span><button data-page="next" ${state.page===pages?'disabled':''}>下一页 →</button>`:'';
    syncSaved();
  }
  function reset() {state.query='';state.filter='all';state.category='all';state.page=1;$('#search').value='';$('#category').value='all';renderResults();}
  const labels={github_stars:'GitHub stars',github_forks:'GitHub forks',hn_points:'HN points',hn_comments:'HN 评论',hf_downloads:'下载/月',hf_likes:'HF likes',traffic_rank:'来源中的排名',appstore_paid_rank_us:'美国付费榜名次',appstore_paid_rank_cn:'中国付费榜名次',npm_downloads_month:'npm 下载/月',pypi_downloads_month:'PyPI 下载/月'};
  let detailTrigger=null, detailId=null;
  function openDetail(id,trigger) {
    const p=byId.get(id); if(!p)return;
    detailTrigger=trigger;
    detailId=id;$('#detail-status').textContent='';
    const metrics=Object.entries(p.metrics).filter(([key])=>labels[key]).map(([key,value])=>`<div class="evidence-row"><span>${labels[key]}</span><strong>${Number(value).toLocaleString('en-US')}</strong></div>`).join('');
    const paymentLabels=[...new Set(p.mechanisms.filter(m=>m.kind==='checkout_present').map(m=>m.label))].join(' · ');
    const seed=p.sources.length===1&&p.sources[0]==='umbrella';
    const note=p.note||'先了解产品的实际用途，再核对来源中的关注指标和收费机制。当前记录不包含客户交易或收入数据。';
    $('#detail-kicker').textContent=p.category+' / 项目观察';
    $('#detail-content').innerHTML=`<div class="detail-grid"><div class="detail-main">${p.art?`<div class="detail-art">${art(p.art)}</div><p class="eyebrow">编辑概念示意 · 非产品截图</p>`:''}<h2 id="detail-title">${esc(p.name)}</h2><p>${esc(p.description||'当前采集记录没有用途介绍。')}</p><details class="original-copy"><summary>查看原始项目名称与简介</summary><p>${esc(p.originalName)}</p><p>${esc(p.originalDescription||'无原始简介')}</p></details><div class="detail-actions">${p.urls[0]?`<a class="primary" href="${esc(p.urls[0])}" target="_blank" rel="noopener noreferrer">打开来源 <span>↗</span></a>`:''}${saveButton(p,'',true)}</div><p class="detail-date">采集于 ${esc((p.lastSeen||data.generatedAt).replace('T',' ').slice(0,16))} UTC<br>记录来源：${esc(sourceText(p))}</p></div><div class="detail-evidence"><section class="detail-section"><h3>为什么放进观察清单</h3><p>${esc(note)}</p></section><section class="detail-section"><h3>目前有哪些证据</h3>${metrics||'<p>尚无可展示的独立公开关注指标。</p>'}<div class="evidence-row"><span>收费线索</span><strong>${esc(statusText(p))}</strong></div>${paymentLabels?`<div class="evidence-row"><span>记录命中的机制</span><strong>${esc(paymentLabels)}</strong></div>`:''}<p class="evidence-note">${seed?'此排名仅来自种子目录，不能作为独立流量或需求证据。':'公开关注指标和支付入口各有含义，不能合并成收入结论。'}</p>${hasPayment(p)?'<p class="evidence-note">支付标签来自采集记录，快照未保留具体命中页面或摘录，尚待复核。下方链接是项目来源。</p>':''}</section><section class="detail-unknown"><h3>还不知道的事</h3><p>是否有真实付费客户、收入规模与持续使用情况。本页没有验证这些信息。支付入口也需要回到原站确认。</p></section>${p.urls.map((url,i)=>`<a class="source-link" target="_blank" rel="noopener noreferrer" href="${esc(url)}">来源 ${i+1} · ${esc(new URL(url).hostname)} ↗</a>`).join('')}</div></div>`;
    $('#detail').showModal();
    $('.close-detail').focus();
  }
  function methodOpen(){ $('#method').showModal();$('.close-method').focus(); }
  $('#detail').addEventListener('close',()=>{ const replacement=allOpenButtons().find(b=>b.dataset.open===detailId&&b.closest('#results')); (detailTrigger?.isConnected?detailTrigger:replacement||$('#library-title')).focus(); });
  function allOpenButtons(){return [...document.querySelectorAll('[data-open]')];}
  document.addEventListener('click',e=>{
    const save=e.target.closest('[data-save]');if(save){toggleSave(save.dataset.save);return;}
    const open=e.target.closest('[data-open]');if(open){openDetail(open.dataset.open,open);return;}
    const filter=e.target.closest('[data-filter]');if(filter){state.filter=filter.dataset.filter;state.page=1;renderResults();return;}
    const page=e.target.closest('[data-page]');if(page&&!page.disabled){state.page+=page.dataset.page==='next'?1:-1;renderResults();$('#results').scrollIntoView({block:'start'});$('#results').focus({preventScroll:true});return;}
    if(e.target.closest('[data-reset]'))reset();
    if(e.target.closest('.close-detail'))$('#detail').close();
    if(e.target.closest('.close-method'))$('#method').close();
  });
  $('#search').addEventListener('input',e=>{state.query=e.target.value;state.page=1;renderResults();});
  $('#category').addEventListener('change',e=>{state.category=e.target.value;state.page=1;renderResults();});
  $('#reset').onclick=reset;
  $('#nav-saved').onclick=()=>{reset();state.filter='saved';renderResults();$('#library').scrollIntoView({block:'start'});};
  ['#method-open','#note-method','#footer-method'].forEach(selector=>$(selector).onclick=methodOpen);
  for(const dialog of [$('#detail'),$('#method')]) dialog.addEventListener('click',e=>{if(e.target!==dialog)return;const rect=dialog.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)dialog.close();});
  let theme='dark'; try {theme=localStorage.getItem('radar-theme')||theme;}catch{}
  const requested=new URLSearchParams(location.search).get('theme'); if(['dark','light'].includes(requested))theme=requested;
  function applyTheme(){document.documentElement.dataset.theme=theme;$('#theme').setAttribute('aria-label',theme==='dark'?'切换浅色主题':'切换深色主题');}
  applyTheme();$('#theme').onclick=()=>{theme=theme==='dark'?'light':'dark';applyTheme();try{localStorage.setItem('radar-theme',theme);}catch{}};
  renderResults();
})();
