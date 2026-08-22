# -*- coding: utf-8 -*-
import struct, sys, json, os, io

class R:
    def __init__(self, data):
        self.d=data
        k=struct.unpack_from('<I',data,0)[0]^0x55555555
        self.pos=4; self.key=k
        self.t=[0]*256
        for i in range(256):
            k=((k>>1)|(k<<31))&0xFFFFFFFF; k=(k*39916801)&0xFFFFFFFF; self.t[i]=k
    def byte(self):
        e=self.d[self.pos]; self.pos+=1
        v=e^(self.key&0xFF); self.key^=self.t[e]; return v
    bool=byte
    def _u(self,n):
        e=self.d[self.pos:self.pos+n]; self.pos+=n
        val=int.from_bytes(e,'little')^(self.key & ((1<<(8*n))-1))
        for b in e: self.key^=self.t[b]
        return val
    def i32(self):
        v=self._u(4); return v-(1<<32) if v>=(1<<31) else v
    def u32(self): return self._u(4)
    def f32(self): return struct.unpack('<f',struct.pack('<I',self._u(4)))[0]
    def sbytes(self,n):
        out=bytearray()
        for _ in range(n):
            b=self.d[self.pos]; self.pos+=1; out.append(b^(self.key&0xFF)); self.key^=self.t[b]
        return bytes(out)
    def s(self):
        n=self.u32(); return self.sbytes(n).decode('latin-1')
    def ws(self):
        n=self.u32(); return self.sbytes(n*2).decode('utf-16-le',errors='replace')
    def raw4_noupd(self):
        e=self.d[self.pos:self.pos+4]; self.pos+=4
        return int.from_bytes(e,'little')^self.key  # length: xor key, no update
    def skip_checksum(self):
        # checksum on disk == enc-state (key) at this point; use it to resync key
        e=self.d[self.pos:self.pos+4]; self.pos+=4
        self.key=int.from_bytes(e,'little')

MASTERY={ '01':'Soldier','02':'Demolitionist','03':'Occultist','04':'Nightblade',
          '05':'Arcanist','06':'Shaman','07':'Inquisitor','08':'Necromancer','09':'Oathkeeper'}
DUAL={
 frozenset({'Soldier','Demolitionist'}):'Commando', frozenset({'Soldier','Occultist'}):'Witchblade',
 frozenset({'Soldier','Nightblade'}):'Blademaster', frozenset({'Soldier','Arcanist'}):'Battlemage',
 frozenset({'Soldier','Shaman'}):'Warder', frozenset({'Soldier','Inquisitor'}):'Tactician',
 frozenset({'Soldier','Necromancer'}):'Death Knight', frozenset({'Soldier','Oathkeeper'}):'Warlord',
 frozenset({'Demolitionist','Occultist'}):'Pyromancer', frozenset({'Demolitionist','Nightblade'}):'Saboteur',
 frozenset({'Demolitionist','Arcanist'}):'Sorcerer', frozenset({'Demolitionist','Shaman'}):'Elementalist',
 frozenset({'Demolitionist','Inquisitor'}):'Purifier', frozenset({'Demolitionist','Necromancer'}):'Defiler',
 frozenset({'Demolitionist','Oathkeeper'}):'Shieldbreaker', frozenset({'Occultist','Nightblade'}):'Witch Hunter',
 frozenset({'Occultist','Arcanist'}):'Warlock', frozenset({'Occultist','Shaman'}):'Conjurer',
 frozenset({'Occultist','Inquisitor'}):'Deceiver', frozenset({'Occultist','Necromancer'}):'Cabalist',
 frozenset({'Occultist','Oathkeeper'}):'Sentinel', frozenset({'Nightblade','Arcanist'}):'Spellbreaker',
 frozenset({'Nightblade','Shaman'}):'Trickster', frozenset({'Nightblade','Inquisitor'}):'Infiltrator',
 frozenset({'Nightblade','Necromancer'}):'Reaper', frozenset({'Nightblade','Oathkeeper'}):'Dervish',
 frozenset({'Arcanist','Shaman'}):'Druid', frozenset({'Arcanist','Inquisitor'}):'Mage Hunter',
 frozenset({'Arcanist','Necromancer'}):'Spellbinder', frozenset({'Arcanist','Oathkeeper'}):'Templar',
 frozenset({'Shaman','Inquisitor'}):'Vindicator', frozenset({'Shaman','Necromancer'}):'Ritualist',
 frozenset({'Shaman','Oathkeeper'}):'Archon', frozenset({'Inquisitor','Necromancer'}):'Apostate',
 frozenset({'Inquisitor','Oathkeeper'}):'Inquisitor/Oathkeeper', frozenset({'Necromancer','Oathkeeper'}):'Bonemonger',
}
DIFF=['Normal','Elite','Ultimate']

