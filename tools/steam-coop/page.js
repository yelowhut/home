const D = window.STEAM_COOP_DATA;
const GAMES = D.games;
// одна и та же логика обслуживает страницу своих игр и страницу магазина
const MODE = D.mode || 'owned';
const STORE = MODE === 'store';
const ACCOUNTS = D.accounts || [];
const HAS_ACCOUNTS = ACCOUNTS.length > 0;
// префикс ключей localStorage: у страниц разные списки скрытого
const LS = STORE ? 'steamCoopStore' : 'steamCoop';
const CNT_STEPS = [0, 50, 500, 5000, 50000];
// Переключаемые режимы совместной игры. id — категория Steam, test — как её понимать.
// 24 сама по себе бывает и чисто PvP-шной, поэтому требуем к ней 9 (Co-op),
// иначе «общий экран» тянул бы в кооп-список файтинги.
const hasCat = (g,c) => (g.spc || []).includes(c);
const MODES = [
  {id:39, label:'Split-screen co-op',   tag:'split-screen co-op', def:true,
   test:g => hasCat(g,39)},
  {id:24, label:'Общий экран',           tag:'общий экран',        def:true,
   // 24 бывает и чисто PvP-шной (файтинги): пускаем, если есть кооп ИЛИ нет PvP-метки,
   // иначе «общий экран» затащил бы в кооп-список Mortal Kombat
   test:g => hasCat(g,24) && (hasCat(g,9) || !hasCat(g,37))},
  {id:37, label:'Split-screen PvP',     tag:'split-screen PvP',   def:false, pvp:true,
   test:g => hasCat(g,37)},
  {id:38, label:'Онлайн-кооп',          tag:'онлайн-кооп',        def:false, net:true,
   test:g => hasCat(g,38)},
  {id:48, label:'LAN-кооп',             tag:'LAN-кооп',           def:false, net:true,
   test:g => hasCat(g,48)},
];
// в магазине список на тысячи строк: рисуем частями, иначе телефон подвисает на каждый фильтр
const RENDER_CAP = 400;
// пороги цены в центах, последний = без ограничений
const PRICE_STEPS = [0, 500, 1000, 1500, 2000, 3000, 4000, 6000, null];
const fmtPrice = c => c === null ? 'без ограничений' : (c === 0 ? 'бесплатно' : '$' + (c/100).toFixed(0));
const DECKS = [
  {v:3, label:'Verified'},
  {v:2, label:'Playable'},
  {v:1, label:'Unsupported'},
  {v:0, label:'Не проверено'},
];
const RELEASE_YEARS = GAMES.map(g => g.releaseTs && new Date(g.releaseTs*1000).getUTCFullYear())
                           .filter(Boolean);
const YMIN = Math.min(1995, ...RELEASE_YEARS);
const YMAX = Math.max(new Date().getFullYear() + 1, ...RELEASE_YEARS);

const $ = s => document.querySelector(s);
// часть элементов есть только на одной из страниц — обращаемся мягко
const el = (sel, fn) => { const e = $(sel); if(e) fn(e); };
const setText = (sel, v) => el(sel, e => { e.textContent = v; });
const COLS = [...document.querySelectorAll('thead th[data-k]')].map(th => th.dataset.k);

const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const st = {
  q:'', both:false,
  modes:new Set(MODES.filter(m=>m.def).map(m=>m.id)),
  accs:new Set(ACCOUNTS.map(a=>a.key)),
  decks:new Set(DECKS.map(d=>d.v)),
  y1:YMIN, y2:YMAX, minPct:0, minCnt:0,
  maxPrice:PRICE_STEPS.length-1, freeOnly:false, showSoon:false, showAll:false,
  sort:'rating', dir:-1,
  // на телефоне steam:// может быть не зарегистрирован, а https-ссылку магазина
  // мобильное приложение Steam обычно перехватывает само
  linkMode: loadPref(LS + 'LinkMode', matchMedia('(hover:none)').matches ? 'web' : 'client'),
  // локальные правки поверх списка из файла: что доскрыли и что вернули
  hidAdd: loadIds(LS + 'HiddenAdd'),
  hidRemove: loadIds(LS + 'HiddenRemove'),
  showHidden: false,
};

