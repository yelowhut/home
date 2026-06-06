#!/usr/bin/env python3
"""
HayDay (Supercell) shared_prefs decrypt/encrypt tool.

Scheme (verified against com.supercell.hayday 1.70.96, class
com.supercell.id.scid_plugin.SecurePreferences, and the public
Galaxy1036/scCredentialsDecrypt tool):

  - key names  : AES-256/ECB/PKCS5  (base64, NO_WRAP)
  - values     : AES-256/CBC/PKCS5  (base64, NO_WRAP)
  - IV         : first 16 bytes of "fldsjfodasjifudslfjdsaofshaufihadsf"
  - AES key    : SHA-256(seed)
  - seed       : either
                   * generate_key(<package_name>)   -> device-INDEPENDENT
                       (storage_new.xml, com.supercell.id.util.SharedDataStorage.xml)
                   * <android_id> (raw, no generate_key) -> device-BOUND
                       (older storage.xml)

Usage:
  python3 hd_prefs_crypto.py decrypt <file.xml> --pkg com.supercell.hayday
  python3 hd_prefs_crypto.py decrypt <file.xml> --android-id 0123456789abcdef
"""
import argparse, base64, hashlib, re, sys
from Crypto.Cipher import AES

XOR_MAP = b'fLxYB9M84AbeusERMY9YFzVG'
IV = b'fldsjfodasjifudslfjdsaofshaufihadsf'[:16]

def generate_key(package_name: bytes) -> bytes:
    out = []
    for i, v in enumerate(package_name):
        out.append(((v ^ XOR_MAP[i % len(XOR_MAP)]) & 0x1f) + 48)
    out.reverse()
    return bytes(out)

def aes_key(seed: bytes) -> bytes:
    return hashlib.sha256(seed).digest()

def _unpad(b: bytes) -> bytes:
    return b[:-b[-1]]

def _pad(b: bytes) -> bytes:
    n = 16 - len(b) % 16
    return b + bytes([n]) * n

def dec(b64: str, key: bytes, ecb: bool) -> str:
    raw = base64.b64decode(b64)
    c = AES.new(key, AES.MODE_ECB) if ecb else AES.new(key, AES.MODE_CBC, IV)
    return _unpad(c.decrypt(raw)).decode('utf-8')

def enc(text: str, key: bytes, ecb: bool) -> str:
    c = AES.new(key, AES.MODE_ECB) if ecb else AES.new(key, AES.MODE_CBC, IV)
    return base64.b64encode(c.encrypt(_pad(text.encode('utf-8')))).decode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['decrypt'])
    ap.add_argument('file')
    ap.add_argument('--pkg', help='package name, e.g. com.supercell.hayday')
    ap.add_argument('--android-id', help='raw android_id (for old device-bound storage.xml)')
    a = ap.parse_args()
    if a.pkg:
        key = aes_key(generate_key(a.pkg.encode()))
    elif a.android_id:
        key = aes_key(a.android_id.encode())
    else:
        sys.exit('need --pkg or --android-id')

    txt = open(a.file, encoding='utf-8').read()
    pairs = re.findall(r'<string name="([^"]+)">([^<]*)</string>', txt)
    ok = 0
    for n, v in pairs:
        try:
            name = dec(n, key, True)
            val = dec(v, key, False) if v else ''
            ok += 1
            print(f"  {name:30} = {val!r}")
        except Exception:
            print(f"  <undecryptable: {n[:24]}...>")
    print(f"# decrypted {ok}/{len(pairs)} entries")

if __name__ == '__main__':
    main()
