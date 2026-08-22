# -*- coding: utf-8 -*-
"""Копирование персонажа Grim Dawn с новым именем.

Имя зашито в зашифрованном player.gdc; эволюция ключа шифра зависит от каждого
зашифрованного байта, поэтому изменение имени сдвигает кейстрим всего файла.
Вместо полной перезаписи (потребовался бы формат всех блоков) инструмент:

  1. Перешифровывает заголовок (magic..uid), блок 1 и блок 2 — их побайтовая
     структура известна (блок 1 v5 сверен с gd-edit: compass, skill-help,
     alt-weapon-set, player-texture, loot-filters; проверено на 6 сейвах).
  2. 16-байтовый UID персонажа сохраняется В ТОЧНОСТИ: файлы квестов
     levels_world001.map/*/quests.gdd привязаны к персонажу по этому UID,
     при несовпадении игра стирает прогресс квестов и кампании.
  3. Состояние ключа выравнивается с оригиналом подбором младших 16 бит
     мантиссы float-полей health/energy в конце блока 2 (дрейф ≤ ~8 HP и
     ~2 энергии — это текущие значения ресурсов, в игре они восстанавливаются).
  4. С блока 3 и до конца файл копируется байт-в-байт — контрольные суммы
     остальных блоков остаются валидными без знания их формата.

Использование:
    python gdrename.py <src player.gdc> <dst player.gdc> <NewName>
"""
import os, struct, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdchar import R, parse


def f32(u):
    return struct.unpack('<f', struct.pack('<I', u & 0xFFFFFFFF))[0]


