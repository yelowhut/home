"use strict";
const D=window.PB_DATA, SM=D.statMeta, IC=D.icons;
const esc=s=>(s==null?'':(''+s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const icon=(n,cls='ic')=>IC[n]?`<img class="${cls}" src="${IC[n]}" alt="">`:`<span class="${cls}"></span>`;
const RARN={1:'Обычное',2:'Необычное',3:'Редкое'}, RARC={1:'var(--r1)',2:'var(--r2)',3:'var(--r3)'};
const SLOTLBL=s=>({internal_aux_offense:'Наступление',internal_aux_defense:'Защита',internal_aux_mobility:'Мобильность',
  internal_aux_weapon:'Оружие',internal_aux_pilot:'Пилот',internal_aux_top_thrusters:'Двигатели',internal_aux_top_core:'Ядро'}[s]||s);
const HIDE=new Set(['scrap_value','comp2_value','comp3_value','wpn_proj_lifetime','wpn_proj_ricochet']);
const LOWER_BETTER=new Set(['mass','act_heat','wpn_scatter_angle','wpn_scatter_angle_moving','wpn_range_min','act_duration']);

// ---- prep ----
D.items.forEach(i=>{
  i._typeLabel=D.slots[i.slot]||i.slot;
  i._weightLabel=i.weight?D.weights[i.weight]:'';
  i._mnf=i.manufacturer?i.manufacturer.name:'';
  i._search=(i.name+' '+i.nameEn+' '+i.desc+' '+i.key+' '+(i.catName||'')+' '+(i.setName||'')+' '+i._mnf+' '+(i.tags||[]).join(' ')).toLowerCase();
});
D.modules.forEach(m=>{m._search=(m.name+' '+m.nameEn+' '+m.desc+' '+m.key+' '+(m.tags||[]).join(' ')).toLowerCase();});
const MNFS={}; D.items.forEach(i=>{if(i.manufacturer)MNFS[i.manufacturer.key]=i.manufacturer.name;});
const CATS={}; D.items.forEach(i=>{if(i.catName)CATS[i.catName]=i.catIcon;});
// global stat bounds (for bars + range sliders)
const BOUNDS={}; D.items.forEach(i=>{for(const k in i.stats){const v=i.stats[k];if(HIDE.has(k))continue;
  const b=BOUNDS[k]||(BOUNDS[k]={min:Infinity,max:-Infinity});b.min=Math.min(b.min,v);b.max=Math.max(b.max,v);}});
const barMax=k=>Math.max(1,Math.abs((BOUNDS[k]||{}).max||1));

// ---- state (persisted in URL hash) ----
const RANGES=[{k:'wpn_damage'},{k:'wpn_range_max'},{k:'act_heat'},{k:'mass'}];
const state={tab:'items',view:'table',q:'',
  f:{slot:new Set(),set:new Set(),weight:new Set(),cat:new Set(),mnf:new Set()},
  r:{}, modslot:new Set(),
  sort:{key:'name',dir:1}, level:1, rarity:1, open:null, cmp:new Set()};

function writeURL(push){
  const p=new URLSearchParams();
  p.set('tab',state.tab); p.set('view',state.view);
  if(state.q)p.set('q',state.q);
  for(const d in state.f) if(state.f[d].size) p.set(d,[...state.f[d]].join(','));
  for(const k in state.r){const r=state.r[k]; if(r) p.set('r_'+k,r[0]+'-'+r[1]);}
  if(state.modslot.size)p.set('ms',[...state.modslot].join(','));
  if(state.sort.key!=='name'||state.sort.dir!==1)p.set('sort',state.sort.key+':'+(state.sort.dir<0?'d':'a'));
  if(state.cmp.size)p.set('cmp',[...state.cmp].join(','));
  if(state.open)p.set('open',state.open);
  const h='#'+p.toString();
  history[push?'pushState':'replaceState'](null,'',h);
}
function readURL(){
  const p=new URLSearchParams(location.hash.slice(1));
  state.tab=p.get('tab')==='mods'?'mods':'items';
  state.view=p.get('view')==='cards'?'cards':'table';
  state.q=p.get('q')||'';
  for(const d in state.f){state.f[d]=new Set((p.get(d)||'').split(',').filter(Boolean));}
  state.r={}; RANGES.forEach(({k})=>{const v=p.get('r_'+k);if(v){const[a,b]=v.split('-').map(Number);if(!isNaN(a)&&!isNaN(b))state.r[k]=[a,b];}});
  state.modslot=new Set((p.get('ms')||'').split(',').filter(Boolean));
  const s=p.get('sort'); if(s){const[k,d]=s.split(':');state.sort={key:k,dir:d==='d'?-1:1};}
  state.cmp=new Set((p.get('cmp')||'').split(',').filter(Boolean));
  state.open=p.get('open')||null;
}

// ---- matching + counts ----
function inRanges(i,except){for(const k in state.r){if(k===except)continue;const[a,b]=state.r[k];const v=i.stats[k];if(v==null||v<a||v>b)return false;}return true;}
function matchItem(i,exceptDim){
  if(state.q&&!i._search.includes(state.q))return false;
  const f=state.f;
  if(exceptDim!=='slot'&&f.slot.size&&!f.slot.has(i.slot))return false;
  if(exceptDim!=='set'&&f.set.size&&!f.set.has(i.set))return false;
  if(exceptDim!=='weight'&&f.weight.size&&!f.weight.has(i.weight))return false;
  if(exceptDim!=='cat'&&f.cat.size&&!f.cat.has(i.catName))return false;
  if(exceptDim!=='mnf'&&f.mnf.size&&!(i.manufacturer&&f.mnf.has(i.manufacturer.key)))return false;
  if(!inRanges(i,exceptDim&&exceptDim.startsWith('r_')?exceptDim.slice(2):null))return false;
  return true;
}
function facetCount(dim,val){let n=0;for(const i of D.items){if(matchItem(i,dim)){
  if(dim==='slot'&&i.slot===val)n++;else if(dim==='set'&&i.set===val)n++;
  else if(dim==='weight'&&i.weight===val)n++;else if(dim==='cat'&&i.catName===val)n++;
  else if(dim==='mnf'&&i.manufacturer&&i.manufacturer.key===val)n++;}}return n;}

// ---- formatting ----
function fmtStat(k,val,level){const m=SM[k]||{};let v=val;
  if(level&&m.perLevel)v=val*(1+m.perLevel*(level-1));v*=(m.multiplier||1);
  if(Number.isInteger(v)){}else if(m.rounded&&Math.abs(v)>=10)v=Math.round(v);else v=Math.round(v*100)/100;
  return m.percentage?v+'%':''+v;}
function statColor(k){const c=(SM[k]||{}).color;return c?`rgb(${c[0]*255|0},${c[1]*255|0},${c[2]*255|0})`:'var(--accent2)';}
function statName(k){return(SM[k]&&SM[k].name)||k;}
function statIcon(k){return SM[k]&&SM[k].icon?SM[k].icon:null;}

