# -*- coding: utf-8 -*-
import os
from gdchar import R
base=os.environ.get("GD_SAVE_MAIN","C:/games/Steam/userdata/337375846/219990/remote/save/main")
PATH=os.environ.get("GD_SAVE_FILE", f"{base}/_yelowhut/player.gdc")

def read_item(r, extra=4):
    it={}
    it['base']=r.s(); it['prefix']=r.s(); it['suffix']=r.s(); it['modifier']=r.s(); it['transmute']=r.s()
    it['seed']=r.i32()
    it['relic']=r.s(); it['relic_bonus']=r.s(); it['relic_seed']=r.i32()
    it['augment']=r.s(); it['unknown']=r.i32(); it['augment_seed']=r.i32()
    it['relic_completion']=r.i32(); it['stack']=r.i32()
    for _ in range(extra): r.i32()
    return it

def read_grid_item(r):   # InventoryItem / StashItem = Item + X + Y
    it=read_item(r); it['X']=r.i32(); it['Y']=r.i32(); return it

def load(path):
    d=open(path,'rb').read(); r=R(d)
    r.u32();r.u32();r.ws();r.bool();r.s();r.i32();r.bool();r.byte();r.skip_checksum();r.i32();r.sbytes(16)
    return d,r

def parse(path):
    d,r=load(path)
    bags=[]; stashes=[]
    while r.pos<len(d):
        bid=r.i32(); length=r.raw4_noupd(); end=r.pos+length
        if bid==3:
            ver=r.i32(); has=r.bool()
            if has:
                sc=r.i32(); r.i32(); r.i32()
                for s in range(sc):
                    sid=r.i32(); slen=r.raw4_noupd(); send=r.pos+slen
                    unused=r.bool(); cnt=r.i32()
                    items=[read_grid_item(r) for _ in range(cnt)]
                    bags.append({'delta':r.pos-send,'items':items})
                    r.pos=send; r.skip_checksum()
        elif bid==4:
            ver=r.i32(); stc=r.i32()
            for s in range(stc):
                sid=r.i32(); slen=r.raw4_noupd(); send=r.pos+slen
                w=r.i32(); h=r.i32(); cnt=r.i32()
                items=[read_grid_item(r) for _ in range(cnt)]
                stashes.append({'w':w,'h':h,'delta':r.pos-send,'items':items})
                r.pos=send; r.skip_checksum()
        r.pos=end; r.skip_checksum()
    return bags,stashes

def leaf(p): return p.replace('.dbr','').split('/')[-1] if p else ''
def short(p): return p.replace('records/items/','').replace('.dbr','') if p else ''

if __name__=='__main__':
    bags,stashes=parse(PATH)
    print("СУМКИ:", len(bags), "  делты:", [b['delta'] for b in bags])
    print("СТЕШ-вкладки:", len(stashes), "делты:", [s['delta'] for s in stashes])
    def dump(items):
        for it in items:
            if not it['base']: continue
            extra=[]
            if it['prefix']: extra.append('преф:'+leaf(it['prefix']))
            if it['suffix']: extra.append('суф:'+leaf(it['suffix']))
            if it['relic']: extra.append('комп:'+leaf(it['relic']))
            if it['augment']: extra.append('AUG:'+leaf(it['augment']))
            st=f" x{it['stack']}" if it['stack']>1 else ''
            print(f"    {short(it['base'])}{st}  {' '.join(extra)}")
    for i,b in enumerate(bags):
        print(f"\n-- Сумка {i} ({len(b['items'])} предметов) --")
        dump(b['items'])
    for i,s in enumerate(stashes):
        print(f"\n-- Стеш-вкладка {i} {s['w']}x{s['h']} ({len(s['items'])} предметов) --")
        dump(s['items'])