class W:
    """Кодировщик, зеркальный gdchar.R."""
    def __init__(self, seed4):
        self.out = bytearray(seed4)
        k = struct.unpack('<I', seed4)[0] ^ 0x55555555
        self.key = k
        self.t = [0] * 256
        for i in range(256):
            k = ((k >> 1) | (k << 31)) & 0xFFFFFFFF
            k = (k * 39916801) & 0xFFFFFFFF
            self.t[i] = k

    def byte(self, p):
        e = (p ^ (self.key & 0xFF)) & 0xFF
        self.out.append(e)
        self.key ^= self.t[e]

    def u32(self, v):
        e = (v ^ self.key) & 0xFFFFFFFF
        eb = e.to_bytes(4, 'little')
        self.out += eb
        for b in eb:
            self.key ^= self.t[b]

    def sbytes(self, bs):
        for p in bs:
            self.byte(p)

    def s(self, txt):
        b = txt.encode('latin-1')
        self.u32(len(b))
        self.sbytes(b)

    def ws(self, txt):
        b = txt.encode('utf-16-le')
        self.u32(len(b) // 2)
        self.sbytes(b)

    def checksum(self):
        # контрольная сумма = текущее состояние ключа; записывается как есть,
        # состояние не меняет
        self.out += self.key.to_bytes(4, 'little')

    def raw_len(self, length):
        # поле длины блока: xor с ключом, без обновления состояния
        self.out += ((length ^ self.key) & 0xFFFFFFFF).to_bytes(4, 'little')


def read_char(data):
    """Строгий разбор до конца блока 2. Все контрольные суммы сверяются с
    вычисленным состоянием ключа (как это делает игра), а не ресинкаются."""
    r = R(data)
    c = {}
    c['magic'] = r.u32()
    assert c['magic'] == 0x58434447, hex(c['magic'])
    c['version'] = r.u32()
    c['name'] = r.ws()
    c['sex'] = r.byte()
    c['class_tag'] = r.s()
    c['level'] = r.u32()
    c['hardcore'] = r.byte()
    c['expansion'] = r.byte()
    assert int.from_bytes(data[r.pos:r.pos + 4], 'little') == r.key, \
        'контрольная сумма заголовка != состоянию ключа'
    r.skip_checksum()
    c['data_version'] = r.u32()
    c['uid'] = r.sbytes(16)

    def block_open(want_bid):
        bid = r.i32()
        assert bid == want_bid, f'ожидался блок {want_bid}, найден {bid}'
        length = r.raw4_noupd()
        return r.pos + length

    def block_close(end, tag):
        assert r.pos == end, f'блок {tag}: разобрано не до конца ({end - r.pos} байт)'
        assert int.from_bytes(data[r.pos:r.pos + 4], 'little') == r.key, \
            f'контрольная сумма блока {tag} != состоянию ключа'
        r.skip_checksum()

    # блок 1 (info), структура версии 5 сверена с gd-edit
    end = block_open(1)
    c['b1_len'] = end - r.pos
    b1 = {}
    b1['version'] = r.u32()
    assert b1['version'] == 5, f'block1 version {b1["version"]} != 5'
    b1['in_main_quest'] = r.byte(); b1['has_been_in_game'] = r.byte()
    b1['last_difficulty'] = r.byte(); b1['greatest_difficulty'] = r.byte()
    b1['iron'] = r.u32()
    b1['greatest_survival_diff'] = r.byte(); b1['tributes'] = r.u32()
    b1['compass'] = r.byte(); b1['skill_help'] = r.byte()
    b1['alt_weapon_set'] = r.byte(); b1['alt_weapon_set_enabled'] = r.byte()
    b1['texture'] = r.s()
    nf = r.u32()
    assert nf < 256, f'loot-filters {nf}'
    b1['loot_filters'] = r.sbytes(nf)
    c['b1'] = b1
    block_close(end, 1)

    # блок 2 (bio); floats храним сырыми u32
    end = block_open(2)
    c['b2_len'] = end - r.pos
    b2 = {}
    b2['version'] = r.u32()
    assert b2['version'] == 8, f'block2 version {b2["version"]} != 8'
    b2['ints'] = [r.u32() for _ in range(6)]
    b2['floats'] = [r._u(4) for _ in range(5)]  # physique,cunning,spirit,health,energy
    c['b2'] = b2
    key_at_end = r.key
    block_close(end, 2)

    c['key_after_b2'] = key_at_end  # состояние ключа на конце контента блока 2
    c['rest_off'] = r.pos           # начало блока 3: отсюда до конца — verbatim
    return c


def _write_through_cunning(c, new_name):
    """Пишет новый файл до поля cunning (включительно)."""
    w = W(c['seed'])
    w.u32(c['magic']); w.u32(c['version'])
    w.ws(new_name)
    w.byte(c['sex']); w.s(c['class_tag']); w.u32(c['level'])
    w.byte(c['hardcore']); w.byte(c['expansion'])
    w.checksum()
    w.u32(c['data_version'])
    w.sbytes(c['uid'])                      # UID сохраняется байт-в-байт

    b1 = c['b1']
    w.u32(1); w.raw_len(c['b1_len'])
    w.u32(b1['version'])
    w.byte(b1['in_main_quest']); w.byte(b1['has_been_in_game'])
    w.byte(b1['last_difficulty']); w.byte(b1['greatest_difficulty'])
    w.u32(b1['iron'])
    w.byte(b1['greatest_survival_diff']); w.u32(b1['tributes'])
    w.byte(b1['compass']); w.byte(b1['skill_help'])
    w.byte(b1['alt_weapon_set']); w.byte(b1['alt_weapon_set_enabled'])
    w.s(b1['texture'])
    w.u32(len(b1['loot_filters'])); w.sbytes(b1['loot_filters'])
    w.checksum()

    b2 = c['b2']
    w.u32(2); w.raw_len(c['b2_len'])
    w.u32(b2['version'])
    for v in b2['ints']:
        w.u32(v)
    f = b2['floats']
    w.u32(f[0]); w.u32(f[1])                # physique, cunning
    return w


def rename_copy(data, new_name):
    c = read_char(data)
    c['seed'] = data[0:4]
    f = c['b2']['floats']
    target = c['key_after_b2']

    w = _write_through_cunning(c, new_name)
    t = w.t
    S0 = w.key                              # состояние перед spirit
    pe2 = (f[4] >> 16) & 0xFF
    pe3 = (f[4] >> 24) & 0xFF

    pairs = {}
    for a in range(256):
        ta = t[a]
        for b in range(a, 256):
            pairs.setdefault(ta ^ t[b], (a, b))

    # трёхуровневый каскад свободных младших битов мантисс (перебор от
    # минимального дрейфа): spirit(16) -> health(16) -> energy(16, MITM).
    # Вероятность успеха на одну итерацию spirit ~40%, поэтому spirit почти
    # всегда остаётся нетронутым или с дрейфом ~ULP.
    orig_slo = f[2] & 0xFFFF
    orig_hlo = f[3] & 0xFFFF
    h_order = sorted(range(65536), key=lambda v: abs(v - orig_hlo))
    S0b = [(S0 >> (8 * i)) & 0xFF for i in range(4)]
    es2 = ((f[2] >> 16) & 0xFF) ^ S0b[2]
    es3 = ((f[2] >> 24) & 0xFF) ^ S0b[3]
    for s_lo in sorted(range(65536), key=lambda v: abs(v - orig_slo)):
        es0 = (s_lo & 0xFF) ^ S0b[0]
        es1 = ((s_lo >> 8) & 0xFF) ^ S0b[1]
        S = S0 ^ t[es0] ^ t[es1] ^ t[es2] ^ t[es3]     # перед health
        Sb = [(S >> (8 * i)) & 0xFF for i in range(4)]
        eh2 = ((f[3] >> 16) & 0xFF) ^ Sb[2]
        eh3 = ((f[3] >> 24) & 0xFF) ^ Sb[3]
        base = S ^ t[eh2] ^ t[eh3]
        for h_lo in h_order:
            eh0 = (h_lo & 0xFF) ^ Sb[0]
            eh1 = ((h_lo >> 8) & 0xFF) ^ Sb[1]
            S1 = base ^ t[eh0] ^ t[eh1]                # перед energy
            S1b = [(S1 >> (8 * i)) & 0xFF for i in range(4)]
            ee2 = pe2 ^ S1b[2]
            ee3 = pe3 ^ S1b[3]
            hit = pairs.get(target ^ S1 ^ t[ee2] ^ t[ee3])
            if hit is None:
                continue
            ee0, ee1 = hit
            e_lo = (ee0 ^ S1b[0]) | ((ee1 ^ S1b[1]) << 8)
            new_spirit = (f[2] & 0xFFFF0000) | s_lo
            new_health = (f[3] & 0xFFFF0000) | h_lo
            new_energy = (f[4] & 0xFFFF0000) | e_lo
            w.u32(new_spirit)
            w.u32(new_health)
            w.u32(new_energy)
            assert w.key == target, 'состояние ключа не сошлось'
            w.checksum()
            out = bytes(w.out) + data[c['rest_off']:]
            drift = (f32(new_spirit) - f32(f[2]),
                     f32(new_health) - f32(f[3]),
                     f32(new_energy) - f32(f[4]))
            return out, drift
    raise RuntimeError('компенсация не найдена (не должно случаться)')


def _parse_tmp(data):
    fd, p = tempfile.mkstemp(suffix='.gdc')
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
        c = parse(p)
        assert '_errors' not in c['blocks'], c['blocks'].get('_errors')
        return c
    finally:
        os.unlink(p)


def verify_copy(orig, copy, new_name):
    """Доказательная сверка копии с оригиналом."""
    co, cc = read_char(orig), read_char(copy)   # строгие assert'ы внутри
    assert cc['name'] == new_name, cc['name']
    assert cc['uid'] == co['uid'], 'UID изменился — сломает привязку quests.gdd'
    for k in ('magic', 'version', 'sex', 'class_tag', 'level', 'hardcore',
              'expansion', 'data_version', 'b1_len', 'b2_len', 'key_after_b2'):
        assert cc[k] == co[k], k
    assert cc['b1'] == co['b1'], 'блок 1 отличается'
    assert cc['b2']['version'] == co['b2']['version']
    assert cc['b2']['ints'] == co['b2']['ints'], 'блок 2 (ints) отличается'
    for i, (a, b) in enumerate(zip(co['b2']['floats'], cc['b2']['floats'])):
        assert abs(f32(a) - f32(b)) <= 16.0, f'float {i}: {f32(a)} -> {f32(b)}'
    assert copy[cc['rest_off']:] == orig[co['rest_off']:], 'остаток файла отличается'

    # цепочка блоков хвоста: id разумны, длины сходятся точно к концу файла
    pos, key, t = cc['rest_off'], cc['key_after_b2'], R(copy).t
    bids = [1, 2]
    while pos < len(copy):
        enc = copy[pos:pos + 4]
        bid = int.from_bytes(enc, 'little') ^ key
        for b in enc:
            key ^= t[b]
        length = int.from_bytes(copy[pos + 4:pos + 8], 'little') ^ key
        pos += 8
        assert 0 <= bid < 64 and 0 < length <= len(copy) - pos - 4, (bid, length)
        pos += length
        key = int.from_bytes(copy[pos:pos + 4], 'little')
        pos += 4
        bids.append(bid)
    assert pos == len(copy)

    # полный парс обоих файлов и сравнение всех распознанных данных
    po, pc = _parse_tmp(orig), _parse_tmp(copy)
    assert pc.pop('name') == new_name and po.pop('name')
    for d in (po, pc):
        for fld in ('spirit', 'health', 'energy'):
            d['blocks'].get(2, {}).pop(fld, None)
    assert po == pc, 'распарсенные данные копии отличаются от оригинала'
    return bids


if __name__ == '__main__':
    src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
    data = open(src, 'rb').read()
    out, (ds, dh, de) = rename_copy(data, name)
    bids = verify_copy(data, out, name)
    with open(dst, 'wb') as fh:
        fh.write(out)
    print(f'OK: {dst} — имя "{name}", UID сохранён, блоки {bids}, '
          f'дрейф spirit {ds:+.4f} / HP {dh:+.3f} / энергии {de:+.3f}, сверка пройдена')
