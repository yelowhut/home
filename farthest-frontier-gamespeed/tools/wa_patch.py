"""Patch Farthest Frontier work-area radii directly in resources.assets — no mod loader.

Usage:
    python wa_patch.py --out <file>            write patched copy here (safe, default)
    python wa_patch.py --inplace               patch the game file (a .bak is made first)
    python wa_patch.py --verify <file>          re-read a patched file and print its radii

Multipliers live in MULT below; 1.0 leaves a class untouched. Close the game first -
the file is replaced on disk. Needs UnityPy and TypeTreeGeneratorAPI (pip install).

The radii are prefab defaults, so this needs no mod loader at all: it is the static
equivalent of what the WorkAreaOverhauled mod did at runtime.
"""
import argparse
import gc
import os
import shutil
import struct
import sys

import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

GAME = r'C:\games\Farthest Frontier'
DATA = os.path.join(GAME, 'Farthest Frontier_Data')
ASSETS = os.path.join(DATA, 'resources.assets')
UNITY = '2022.3.62f3'

# class -> (radius field, multiplier)
MULT = {
    'ArboristBuilding': ('harvestRadius', 1.0),
    'FishingShack': ('fishingRadius', 1.0),
    'ForagerShack': ('foragingRadius', 1.0),
    'HunterBuilding': ('huntingRadius', 1.0),
    'MineralSiteMine': ('miningRadius', 1.0),
    'RatCatcherBuilding': ('workRadius', 1.0),
    'WorkCamp': ('workRadius', 1.0),
}

_orig_get_nodes = TypeTreeGenerator.get_nodes


def _get_nodes(self, assembly, fullname):
    """UnityPy appends '.dll'; the il2cpp generator only knows 'Assembly-CSharp'."""
    if assembly.endswith('.dll'):
        try:
            return _orig_get_nodes(self, assembly[:-4], fullname)
        except Exception:
            pass
    return _orig_get_nodes(self, assembly, fullname)


TypeTreeGenerator.get_nodes = _get_nodes


def script_map():
    env = UnityPy.load(os.path.join(DATA, 'globalgamemanagers.assets'))
    return {o.path_id: o.read().m_ClassName for o in env.objects if o.type.name == 'MonoScript'}


def class_of(obj, scripts):
    raw = obj.get_raw_data()
    if len(raw) < 28:
        return None
    file_id, path_id = struct.unpack_from('<iq', raw, 16)
    if file_id == 0:
        return scripts.get(path_id)
    exts = obj.assets_file.externals
    if file_id - 1 >= len(exts):
        return None
    if os.path.basename(exts[file_id - 1].path) != 'globalgamemanagers.assets':
        return None
    return scripts.get(path_id)


def go_name(obj, by_id):
    fid, pid = struct.unpack_from('<iq', obj.get_raw_data(), 0)
    if fid == 0 and pid in by_id:
        return by_id[pid].read().m_Name
    return ''


def open_env(path):
    gen = TypeTreeGenerator(UNITY)
    gen.load_local_game(GAME)
    env = UnityPy.load(path)
    env.typetree_generator = gen
    return env


def run(src, out, scripts):
    env = open_env(src)
    by_id = {o.path_id: o for o in env.objects}
    changed = 0
    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        cls = class_of(obj, scripts)
        if cls not in MULT:
            continue
        field, mult = MULT[cls]
        tree = obj.read_typetree()
        # public name is often a property over a serialized backing field
        field = next((k for k in (field, '_' + field) if k in tree), None)
        if field is None:
            print('  !! %-20s %-32s no %s field' % (cls, go_name(obj, by_id), MULT[cls][0]))
            continue
        old = tree[field]
        new = round(old * mult, 3)
        mark = ' ' if new == old else '*'
        print('%s %-20s %-32s %-14s %8.2f -> %.2f' % (mark, cls, go_name(obj, by_id), field, old, new))
        if new == old:
            continue
        tree[field] = new
        obj.save_typetree(tree)
        changed += 1

    if not changed:
        print('\nno value changed - nothing written')
        return
    data = env.file.save()
    with open(out, 'wb') as f:
        f.write(data)
    print('\n%d prefabs patched -> %s (%.1f MB)' % (changed, out, len(data) / 1024 ** 2))


def verify(path, scripts):
    env = open_env(path)
    by_id = {o.path_id: o for o in env.objects}
    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        cls = class_of(obj, scripts)
        if cls not in MULT:
            continue
        field = MULT[cls][0]
        tree = obj.read_typetree()
        key = next((k for k in (field, '_' + field) if k in tree), field)
        print('  %-20s %-32s %-14s %s' % (cls, go_name(obj, by_id), key, tree.get(key)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    ap.add_argument('--inplace', action='store_true')
    ap.add_argument('--verify', default=None)
    ap.add_argument('--mult', action='append', default=[],
                    metavar='CLASS=X', help='override a multiplier, or ALL=X for every class')
    a = ap.parse_args()

    for spec in a.mult:
        name, _, value = spec.partition('=')
        value = float(value)
        if name.upper() == 'ALL':
            for k in MULT:
                MULT[k] = (MULT[k][0], value)
        elif name in MULT:
            MULT[name] = (MULT[name][0], value)
        else:
            sys.exit('unknown class %r; known: %s' % (name, ', '.join(sorted(MULT))))

    scripts = script_map()

    if a.verify:
        verify(a.verify, scripts)
        return

    if a.inplace:
        bak = ASSETS + '.bak'
        if not os.path.exists(bak):
            print('backing up -> %s' % bak)
            shutil.copy2(ASSETS, bak)
        tmp = ASSETS + '.new'
        run(ASSETS, tmp, scripts)
        if os.path.exists(tmp):
            # UnityPy keeps the source file open; drop it or Windows denies the replace
            gc.collect()
            os.replace(tmp, ASSETS)
            print('game file replaced (original kept as resources.assets.bak)')
        return

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources.assets.patched')
    run(ASSETS, out, scripts)


main()
