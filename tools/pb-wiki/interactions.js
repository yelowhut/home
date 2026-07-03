"use strict";
// ---- comparison ----
function toggleCmp(key){state.cmp.has(key)?state.cmp.delete(key):state.cmp.add(key);updateCmp();writeURL();syncSel();
  document.querySelectorAll(`[data-cmp="${CSS.escape(key)}"]`).forEach(b=>b.textContent=state.cmp.has(key)?'✓':'');}
function updateCmp(){const bar=document.getElementById('cmpbar');bar.classList.toggle('show',state.cmp.size>0);
  document.getElementById('cmpits').innerHTML=[...state.cmp].map(k=>{const i=D.items.find(x=>x.key===k);
    return i?`<span class="ci">${esc(i.name)} <b data-x="${k}">×</b></span>`:'';}).join('');}
document.getElementById('cmpits').addEventListener('click',e=>{if(e.target.dataset.x)toggleCmp(e.target.dataset.x);});
document.getElementById('cmpclr').onclick=()=>{state.cmp.clear();updateCmp();writeURL();syncSel();document.querySelectorAll('[data-cmp]').forEach(b=>b.textContent='');};
document.getElementById('cmpgo').onclick=()=>{
  const items=[...state.cmp].map(k=>D.items.find(x=>x.key===k)).filter(Boolean);
  if(items.length<2){alert('Выберите минимум 2 предмета.');return;}
  const keys=[...new Set(items.flatMap(i=>Object.keys(i.stats)))].filter(k=>!HIDE.has(k)).sort((a,b)=>((SM[b]||{}).priority||0)-((SM[a]||{}).priority||0));
  let h=`<h2>Сравнение — ${items.length} ${plural(items.length,'предмет','предмета','предметов')}</h2><table class="ct"><thead><tr><th>Характеристика</th>${items.map(i=>`<th>${esc(i.name)}</th>`).join('')}</tr></thead><tbody>`;
  keys.forEach(k=>{const vals=items.map(i=>i.stats[k]);const nums=vals.filter(v=>v!=null);
    const inv=LOWER_BETTER.has(k);const best=inv?Math.min(...nums):Math.max(...nums);const worst=inv?Math.max(...nums):Math.min(...nums);
    h+=`<tr><td>${statName(k)}</td>${vals.map(v=>v==null?'<td style="color:var(--dim2)">—</td>':`<td class="${nums.length>1&&v===best?'best':(nums.length>1&&v===worst?'worst':'')}">${fmtStat(k,v)}</td>`).join('')}</tr>`;});
  h+=`</tbody></table><p class="note">Зелёным — лучшее в строке, красным — худшее (для массы/тепла/разброса «лучше» = меньше). Уровень = 1.</p>`;
  document.getElementById('mbox').innerHTML=h;document.getElementById('modal').classList.add('open');
};
document.getElementById('modal').onclick=e=>{if(e.target.id==='modal')e.currentTarget.classList.remove('open');};

// ---- tooltip ----
const tip=document.getElementById('tip');
document.getElementById('scroll').addEventListener('mouseover',e=>{
  const r=e.target.closest('[data-key]');if(!r||e.target.closest('[data-cmp]'))return;
  const src=state.tab==='mods'?D.modules:D.items;const i=src.find(x=>x.key===r.dataset.key);if(!i)return;
  const stats=(state.tab==='mods'?Object.keys(i.stats):activeColumns([i])).filter(k=>i.stats[k]!=null&&!HIDE.has(k)).slice(0,6);
  tip.innerHTML=`<h5>${esc(i.name)}</h5><div class="k">${esc(i._typeLabel||i.slots&&i.slots.map(SLOTLBL).join(', ')||'')}${i.setName?' · '+esc(i.setName):''}</div>
    ${stats.map(k=>`<div class="tr"><span>${statName(k)}</span><b>${fmtStat(k,i.stats[k])}</b></div>`).join('')}
    ${i.desc?`<div class="td">${esc(i.desc)}</div>`:''}`;
  tip.style.display='block';
});
document.getElementById('scroll').addEventListener('mousemove',e=>{
  if(tip.style.display!=='block')return;const pad=16;let x=e.clientX+pad,y=e.clientY+pad;
  const r=tip.getBoundingClientRect();if(x+r.width>innerWidth)x=e.clientX-r.width-pad;if(y+r.height>innerHeight)y=e.clientY-r.height-pad;
  tip.style.left=x+'px';tip.style.top=y+'px';});
document.getElementById('scroll').addEventListener('mouseout',e=>{if(!e.relatedTarget||!e.relatedTarget.closest('[data-key]'))tip.style.display='none';});

// ---- tabs / view / search ----
function setTab(t){state.tab=t;document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===t));
  closeDetail();buildFilters();render();writeURL();}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>setTab(t.dataset.tab));
function setView(v){state.view=v;document.querySelectorAll('.viewtoggle button').forEach(b=>b.classList.toggle('on',b.dataset.view===v));render();writeURL();}
document.querySelectorAll('.viewtoggle button').forEach(b=>b.onclick=()=>setView(b.dataset.view));
let qt;document.getElementById('q').oninput=e=>{clearTimeout(qt);qt=setTimeout(()=>{state.q=e.target.value.toLowerCase().trim();render();writeURL();if(state.tab==='items')buildCountsOnly();},130);};
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement.id!=='q'){e.preventDefault();document.getElementById('q').focus();}
  if(e.key==='Escape'){if(document.getElementById('modal').classList.contains('open'))document.getElementById('modal').classList.remove('open');
    else if(state.open)closeDetail();else{document.getElementById('q').blur();}}
});
window.addEventListener('popstate',()=>{readURL();applyURL();});

// ---- boot ----
function applyURL(){
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===state.tab));
  document.querySelectorAll('.viewtoggle button').forEach(b=>b.classList.toggle('on',b.dataset.view===state.view));
  document.getElementById('q').value=state.q;
  buildFilters();updateCmp();render();
  if(state.open){const src=state.tab==='mods'?D.modules:D.items;const it=src.find(x=>x.key===state.open);
    if(it){openPanel();state.tab==='mods'?openModRaw(it):renderDetail(it);}}
  else closePanel();
}
function openModRaw(m){state.open=m.key;openMod(m.key);} // reuse
readURL();applyURL();
