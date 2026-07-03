"use strict";
// ---- detail ----
function openPanel(){document.getElementById('detail').classList.add('open');document.body.classList.add('detail-open');}
function closePanel(){document.getElementById('detail').classList.remove('open');document.body.classList.remove('detail-open');}
function openItem(key){const i=D.items.find(x=>x.key===key);if(!i)return;
  state.open=key;state.level=1;state.rarity=1;renderDetail(i);openPanel();writeURL(true);syncSel();}
function closeDetail(){state.open=null;closePanel();writeURL();syncSel();}
function syncSel(){document.querySelectorAll('tr[data-key],.card[data-key]').forEach(r=>{
  r.classList.toggle('sel',state.cmp.has(r.dataset.key));
  if(r.tagName==='TR')r.classList.toggle('sel',state.cmp.has(r.dataset.key));});
  document.querySelectorAll('[data-key]').forEach(r=>{if(r.dataset.key===state.open)r.style.background='var(--rowhov)';});}
function renderDetail(i){
  const scale=new Set(D.levelScaling.stats);
  const keys=Object.keys(i.stats).filter(k=>!HIDE.has(k)).sort((a,b)=>((SM[b]||{}).priority||0)-((SM[a]||{}).priority||0));
  const isArmor=['torso','legs','arm'].includes(i.slot);
  const d=document.getElementById('detail');
  d.innerHTML=`<div class="dhead">${icon(i.catIcon)}<div><h2>${esc(i.name)}</h2><div class="k">${esc(i.key)}${i.nameEn?' · '+esc(i.nameEn):''}</div></div><button class="dx" onclick="closeDetail()">×</button></div>
   <div class="dbody">${i.desc?`<p class="desc">${esc(i.desc)}</p>`:''}
    <div class="lvlbox"><div class="lr"><span>Уровень предмета</span><span class="lvn" id="lvn">1</span></div>
      <input type="range" id="lvl" min="1" max="${D.levelScaling.limit}" value="1">
      <div class="lr"><span>ур.1 (база)</span><span>макс. ${D.levelScaling.limit}</span></div>
      <div class="note">Масштабирует только: ${D.levelScaling.stats.map(statName).join(', ')} (+${D.levelScaling.increase*100}%/ур., линейно).</div>
      <div class="rar"><button data-r="1" class="on">Обычное</button><button data-r="2">Необычное</button><button data-r="3">Редкое</button></div></div>
    <div class="sec"><h4>Характеристики</h4><div id="statlist"></div>
      ${isArmor?'<div class="note">Для брони барьер/HP/масса — доля от запаса набора (как в файлах игры).</div>':''}</div>
    ${i.moduleSlots&&i.moduleSlots.length?`<div class="sec"><h4>Слоты модификаций</h4><div id="slotlist"></div><div class="note">Цвет = мин. редкость, при которой слот доступен.</div></div>`:''}
    ${i.subsystems&&i.subsystems.length?`<div class="sec"><h4>Состав</h4>${i.subsystems.map(s=>`<div class="subp"><span>${esc(s.name)}</span><span>${esc(s.hardpoint)}</span></div>`).join('')}</div>`:''}
    ${i.specs&&i.specs.length?`<div class="sec"><h4>Особенности</h4><div class="bl">${i.specs.map(s=>`<span class="b">${esc(s.name)}</span>`).join('')}</div></div>`:''}</div>`;
  const lvl=d.querySelector('#lvl');lvl.oninput=()=>{state.level=+lvl.value;d.querySelector('#lvn').textContent=lvl.value;drawStats(i);};
  d.querySelectorAll('.rar button').forEach(b=>b.onclick=()=>{state.rarity=+b.dataset.r;
    d.querySelectorAll('.rar button').forEach(x=>x.classList.toggle('on',x===b));drawSlots(i);});
  drawStats(i);drawSlots(i);
}
function drawStats(i){const box=document.getElementById('statlist');if(!box)return;
  const scale=new Set(D.levelScaling.stats);
  const keys=Object.keys(i.stats).filter(k=>!HIDE.has(k)).sort((a,b)=>((SM[b]||{}).priority||0)-((SM[a]||{}).priority||0));
  box.innerHTML=keys.map(k=>{const up=scale.has(k)&&state.level>1;const si=statIcon(k);
    const w=Math.min(100,Math.abs(i.stats[k]*(up?(1+0.25*(state.level-1)):1))/barMax(k)*100);
    return `<div class="srow ${up?'up':''}">${si&&IC[si]?`<img class="si" src="${IC[si]}">`:'<span class="si"></span>'}
      <span class="snm">${statName(k)}</span><span class="sv">${fmtStat(k,i.stats[k],state.level)}${up?' ↑':''}</span>
      <span class="sbar" style="width:${w}%;background:${statColor(k)}"></span></div>`;}).join('');
}
function drawSlots(i){const box=document.getElementById('slotlist');if(!box)return;
  box.innerHTML=(i.moduleSlots||[]).map(s=>{const r=Math.max(1,s.ratingMin);const col=RARC[r];const avail=r<=state.rarity;
    return `<div class="slot ${avail?'':'locked'}"><span class="dot" style="background:${col}"></span>
      <span class="snm">${SLOTLBL(s.hardpoint)}${s.default?` · <span style="color:var(--dim2)">${esc(s.default.name)}</span>`:''}</span>
      <span class="tg" style="background:${col}">${r>1?RARN[r]:'база'}</span></div>`;}).join('');
}

