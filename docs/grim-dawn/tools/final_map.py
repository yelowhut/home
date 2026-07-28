# -*- coding: utf-8 -*-
import json, os
_jp=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','components.json')
comps=json.load(open(_jp,encoding='utf-8'))

# their original 45 components (name without comp prefix)
owned=['crackedlodestone','chippedclaw','serratedspike','frozenheart','searingember',
'scavengedplating','polishedemerald','mutagenicichor','festeringblood','batteredshell',
'corpsedust','ancientarmorplate','consecratedwrappings','chilledsteel','ectoplasm',
'lodestone','markofthetraveler','aethersoul','spinedcarapace','markofillusions',
'bristlyfur','blessedsteel','markofdreeg','soulshard','markofthemyrmidon',
'viciousjawbone','runestone','whetstone','spellwoventhreads','unholyinscription',
'rigidshell','deviltouchedammo','mutatedscales','viciousspikes','chainsofoleron',
'focusingprism','hollowedfang','restlessremains','hallowedground','arcanelens',
'riftstone','imbuedsilver','vengefulwraith','symbolofsolael','sanctifiedbone']

def find(name):
    for k,v in comps.items():
        if k.split('_',1)[1]==name: return k,v
    return None,None

ARMOR={'head':'Голова','shoulders':'Плечи','chest':'Торс','legs':'Ноги','hands':'Руки',
       'feet':'Ступни','amulet':'Амулет','ring':'Кольца','medal':'Медаль','waist':'Пояс'}
WEAP={'sword':'меч1h','sword2h':'меч2h','mace':'булава1h','mace2h':'булава2h','axe':'топор1h',
      'axe2h':'топор2h','dagger':'кинжал','scepter':'скипетр','spear2h':'копьё','ranged1h':'пистолет',
      'ranged2h':'ружьё','offhand':'фокус','shield':'ЩИТ'}

def slotnames(slots):
    arm=[ARMOR[s] for s in slots if s in ARMOR]
    wp=[s for s in slots if s in WEAP]
    # summarize weapons
    if len(wp)>=10: wtxt=['ЛЮБОЕ оружие']
    elif set(wp)>= {'sword','mace','axe','dagger','scepter'} and 'ranged1h' not in wp: wtxt=['ближ.оружие']
    else: wtxt=[WEAP[s] for s in wp]
    return arm+wtxt

print("КОМПОНЕНТ                     ТОЧНЫЕ СЛОТЫ (из базы игры)            СОПРОТ/СТАТЫ")
print("-"*95)
for name in owned:
    k,v=find(name)
    if not v:
        print(f"{name:28} ??? не найден"); continue
    slots=' / '.join(slotnames(v['slots'])) or v.get('desc','?')
    res=', '.join(f"{val} {n}" for n,val in v['resists'].items())
    ex=[]
    if v.get('armor'): ex.append(f"броня+{v['armor']}")
    if v.get('armor_absorb_pct'): ex.append(f"поглощ+{v['armor_absorb_pct']}%")
    if v.get('health'): ex.append(f"HP+{v['health']}")
    tail=(res+('  ['+', '.join(ex)+']' if ex else '')) or (('['+', '.join(ex)+']') if ex else 'бонус — случайный')
    print(f"{name:28} {slots:38} {tail}")