def class_name(tag):
    # tag like 'tagSkillClassName0102'
    import re
    nums=re.findall(r'(\d{2})', tag.replace('tagSkillClassName',''))
    names=[MASTERY.get(n,n) for n in nums]
    if not names: return '(no mastery yet)'
    if len(names)==1: return names[0]
    combo=DUAL.get(frozenset(names))
    return (combo+' ('+' + '.join(names)+')') if combo else ' + '.join(names)

FACTIONS=['','Devil\'s Crossing','Aetherials','Chthonians','Cronley\'s Gang','Rovers',
          'Homestead','Black Legion','Kymon\'s Chosen','Order of Death\'s Vigil',
          'Undead','Barrowholm','Coven of Ugdenbog','Malmouth Resistance','Vanguard',
          'The Outcast','Bysmiel','Dreeg','Solael','Order/Kymon']

def parse(path):
    d=open(path,'rb').read()
    r=R(d)
    magic=r.u32(); assert magic==0x58434447, hex(magic)
    version=r.u32()
    C={}
    C['name']=r.ws(); C['sex']='M' if r.bool()==1 else 'F'
    C['class_tag']=r.s(); C['level']=r.i32()
    C['hardcore']=bool(r.bool()); C['expansion']=r.byte()
    r.skip_checksum()                 # header checksum
    C['data_version']=r.i32()
    r.sbytes(16)                       # mystery field (uid-ish)
    blocks={}
    while r.pos < len(d):
        bid=r.i32()
        length=r.raw4_noupd()
        end=r.pos+length
        try:
            if bid==1:
                b={}; b['version']=r.i32()
                b['in_main_quest']=r.bool(); b['has_been_in_game']=r.bool()
                b['last_difficulty']=r.byte(); b['greatest_difficulty']=r.byte()
                b['iron']=r.i32()
                b['greatest_survival_diff']=r.byte(); b['tributes']=r.i32()
                blocks[1]=b
            elif bid==2:
                b={}; b['version']=r.i32()
                b['level']=r.i32(); b['experience']=r.i32()
                b['attribute_points']=r.i32(); b['skill_points']=r.i32()
                b['devotion_points']=r.i32(); b['total_devotion_unlocked']=r.i32()
                b['physique']=round(r.f32()); b['cunning']=round(r.f32()); b['spirit']=round(r.f32())
                b['health']=round(r.f32()); b['energy']=round(r.f32())
                blocks[2]=b
            elif bid==8:
                b={}; b['version']=r.i32()
                cnt=r.i32()
                content_start=r.pos; start_key=r.key
                def read_skills(extra):
                    r.pos=content_start; r.key=start_key
                    out=[]
                    for _ in range(cnt):
                        sk={}
                        sk['name']=r.s()
                        if not sk['name'].startswith('records/'): raise ValueError('badname')
                        sk['level']=r.i32(); sk['enabled']=r.bool()
                        sk['devotion_level']=r.i32(); sk['devotion_xp']=r.i32(); sk['sublevel']=r.i32()
                        sk['active']=r.bool(); sk['transition']=r.bool()
                        if extra: r.byte()          # v8+ extra flag byte
                        sk['autocast']=r.s(); sk['autocast_ctrl']=r.s()
                        if r.pos>end: raise ValueError('overflow')
                        out.append(sk)
                    return out
                try:
                    skills=read_skills(0); b['skill_fmt']='v5'
                except Exception:
                    skills=read_skills(1); b['skill_fmt']='v8'
                b['masteries_allowed']=r.i32()
                b['skill_pts_reclaimed']=r.i32(); b['devotion_pts_reclaimed']=r.i32()
                b['skills']=skills
                blocks[8]=b
            elif bid==13:
                b={}; b['version']=r.i32(); b['my_faction']=r.i32()
                cnt=r.i32(); fac=[]
                for i in range(cnt):
                    f={}; f['changed']=r.bool(); f['unlocked']=r.bool()
                    f['value']=round(r.f32()); f['pos_boost']=r.f32(); f['neg_boost']=r.f32()
                    f['idx']=i; fac.append(f)
                b['factions']=fac
                blocks[13]=b
            elif bid==16:
                b={}; b['version']=r.i32()
                b['playtime']=r.i32(); b['deaths']=r.i32(); b['kills']=r.i32()
                b['xp_from_kills']=r.i32(); b['health_pots']=r.i32(); b['energy_pots']=r.i32()
                b['max_level']=r.i32(); b['hits_received']=r.i32(); b['hits_inflicted']=r.i32()
                b['crits_inflicted']=r.i32(); b['crits_received']=r.i32()
                b['greatest_damage']=round(r.f32())
                blocks[16]=b
        except Exception as ex:
            blocks.setdefault('_errors',[]).append(f"block{bid}:{ex}")
        r.pos=end
        r.skip_checksum()
    C['blocks']=blocks
    return C