// ---- modules ----
function renderMods(){
  const c=document.getElementById('chips');
  let fam={};D.modules.forEach(m=>{if(state.q&&!m._search.includes(state.q))return;
    if(state.modslot.size&&!m.slots.some(s=>state.modslot.has(s)))return;(fam[m.family]=fam[m.family]||[]).push(m);});
  const fams=Object.values(fam).sort((a,b)=>a[0].name.localeCompare(b[0].name,'ru'));
  c.innerHTML=`<span class="lead">Модификации — вставляются в слоты снаряжения</span>`+
    (state.modslot.size?`<button class="clearall" onclick="resetFilters()">Сбросить</button>`:'')+
    `<span class="count">${fams.length} ${plural(fams.length,'семейство','семейства','семейств')}</span>`;
  const sc=document.getElementById('scroll');
  if(!fams.length){sc.innerHTML=`<div class="empty">Ничего не найдено</div>`;return;}
  sc.innerHTML=`<div class="grid">`+fams.map(ms=>{const m=ms[0];
    const eff=Object.keys(m.stats).filter(k=>!HIDE.has(k)).slice(0,4);
    const tiers=ms.slice().sort((a,b)=>(a.tier>b.tier?1:-1)).map(x=>x.tier?x.tier.toUpperCase():'·');
    return `<div class="card" data-key="${m.key}"><div class="top">${icon('s_icon_l32_part_arch_all')}
      <div style="flex:1"><div class="nm">${esc(m.name)}</div><div class="sub">${ms[0].slots.map(SLOTLBL).join(', ')}</div></div></div>
      <div class="bl">${tiers.map(t=>`<span class="b">${t}</span>`).join('')}</div>
      <div class="cstat">${eff.map(k=>`<div class="r"><span>${statName(k)}</span><b class="tnum">${fmtStat(k,m.stats[k])}</b></div>`).join('')}</div></div>`;}).join('')+`</div>`;
}
function openMod(key){const m=D.modules.find(x=>x.key===key);if(!m)return;
  const fam=D.modules.filter(x=>x.family===m.family).sort((a,b)=>(a.tier>b.tier?1:-1));
  const d=document.getElementById('detail');
  d.innerHTML=`<div class="dhead">${icon('s_icon_l32_part_arch_all')}<div><h2>${esc(m.name)}</h2><div class="k">${esc(m.family)} · ${m.slots.map(SLOTLBL).join(', ')}</div></div><button class="dx" onclick="closeDetail()">×</button></div>
   <div class="dbody">${m.desc?`<p class="desc">${esc(m.desc)}</p>`:''}
    ${fam.map(x=>`<div class="sec"><h4>${x.tier?'Тир '+x.tier.toUpperCase():'Базовый'}</h4>
      ${Object.keys(x.stats).filter(k=>!HIDE.has(k)).map(k=>`<div class="srow"><span class="snm">${statName(k)}</span><span class="sv">${fmtStat(k,x.stats[k])}</span></div>`).join('')||'<div class="note">нет числовых эффектов</div>'}</div>`).join('')}</div>`;
  state.open=key;openPanel();writeURL(true);
}

