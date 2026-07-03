"use strict";
// ---- filters UI ----
function buildFilters(){
  const el=document.getElementById('filters');
  if(state.tab==='mods'){
    const slots={};D.modules.forEach(m=>m.slots.forEach(s=>slots[s]=true));
    el.innerHTML=fgroup('slot','Слот модуля',Object.keys(slots).map(k=>optHTML('modslot',k,SLOTLBL(k),null,
      D.modules.filter(m=>m.slots.includes(k)).length)))+resetBtn();
    return;
  }
  let h='';
  h+=fgroup('slot','Тип',Object.entries(D.slots).map(([k,v])=>optHTML('slot',k,v,null,facetCount('slot',k))));
  h+=fgroup('set','Набор',Object.entries(D.sets).map(([k,v])=>optHTML('set',k,v,null,facetCount('set',k))).filter((_,idx)=>true));
  h+=fgroup('weight','Вес',Object.entries(D.weights).map(([k,v])=>optHTML('weight',k,v,null,facetCount('weight',k))));
  h+=fgroup('cat','Категория',Object.keys(CATS).sort((a,b)=>a.localeCompare(b,'ru')).map(v=>optHTML('cat',v,v,CATS[v],facetCount('cat',v))));
  h+=fgroup('mnf','Производитель',Object.entries(MNFS).sort((a,b)=>a[1].localeCompare(b[1],'ru')).map(([k,v])=>optHTML('mnf',k,v,null,facetCount('mnf',k))));
  h+=fgroup('rng','Диапазоны',RANGES.map(r=>rangeHTML(r.k)).join(''),true);
  el.innerHTML=h+resetBtn();
  bindRanges();
}
const COLLAPSED=new Set();
function fgroup(id,title,opts,raw){
  const body=Array.isArray(opts)?opts.join(''):opts;
  return `<div class="fg ${COLLAPSED.has(id)?'collapsed':''}" data-fg="${id}"><h3>${title}<span class="arw">▼</span></h3><div class="body">${body}</div></div>`;
}
function optHTML(dim,key,label,ic,cnt){
  const on=(dim==='modslot'?state.modslot:state.f[dim]).has(key);
  return `<div class="opt ${on?'on':''} ${cnt===0&&!on?'zero':''}" data-dim="${dim}" data-key="${esc(key)}">
    <span class="box">${on?'✓':''}</span>${ic&&IC[ic]?`<img class="ic" src="${IC[ic]}">`:''}
    <span class="lbl">${esc(label)}</span><span class="cnt">${cnt}</span></div>`;
}
function rangeHTML(k){
  const b=BOUNDS[k]||{min:0,max:100};const lo=Math.floor(b.min),hi=Math.ceil(b.max);
  const cur=state.r[k]||[lo,hi];
  return `<div class="range" data-r="${k}"><div class="rl"><span>${esc(SM[k].name)}</span><b><span class="lv">${cur[0]}</span>–<span class="hv">${cur[1]}</span></b></div>
   <div class="dual"><div class="track"></div><div class="fill"></div>
     <input type="range" class="lo" min="${lo}" max="${hi}" value="${cur[0]}">
     <input type="range" class="hi" min="${lo}" max="${hi}" value="${cur[1]}"></div></div>`;
}
function bindRanges(){
  document.querySelectorAll('.range').forEach(rg=>{
    const k=rg.dataset.r,b=BOUNDS[k],lo=Math.floor(b.min),hi=Math.ceil(b.max);
    const iLo=rg.querySelector('.lo'),iHi=rg.querySelector('.hi'),fill=rg.querySelector('.fill');
    const upd=(commit)=>{let a=+iLo.value,c=+iHi.value;if(a>c){[a,c]=[c,a];}
      rg.querySelector('.lv').textContent=a;rg.querySelector('.hv').textContent=c;
      const span=hi-lo||1;fill.style.left=((a-lo)/span*100)+'%';fill.style.right=(100-(c-lo)/span*100)+'%';fill.style.width='auto';
      if(commit){if(a<=lo&&c>=hi)delete state.r[k];else state.r[k]=[a,c];render();writeURL();buildCountsOnly();}};
    iLo.oninput=()=>upd(false);iHi.oninput=()=>upd(false);
    iLo.onchange=()=>upd(true);iHi.onchange=()=>upd(true);
    upd(false);
  });
}
function buildCountsOnly(){ // refresh facet counts without losing slider drag focus
  document.querySelectorAll('.opt').forEach(o=>{const d=o.dataset.dim,k=o.dataset.key;if(d==='modslot')return;
    const c=facetCount(d,k);o.querySelector('.cnt').textContent=c;
    o.classList.toggle('zero',c===0&&!o.classList.contains('on'));});
}
function resetBtn(){return `<button class="reset" onclick="resetFilters()">Сбросить фильтры</button>`;}
function resetFilters(){for(const d in state.f)state.f[d].clear();state.r={};state.modslot.clear();state.q='';document.getElementById('q').value='';buildFilters();render();writeURL();}

document.getElementById('filters').addEventListener('click',e=>{
  const h=e.target.closest('h3');
  if(h){const id=h.parentElement.dataset.fg;COLLAPSED.has(id)?COLLAPSED.delete(id):COLLAPSED.add(id);h.parentElement.classList.toggle('collapsed');return;}
  const o=e.target.closest('.opt');if(!o)return;
  const dim=o.dataset.dim,key=o.dataset.key;
  const set=dim==='modslot'?state.modslot:state.f[dim];
  set.has(key)?set.delete(key):set.add(key);
  buildFilters();render();writeURL();
});

// ---- columns ----
const COL_WEAPON=['wpn_damage','wpn_impact','wpn_range_max','act_heat','mass'];
const COL_ARMOR=['hp','barrier','heat_dissipation','mass'];
const COL_BACK=['mass','heat_dissipation'];
function activeColumns(list){
  const c={weapon:0,armor:0,back:0};
  list.forEach(i=>{if(i.slot==='main_weapon'||i.slot==='secondary_weapon')c.weapon++;
    else if(i.slot==='back')c.back++;else c.armor++;});
  let stats;
  if(c.weapon>=c.armor&&c.weapon>=c.back)stats=COL_WEAPON;
  else if(c.armor>=c.back)stats=COL_ARMOR;
  else stats=COL_BACK;
  // if genuinely mixed, blend key stats
  if(c.weapon&&c.armor)stats=['wpn_damage','hp','barrier','act_heat','mass'];
  return stats;
}

