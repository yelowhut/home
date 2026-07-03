"use strict";
// ---- render ----
function getList(){
  let l=D.items.filter(i=>matchItem(i));
  const {key,dir}=state.sort;
  if(key==='name')l.sort((a,b)=>a.name.localeCompare(b.name,'ru')*dir);
  else if(['_typeLabel','setName','_weightLabel','_mnf'].includes(key))
    l.sort((a,b)=>((a[key]||'')+'').localeCompare((b[key]||'')+'','ru')*dir);
  else l.sort((a,b)=>{const av=a.stats[key],bv=b.stats[key];
    if(av==null&&bv==null)return 0;if(av==null)return 1;if(bv==null)return -1;return(av-bv)*dir;});
  return l;
}
function render(){
  if(state.tab==='mods')return renderMods();
  const list=getList();
  renderChips(list.length);
  const sc=document.getElementById('scroll');
  if(!list.length){sc.innerHTML=`<div class="empty">Ничего не найдено<button onclick="resetFilters()">Сбросить фильтры</button></div>`;return;}
  sc.innerHTML=state.view==='table'?tableHTML(list):cardsHTML(list);
  syncSel();
}
function renderChips(n){
  const c=document.getElementById('chips');let chips=[];
  const LBL={slot:'Тип',set:'Набор',weight:'Вес',cat:'Категория',mnf:'Произв.'};
  const NAME={slot:k=>D.slots[k],set:k=>D.sets[k],weight:k=>D.weights[k],cat:k=>k,mnf:k=>MNFS[k]};
  for(const d in state.f)for(const k of state.f[d])chips.push({d,k,t:LBL[d],v:NAME[d](k)});
  for(const k in state.r)chips.push({d:'r_'+k,k,t:SM[k].name,v:state.r[k][0]+'–'+state.r[k][1]});
  if(state.q)chips.push({d:'q',k:'',t:'Поиск',v:'"'+state.q+'"'});
  c.innerHTML=(chips.length?`<span class="lead">Фильтры:</span>`:`<span class="lead">Все предметы</span>`)+
    chips.map(ch=>`<span class="achip"><b>${esc(ch.t)}:</b> ${esc(ch.v)} <span class="x" data-cx="${ch.d}" data-ck="${esc(ch.k)}">×</span></span>`).join('')+
    (chips.length?`<button class="clearall" onclick="resetFilters()">Сбросить всё</button>`:'')+
    `<span class="count">${n} ${plural(n,'предмет','предмета','предметов')}</span>`;
}
function plural(n,a,b,c){n=Math.abs(n)%100;const n1=n%10;if(n>10&&n<20)return c;if(n1>1&&n1<5)return b;if(n1===1)return a;return c;}
document.getElementById('chips').addEventListener('click',e=>{
  const x=e.target.closest('[data-cx]');if(!x)return;
  const d=x.dataset.cx,k=x.dataset.ck;
  if(d==='q'){state.q='';document.getElementById('q').value='';}
  else if(d.startsWith('r_'))delete state.r[d.slice(2)];
  else state.f[d].delete(k);
  buildFilters();render();writeURL();
});

function statCell(i,k){
  const v=i.stats[k];
  if(v==null)return `<td class="statcell dim">—</td>`;
  const w=Math.min(100,Math.abs(v)/barMax(k)*100);const col=statColor(k);
  return `<td class="statcell tnum">${fmtStat(k,v)}<span class="bar" style="width:${w}%;background:${col}"></span></td>`;
}
function tableHTML(list){
  const stats=activeColumns(list);
  const base=[['name','Название'],['_typeLabel','Тип'],['setName','Набор'],['_weightLabel','Вес']];
  const tail=[['_mnf','Произв.']];
  const cols=[...base,...stats.map(k=>[k,SM[k].name]),...tail];
  const th=`<th class="cmpcol"></th>`+cols.map(([k,l])=>{
    const on=state.sort.key===k;return `<th data-sort="${k}">${esc(l)}${on?`<span class="sar">${state.sort.dir<0?'▼':'▲'}</span>`:''}</th>`;}).join('');
  const rows=list.map(i=>`<tr data-key="${i.key}">
    <td class="cmpcol"><span class="cmpbox" data-cmp="${i.key}">${state.cmp.has(i.key)?'✓':''}</span></td>
    <td><div class="cellname">${icon(i.catIcon)}<div><div class="nm">${esc(i.name)}</div><div class="rk">${esc(i.catName||'')}</div></div></div></td>
    <td>${esc(i._typeLabel)}</td>
    <td class="${i.setName?'tag-set':''}">${esc(i.setName||'—')}</td>
    <td class="${i.weight?'tag-w':''}">${esc(i._weightLabel||'—')}</td>
    ${stats.map(k=>statCell(i,k)).join('')}
    <td class="dim" style="color:var(--dim)">${esc(i._mnf||'—')}</td></tr>`).join('');
  return `<table class="db"><thead><tr>${th}</tr></thead><tbody>${rows}</tbody></table>`;
}
function cardsHTML(list){
  return `<div class="grid">`+list.map(i=>{
    const stats=activeColumns([i]).filter(k=>i.stats[k]!=null).slice(0,4);
    return `<div class="card" data-key="${i.key}">
      <div class="top">${icon(i.catIcon)}
        <div style="flex:1"><div class="nm">${esc(i.name)}</div><div class="sub">${esc(i._typeLabel)}${i.catName?' · '+esc(i.catName):''}</div></div>
        <span class="cmpbox" data-cmp="${i.key}" style="align-self:start">${state.cmp.has(i.key)?'✓':''}</span></div>
      <div class="bl">${i.setName?`<span class="b set">${esc(i.setName)}</span>`:''}${i.weight?`<span class="b w">${esc(i._weightLabel)}</span>`:''}${i._mnf?`<span class="b">${esc(i._mnf)}</span>`:''}</div>
      <div class="cstat">${stats.map(k=>{const w=Math.min(100,Math.abs(i.stats[k])/barMax(k)*100);
        return `<div class="r"><span>${esc(SM[k].name)}</span><b class="tnum">${fmtStat(k,i.stats[k])}</b><span class="bar" style="width:${w}%;background:${statColor(k)}"></span></div>`;}).join('')}</div>
    </div>`;}).join('')+`</div>`;
}
document.getElementById('scroll').addEventListener('click',e=>{
  const cmp=e.target.closest('[data-cmp]');if(cmp){e.stopPropagation();toggleCmp(cmp.dataset.cmp);return;}
  const th=e.target.closest('[data-sort]');if(th){const k=th.dataset.sort;
    if(state.sort.key===k)state.sort.dir*=-1;else state.sort={key:k,dir:k==='name'||['_typeLabel','setName','_weightLabel','_mnf'].includes(k)?1:-1};
    render();writeURL();return;}
  const row=e.target.closest('[data-key]');if(row){state.tab==='mods'?openMod(row.dataset.key):openItem(row.dataset.key);}
});