// Базовый список приезжает в hidden.js вместе с файлом и одинаков на всех устройствах.
// Локальные правки хранятся отдельно как diff — иначе либо потерялись бы при переносе,
// либо навсегда затенили бы обновлённый файл.
function idSet(v){
  return new Set(Array.isArray(v) ? v.map(Number).filter(Number.isFinite) : []);
}
function loadIds(key){
  try{ return idSet(JSON.parse(loadPref(key, '[]'))) }catch(e){ return new Set() }
}
function saveHidden(){
  savePref(LS + 'HiddenAdd', JSON.stringify([...st.hidAdd]));
  savePref(LS + 'HiddenRemove', JSON.stringify([...st.hidRemove]));
}

const BAKED = idSet(window.STEAM_COOP_HIDDEN || []);

// effective = (файл ∪ локально скрытые) \ локально возвращённые
const isHidden = id => (BAKED.has(id) || st.hidAdd.has(id)) && !st.hidRemove.has(id);
function hiddenSet(){
  const s = new Set([...BAKED, ...st.hidAdd]);
  st.hidRemove.forEach(id => s.delete(id));
  return s;
}
function toggleHidden(id){
  if(isHidden(id)){
    st.hidAdd.delete(id);
    if(BAKED.has(id)) st.hidRemove.add(id);   // перекрываем файл локально
  } else {
    st.hidRemove.delete(id);
    if(!BAKED.has(id)) st.hidAdd.add(id);
  }
  saveHidden();
}
// содержимое нового hidden.js
function hiddenFileText(){
  const ids = [...hiddenSet()].sort((a,b)=>a-b);   // сортировка, чтобы git-диффы были чистыми
  return '// Список скрытых игр (appid), едет вместе со страницей и бандлом.\n'
    + '// Обновляется кнопкой «Сохранить список в файл» на самой странице:\n'
    + '// заменить этот файл скачанным, затем пересобрать — python3 tools/steam-coop/build.py\n'
    + 'window.STEAM_COOP_HIDDEN = ' + JSON.stringify(ids) + ';\n';
}

// localStorage может быть недоступен при открытии через file:// — не роняем страницу
function loadPref(k, def){ try{ return localStorage.getItem(k) || def }catch(e){ return def } }
function savePref(k, v){ try{ localStorage.setItem(k, v) }catch(e){} }

