# -*- coding: utf-8 -*-
import os
from gdchar import R
base=os.environ.get("GD_SAVE_MAIN","C:/games/Steam/userdata/337375846/219990/remote/save/main")

def load(path):
    d=open(path,'rb').read()
    r=R(d)
    r.u32();r.u32();r.ws();r.bool();r.s();r.i32();r.bool();r.byte();r.skip_checksum();r.i32();r.sbytes(16)
    return d,r

def read_item(r, extra):
    it={}
    it['base']=r.s(); it['prefix']=r.s(); it['suffix']=r.s(); it['modifier']=r.s(); it['transmute']=r.s()
    it['seed']=r.i32()
    it['relic']=r.s(); it['relic_bonus']=r.s(); it['relic_seed']=r.i32()
    it['augment']=r.s(); it['unknown']=r.i32(); it['augment_seed']=r.i32()
    it['relic_completion']=r.i32(); it['stack']=r.i32()
    for _ in range(extra): r.i32()   # v11 extra tail ints
    it['attached']=r.bool()
    return it

def parse_gear(path, extra):
    d,r=load(path)
    while r.pos<len(d):
        bid=r.i32(); length=r.raw4_noupd(); end=r.pos+length
        if bid==3:
            ver=r.i32(); has=r.bool()
            if not has: return None
            sc=r.i32(); r.i32(); r.i32()
            for s in range(sc):
                sid=r.i32(); slen=r.raw4_noupd(); r.pos+=slen; r.skip_checksum()
            r.bool()
            eq=[read_item(r,extra) for _ in range(12)]
            a1=r.bool(); w1=[read_item(r,extra) for _ in range(2)]
            a2=r.bool(); w2=[read_item(r,extra) for _ in range(2)]
            ok = all(not it['base'] or it['base'].startswith('records/') for it in eq+w1+w2)
            return {'ver':ver,'delta':r.pos-end,'ok':ok,'eq':eq,'w':[w1,w2],'end':end,'pos':r.pos}
        r.pos=end; r.skip_checksum()

SLOTS=['Голова','Амулет','Торс','Ноги','Ступни','Руки(перчатки)','Кольцо1','Кольцо2','Пояс','Медаль','Плечи','Реликвия']
def nm(p): return p.replace('records/items/','').replace('.dbr','') if p else ''
def leaf(p): return nm(p).split('/')[-1]

def show(path):
    res=parse_gear(path, 4)
    print(f"block3 v{res['ver']}  (delta {res['delta']})\n")
    print("=== НАДЕТО ===")
    empty=[]
    for i,it in enumerate(res['eq']):
        slot=SLOTS[i] if i<len(SLOTS) else str(i)
        if not it['base']:
            empty.append(slot); continue
        print(f"  {slot:16} {leaf(it['base'])}")
        parts=[]
        if it['prefix']:   parts.append('преф: '+leaf(it['prefix']))
        if it['suffix']:   parts.append('суф: '+leaf(it['suffix']))
        if it['modifier']: parts.append('мод: '+leaf(it['modifier']))
        if parts: print(f"        {' | '.join(parts)}")
        if it['augment']:  print(f"        АУГМЕНТ: {leaf(it['augment'])}")
        if it['relic']:    print(f"        компонент: {leaf(it['relic'])} (готовность {it['relic_completion']})")
        if it['transmute']:print(f"        (иллюзия/вид: {leaf(it['transmute'])})")
    labels=['set1-осн','set1-щит/2я','set2-осн','set2-щит/2я']
    print("\n=== ОРУЖЕЙНЫЕ НАБОРЫ ===")
    flat=res['w'][0]+res['w'][1]
    for j,it in enumerate(flat):
        if not it['base']: print(f"  {labels[j]:14} (пусто)"); continue
        line=f"  {labels[j]:14} {leaf(it['base'])}"
        if it['augment']: line+=f"   аугмент:{leaf(it['augment'])}"
        print(line)
        af=[x for x in [it['prefix'] and 'преф:'+leaf(it['prefix']), it['suffix'] and 'суф:'+leaf(it['suffix']), it['modifier'] and 'мод:'+leaf(it['modifier'])] if x]
        if af: print(f"        {' | '.join(af)}")
        if it['relic']: print(f"        компонент: {leaf(it['relic'])}")
    if empty: print("\nПУСТЫЕ СЛОТЫ:", ', '.join(empty))
    # augment / resist audit
    augs=[leaf(it['augment']) for it in res['eq']+flat if it['augment']]
    print(f"\nВсего аугментов надето: {len(augs)} из ~14 возможных")

if __name__=='__main__':
    show(f"{base}/_yelowhut/player.gdc")