def fmt_time(sec):
    h=sec//3600; m=(sec%3600)//60; return f"{h}h {m}m"

def summarize(folder,C):
    b=C['blocks']
    print("="*64)
    print(f"[{folder}]  {C['name']}  ({C['sex']})   {'HARDCORE ' if C['hardcore'] else ''}")
    print(f"  Класс: {class_name(C['class_tag'])}   ур. {C['level']}   ({'экспансия' if C['expansion'] else 'база'})")
    if 2 in b:
        a=b[2]
        print(f"  Опыт: {a['experience']:,}   Devotion разблокировано: {a['total_devotion_unlocked']}")
        print(f"  Атрибуты — Физика:{a['physique']}  Хитрость:{a['cunning']}  Дух:{a['spirit']}  | HP:{a['health']}  Энергия:{a['energy']}")
        print(f"  Нераспределено — атрибуты:{a['attribute_points']}  навыки:{a['skill_points']}  devotion:{a['devotion_points']}")
    if 1 in b:
        i=b[1]
        gd=i['greatest_difficulty']
        print(f"  Iron (деньги): {i['iron']:,}   Трибуты: {i['tributes']}")
        print(f"  Кампания пройдена до сложности: {DIFF[gd] if gd<3 else gd}")
    if 16 in b:
        s=b[16]
        print(f"  В игре: {fmt_time(s['playtime'])}   Смертей: {s['deaths']}   Убийств: {s['kills']:,}")
        print(f"  Макс.урон: {s['greatest_damage']:,}   Криты нанесено: {s['crits_inflicted']:,}")
    if 8 in b:
        allsk=b[8]['skills']
        mast=[s for s in allsk if '_classtraining_class' in s['name'] and s['level']>0]
        # real named skills: exclude mastery bars, default/tierX generic nodes
        real=[s for s in allsk if s['level']>0
              and '_classtraining_class' not in s['name']
              and not s['name'].split('/')[-1].startswith('default')
              and not s['name'].split('/')[-1].startswith('tier')]
        if mast:
            mlbl={'class01':'Soldier','class02':'Demolitionist','class03':'Occultist','class04':'Nightblade',
                  'class05':'Arcanist','class06':'Shaman','class07':'Inquisitor','class08':'Necromancer','class09':'Oathkeeper'}
            def mn(s):
                key=s['name'].split('_classtraining_')[-1].replace('.dbr','')
                return mlbl.get(key,key)
            print("  Мастерства: " + ", ".join(f"{mn(s)} {s['level']}/50" for s in mast)
                  + f"   (разрешено классов: {b[8]['masteries_allowed']})")
        if real:
            print(f"  Прокачанные умения ({len(real)}):")
            for s in sorted(real,key=lambda x:-x['level']):
                nm=s['name'].split('/')[-1].replace('.dbr','')
                print(f"      {nm:<26} lvl {s['level']}")
    if 13 in b:
        fac=[f for f in b[13]['factions'] if f['unlocked'] and f['value']!=0]
        if fac:
            print("  Репутация фракций:")
            for f in sorted(fac,key=lambda x:-x['value'])[:8]:
                nm=FACTIONS[f['idx']] if f['idx']<len(FACTIONS) else f"faction#{f['idx']}"
                print(f"      {nm:<26} {f['value']:>8,}")
    if '_errors' in b: print("  [warn]", b['_errors'])

if __name__=='__main__':
    base=os.environ.get("GD_SAVE_MAIN","C:/games/Steam/userdata/337375846/219990/remote/save/main")
    for folder in ['_Redhat','__yelowhut','_yelowhut']:
        C=parse(f"{base}/{folder}/player.gdc")
        summarize(folder,C)