const year = ts => ts ? new Date(ts*1000).getUTCFullYear() : null;
const fmtDate = ts => ts
  ? new Date(ts*1000).toLocaleDateString('ru-RU',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'})
  : '—';
const fmtNum = n => n>=1000 ? (n/1000).toFixed(n>=10000?0:1).replace('.',',')+'k' : String(n);
const fmtHrs = m => m>=60 ? Math.round(m/60)+' ч' : (m>0 ? m+' мин' : '—');

// ---- построение фильтров ----
el('#accs', e => e.innerHTML = ACCOUNTS.map(a=>
  `<label class="opt on"><input type="checkbox" data-acc="${a.key}" checked>
   <span class="lbl">${esc(a.label)}</span><span class="n">${a.size}</span></label>`).join(''));
el('#modes', e => e.innerHTML = MODES.map(m=>
  `<label class="opt${m.def ? ' on' : ''}"><input type="checkbox" data-mode="${m.id}"${m.def ? ' checked' : ''}>
   <span class="lbl">${m.label}</span><span class="n" data-mn="${m.id}"></span></label>`).join(''));
$('#decks').innerHTML = DECKS.map(d=>
  `<label class="opt on"><input type="checkbox" data-deck="${d.v}" checked>
   <span class="lbl">${d.label}</span><span class="n" data-dn="${d.v}"></span></label>`).join('');
for(const id of ['#y1','#y2']){ $(id).min = YMIN; $(id).max = YMAX; }
$('#y1').value = st.y1; $('#y2').value = st.y2;

// ---- фильтрация ----
// игра проходит, если включён хотя бы один её режим
function typeOk(g){ return MODES.some(m => st.modes.has(m.id) && m.test(g)); }

function pass(g){
  if(!typeOk(g)) return false;
  if(!st.showHidden && isHidden(g.appid)) return false;
  if(st.q && !g.name.toLowerCase().includes(st.q)) return false;
  if(HAS_ACCOUNTS && !g.owners.some(o=>st.accs.has(o))) return false;
  if(st.both && g.owners.length < 2) return false;
  if(!st.decks.has(g.deck)) return false;
  const y = year(g.releaseTs);
  const narrowed = st.y1 > YMIN || st.y2 < YMAX;
  if(y === null){ if(narrowed) return false; }
  else if(y < st.y1 || y > st.y2) return false;
  if((g.reviewPercent ?? -1) < st.minPct) return false;
  if((g.reviewCount ?? 0) < CNT_STEPS[st.minCnt]) return false;
  if(STORE){
    // не вышедшие прячем по умолчанию: для списка покупок это шум
    if(!st.showSoon && g.comingSoon) return false;
    if(st.freeOnly && !g.isFree) return false;
    const cap = PRICE_STEPS[st.maxPrice];
    if(cap !== null){
      if(g.isFree) return true;
      if(g.priceCents == null || g.priceCents > cap) return false;
    }
  }
  return true;
}

const KEYS = {
  name:    g => g.name.toLowerCase(),
  owners:  g => g.owners.slice().sort().join(','),
  rating:  g => [g.reviewScore ?? -1, g.reviewPercent ?? -1, g.reviewCount ?? 0],
  deck:    g => g.deckRank,
  release: g => g.releaseTs,
  playtime:g => g.playtime,
  // бесплатные — ноль, цена неизвестна — в конец
  price:   g => g.isFree ? 0 : (g.priceCents == null ? Infinity : g.priceCents),
};

function cmp(a,b){
  const k = KEYS[st.sort];
  let x = k(a), y = k(b);
  // «не проверено» и отсутствующие даты — всегда в конце, независимо от направления
  if(st.sort==='deck'){
    if((a.deck===0) !== (b.deck===0)) return a.deck===0 ? 1 : -1;
  }
  if(st.sort==='release'){
    if((x==null) !== (y==null)) return x==null ? 1 : -1;
  }
  // цена неизвестна — тоже в конец в обе стороны, это отсутствие данных, а не «дорого»
  if(st.sort==='price'){
    const na = g => !g.isFree && g.priceCents == null;
    if(na(a) !== na(b)) return na(a) ? 1 : -1;
  }
  let r = 0;
  if(Array.isArray(x)){
    for(let i=0;i<x.length && !r;i++) r = x[i] < y[i] ? -1 : x[i] > y[i] ? 1 : 0;
  } else {
    r = x < y ? -1 : x > y ? 1 : 0;
  }
  return r * st.dir || KEYS.name(a).localeCompare(KEYS.name(b),'ru');
}

// ---- отрисовка ----
function render(){
  const list = GAMES.filter(pass).sort(cmp);
  const capped = !st.showAll && list.length > RENDER_CAP;
  const shown = capped ? list.slice(0, RENDER_CAP) : list;

  $('#rows').innerHTML = shown.map(g=>{
    const p = g.reviewPercent;
    const cls = p==null ? '' : p>=80 ? 'g' : p>=60 ? 'm' : 'b';
    const tags = MODES.filter(m => m.test(g)).map(m =>
      `<span class="tag${m.pvp ? ' pvp' : m.net ? ' net' : ''}">${m.tag}</span>`);
    const dl = (DECKS.find(d=>d.v===g.deck) || DECKS[3]).label;
    const inClient = st.linkMode === 'client';
    // steam://store открывает страницу магазина внутри клиента, steam://run запускает игру
    const href = inClient
      ? `steam://store/${g.appid}`
      : `https://store.steampowered.com/${esc(g.storePath)}`;
    const attrs = inClient ? '' : ' target="_blank" rel="noopener"';
    const isHid = isHidden(g.appid);
    // ячейки собираются по колонкам, объявленным в самой странице (thead data-k),
    // поэтому у своих игр и у магазина разные наборы столбцов без копии шаблона
    const cell = {
      name: () => `<td class="nm"><a href="${href}"${attrs}>${esc(g.name)}</a>`
        + (STORE ? '' : `<a class="run" href="steam://run/${g.appid}" title="Запустить игру в Steam">▶ запуск</a>`)
        + `<button class="hide" data-hide="${g.appid}" title="${isHid ? 'Вернуть в список' : 'Скрыть игру'}"`
        + `>${isHid ? '↺ вернуть' : '✕ скрыть'}</button>`
        + `<div class="tags">${tags.join('')}</div></td>`,
      owners: () => `<td class="own">${g.owners.map(o=>`<span class="acc ${esc(o)}">${esc(o)}</span>`).join('')}</td>`,
      rating: () => `<td class="rt"><span class="pct ${cls} tnum">${p==null?'—':p+'%'}</span> `
        + `<span class="rc tnum">${g.reviewCount?'('+fmtNum(g.reviewCount)+')':''}</span></td>`,
      deck: () => `<td class="dk"><span class="deck d${g.deck}"><span class="dot"></span>${dl}</span></td>`,
      release: () => `<td class="rl tnum">${fmtDate(g.releaseTs)}`
        + (g.comingSoon ? ' <span class="tag soon">не вышла</span>' : '') + `</td>`,
      playtime: () => `<td class="pt tnum">${fmtHrs(g.playtime)}</td>`,
      price: () => `<td class="pr tnum${g.isFree ? ' free' : ''}">${esc(g.priceText || '—')}</td>`,
    };
    return `<tr${isHid ? ' class="hid"' : ''}>`
      + COLS.map(k => (cell[k] || (()=>'<td></td>'))()).join('')
      + `</tr>`;
  }).join('');

  el('#more', e => {
    e.hidden = !capped;
    e.textContent = `Показаны первые ${RENDER_CAP} из ${list.length} — показать все`;
  });
  $('#empty').hidden = list.length > 0;
  $('#count').innerHTML = `<b>${list.length}</b> из ${GAMES.filter(typeOk).length}`;

  // счётчики в сайдбаре считаются по текущему набору
  MODES.forEach(m => setText(`[data-mn="${m.id}"]`, GAMES.filter(m.test).length));
  setText('#n-both', GAMES.filter(g=>typeOk(g) && g.owners.length>1).length);
  $('#n-hidden').textContent = GAMES.filter(g=>typeOk(g) && isHidden(g.appid)).length;
  const hidTotal = hiddenSet().size;
  $('#unhide-all').hidden = hidTotal === 0;
  $('#unhide-all').textContent = `Вернуть все скрытые (${hidTotal})`;
  DECKS.forEach(d=>{
    const el = document.querySelector(`[data-dn="${d.v}"]`);
    if(el) el.textContent = GAMES.filter(g=>typeOk(g) && g.deck===d.v).length;
  });

  if(STORE){
    setText('#n-free', GAMES.filter(g=>typeOk(g) && g.isFree).length);
    setText('#n-soon', GAMES.filter(g=>typeOk(g) && g.comingSoon).length);
  }
  document.querySelectorAll('#lnkmode button').forEach(b=>
    b.classList.toggle('on', b.dataset.m === st.linkMode));

  document.querySelectorAll('thead th').forEach(th=>{
    const on = th.dataset.k === st.sort;
    th.classList.toggle('on', on);
    th.querySelector('.arw').textContent = st.dir < 0 ? '▼' : '▲';
  });
  document.querySelectorAll('.opt').forEach(o=>{
    const i = o.querySelector('input[type=checkbox]');
    if(i) o.classList.toggle('on', i.checked);
  });

  const s = D.stats;
  $('#foot').innerHTML = STORE
    ? `Просмотрено ${s.swept} игр магазина с общим экраном, вычтено ${s.owned} уже имеющихся, `
      + `осталось ${s.candidates} кандидатов. Предикату соответствуют ${s.matched}, `
      + `в список попали ${s.matched - s.dropped} с числом отзывов не меньше ${s.minReviews} `
      + `(отброшено ${s.dropped} малоизвестных — иначе страница не поднялась бы на телефоне). `
      + `${s.unresolved} игр не отдали данные магазина. Ещё не вышли: ${s.comingSoon}. `
      + `Цены — снимок на момент сборки. `
      + `Обновить: <code>STEAM_API_KEY=… python3 tools/steam-coop/fetch_store.py</code>`
    : `Библиотеки: ${ACCOUNTS.map(a=>`${a.label} — ${a.size}`).join(', ')}; ${s.union} уникальных игр. `
      + `Про совместную игру — ${s.total ?? GAMES.length}: на одном устройстве ${s.sameDevice}, `
      + `с онлайн-коопом ${s.online ?? '—'}. `
      + `${s.unresolved} игр не отдали данные магазина (удалены/недоступны в регионе) — их категории неизвестны, `
      + `в список они не попали. Источник: Steam Web API + IStoreBrowseService. `
      + `Обновить: <code>STEAM_API_KEY=… python3 tools/steam-coop/fetch.py</code>`;
}

// ---- события ----
// строки перерисовываются через innerHTML, поэтому слушаем контейнер, а не кнопки
$('#rows').addEventListener('click', e => {
  const b = e.target.closest('[data-hide]');
  if(!b) return;
  const id = +b.dataset.hide;
  toggleHidden(id);
  render();
});
$('#f-hidden').onchange = e => { st.showHidden = e.target.checked; render(); };

// Скачивание blob-а со страницы, открытой как локальный файл, работает не везде,
// поэтому текст всегда показываем в поле — оттуда его можно скопировать руками.
$('#export').onclick = () => {
  const text = hiddenFileText();
  const ta = $('#exported');
  ta.value = text;
  ta.hidden = false;
  try{
    const url = URL.createObjectURL(new Blob([text], {type:'text/javascript'}));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hidden.js';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }catch(e){ /* поле с текстом уже заполнено */ }
};
// чистим локальные добавления и глушим весь базовый список — иначе он вернулся бы
// после перезагрузки, хотя кнопка отработала бы «успешно»
$('#unhide-all').onclick = () => {
  st.hidAdd.clear();
  BAKED.forEach(id => st.hidRemove.add(id));
  saveHidden();
  render();
};

document.querySelectorAll('#lnkmode button').forEach(b => b.onclick = () => {
  st.linkMode = b.dataset.m;
  savePref('steamCoopLinkMode', st.linkMode);
  render();
});
el('#maxPrice', e => { e.max = PRICE_STEPS.length-1; e.value = st.maxPrice;
  e.oninput = ev => { st.maxPrice = +ev.target.value;
    setText('#prv', fmtPrice(PRICE_STEPS[st.maxPrice])); render(); }; });
el('#more', e => e.onclick = () => { st.showAll = true; render(); });
el('#f-free', e => e.onchange = ev => { st.freeOnly = ev.target.checked; render(); });
el('#f-soon', e => e.onchange = ev => { st.showSoon = ev.target.checked; render(); });
let qTimer = null;
$('#q').oninput = e => {
  const v = e.target.value.trim().toLowerCase();
  clearTimeout(qTimer);
  // на большом списке перерисовка на каждый символ ощутимо тормозит
  qTimer = setTimeout(() => { st.q = v; st.showAll = false; render(); }, 150);
};
document.querySelectorAll('[data-mode]').forEach(i => i.onchange = e => {
  const id = +e.target.dataset.mode;
  if(e.target.checked) st.modes.add(id); else st.modes.delete(id);
  st.showAll = false;
  render();
});
el('#f-both', e => e.onchange = ev => { st.both = ev.target.checked; render(); });
document.querySelectorAll('[data-acc]').forEach(i => i.onchange = e => {
  e.target.checked ? st.accs.add(e.target.dataset.acc) : st.accs.delete(e.target.dataset.acc);
  render();
});
document.querySelectorAll('[data-deck]').forEach(i => i.onchange = e => {
  const v = +e.target.dataset.deck;
  e.target.checked ? st.decks.add(v) : st.decks.delete(v);
  render();
});
$('#y1').oninput = e => { st.y1 = +e.target.value || YMIN; render(); };
$('#y2').oninput = e => { st.y2 = +e.target.value || YMAX; render(); };
document.querySelectorAll('.presets button').forEach(b => b.onclick = () => {
  if(b.dataset.since !== undefined){
    st.y1 = +b.dataset.since || YMIN; st.y2 = YMAX;
  } else {
    st.y1 = YMIN; st.y2 = +b.dataset.until;
  }
  $('#y1').value = st.y1; $('#y2').value = st.y2; render();
});
$('#minPct').oninput = e => { st.minPct = +e.target.value; $('#pv').textContent = st.minPct+'%'; render(); };
$('#minCnt').oninput = e => {
  st.minCnt = +e.target.value;
  $('#cv').textContent = CNT_STEPS[st.minCnt] ? fmtNum(CNT_STEPS[st.minCnt])+'+' : '0';
  render();
};
document.querySelectorAll('thead th').forEach(th => th.querySelector('button').onclick = () => {
  const k = th.dataset.k;
  if(st.sort === k) st.dir = -st.dir;
  else { st.sort = k; st.dir = (k === 'name' || k === 'owners') ? 1 : -1; }
  render();
});
$('#reset').onclick = () => {
  // showHidden — фильтр, сбрасываем; сам список скрытых — данные, не трогаем
  Object.assign(st, {q:'', both:false, y1:YMIN, y2:YMAX,
                     minPct:0, minCnt:0, showHidden:false, showAll:false});
  st.modes = new Set(MODES.filter(m=>m.def).map(m=>m.id));
  document.querySelectorAll('[data-mode]').forEach(i => i.checked = st.modes.has(+i.dataset.mode));
  st.accs = new Set(ACCOUNTS.map(a=>a.key));
  st.decks = new Set(DECKS.map(d=>d.v));
  $('#q').value='';
  el('#f-both', e => e.checked=false);
  Object.assign(st, {maxPrice:PRICE_STEPS.length-1, freeOnly:false, showSoon:false});
  el('#maxPrice', e => e.value = st.maxPrice);
  setText('#prv', fmtPrice(PRICE_STEPS[st.maxPrice]));
  el('#f-free', e => e.checked=false);
  el('#f-soon', e => e.checked=false);
  $('#f-hidden').checked=false;
  $('#y1').value=YMIN; $('#y2').value=YMAX;
  $('#minPct').value=0; $('#pv').textContent='0%';
  $('#minCnt').value=0; $('#cv').textContent='0';
  document.querySelectorAll('[data-acc],[data-deck]').forEach(i=>i.checked=true);
  render();
};

// на узком экране список важнее фильтров — панель свёрнута.
// Заголовок <summary> виден только в этом же диапазоне, поэтому при выходе из него
// (поворот экрана, ресайз) панель надо принудительно раскрыть — иначе фильтры
// окажутся свёрнутыми и без видимого переключателя.
const narrow = matchMedia('(max-width:700px)');
const syncFilters = () => { $('#filters').open = !narrow.matches; };
syncFilters();
// addEventListener на MediaQueryList появился в Safari только с 14 — иначе addListener
if(narrow.addEventListener) narrow.addEventListener('change', syncFilters);
else if(narrow.addListener) narrow.addListener(syncFilters);

render();
