# -*- coding: utf-8 -*-
import json, os
from arz import ARZ
GD=os.environ.get("GD_DIR",'C:/games/Steam/steamapps/common/Grim Dawn')
ARZS=['database/database.arz','gdx1/database/GDX1.arz','gdx2/database/GDX2.arz','gdx3/database/GDX3.arz']

ARMOR_SLOTS=['head','shoulders','chest','legs','hands','feet','amulet','ring','medal','waist']
WEAPON_SLOTS=['sword','sword2h','mace','mace2h','axe','axe2h','dagger','scepter','spear2h','ranged1h','ranged2h','offhand','shield']
SLOT_FLAGS=ARMOR_SLOTS+WEAPON_SLOTS

RES={'defensiveFire':'fire','defensiveCold':'cold','defensiveLightning':'lightning',
     'defensivePoison':'poison','defensivePierce':'pierce','defensiveBleeding':'bleed',
     'defensiveLife':'vitality','defensiveAether':'aether','defensiveChaos':'chaos',
     'defensivePhysical':'physical','defensiveElementalResistance':'elemental_all',
     'defensiveDisruption':'disruption','defensiveStun':'stun'}

def num(v):
    try:
        f=float(v); return int(f) if f==int(f) else round(f,1)
    except: return v

def collect():
    comps={}
    for f in ARZS:
        az=ARZ(f'{GD}/{f}')
        for hdr in az.hdrs:
            low=hdr['name'].lower()
            if 'items/materia/comp' not in low: continue
            rec=az.record(hdr)
            if rec.get('Class')!='ItemRelic' or not rec.get('craftingMaterial'): continue
            key=hdr['name'].split('/')[-1].replace('.dbr','')
            slots=[s for s in SLOT_FLAGS if rec.get(s)==1]
            resists={}
            for fld,nm in RES.items():
                v=rec.get(fld)
                if v: resists[nm]=num(v)
            entry={
                'desc': rec.get('FileDescription',''),
                'slots': slots,
                'resists': resists,
            }
            armor=rec.get('characterArmor');
            if armor: entry['armor']=num(armor)
            if rec.get('characterArmorModifier'): entry['armor_pct']=num(rec['characterArmorModifier'])
            if rec.get('characterLife'): entry['health']=num(rec['characterLife'])
            if rec.get('characterLifeModifier'): entry['health_pct']=num(rec['characterLifeModifier'])
            if rec.get('defensiveAbsorptionModifier'): entry['armor_absorb_pct']=num(rec['defensiveAbsorptionModifier'])
            if rec.get('itemSkillName'): entry['grants_skill']=True
            comps[key]=entry
    return comps

if __name__=='__main__':
    comps=collect()
    out=json.dumps(comps,ensure_ascii=False,indent=1,sort_keys=True)
    outpath=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','components.json')
    open(outpath,'w',encoding='utf-8').write(out)
    print('total components:',len(comps))
    # sanity check the ones I got wrong before
    for k in ['compa_frozenheart','compb_chainsofoleron','compa_sanctifiedbone','compa_corpsedust','compa_markofthemyrmidon']:
        if k in comps: print(k,'->',comps[k]['desc'],'| slots:',comps[k]['slots'],'| res:',comps[k]['resists'])
