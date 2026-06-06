# HayDay `shared_prefs` Encryption — Reverse‑Engineering Notes

> **TL;DR** — Modern HayDay (`com.supercell.hayday`) no longer stores its
> `shared_prefs` as plaintext XML. Every key **name** and **value** is
> AES‑encrypted then base64‑wrapped. The current `storage_new.xml` is keyed
> off the **package name** (device‑independent → fully decryptable); the older
> `storage.xml` is keyed off the **device `android_id`** (device‑bound).
> A reusable decryptor lives next to this file: [`hd_prefs_crypto.py`](./hd_prefs_crypto.py).

---

## 1. What was analysed

| Artefact | Notes |
|---|---|
| `Hay+Day_1.70.96_APKPure.xapk` | The real Supercell game. Base apk `com.supercell.hayday.apk`, 5 dex files, plus split configs + native libs. |
| `HD Manager_new*.apk` | Third‑party HayDay bot (`ru.xomka.haydaymanager`). All 3 variants are **byte‑identical** (md5 `cd829248ae2e3b4253e82a0210d1c8de`). Contains a `Cryptor` class implementing the same scheme. |
| `EMS_SELL_BOT-340.apk` | Larger third‑party bot (not needed for the conclusion). |
| `SEND ME 1 COIN!/` | A real `shared_prefs` dump from a HayDay install — used as ground truth for verification. **Contains a live account token; do not commit.** |

Confirmation that the game itself implements the scheme: the IV literal
`fldsjfodasjifuds` appears in the game's **`classes4.dex`**, class
`com.supercell.id.scid_plugin.SecurePreferences`.

---

## 2. The encryption scheme

| Element | Value |
|---|---|
| Key‑name cipher | `AES‑256/ECB/PKCS5Padding` |
| Value cipher | `AES‑256/CBC/PKCS5Padding` |
| IV (CBC) | first 16 bytes of `fldsjfodasjifudslfjdsaofshaufihadsf` → `fldsjfodasjifuds` |
| AES key | `SHA‑256(seed)` (32 bytes → AES‑256) |
| Encoding | Base64 (`NO_WRAP`) of the ciphertext, in both `name=` and the value |

So a stored entry `<string name="ENC_NAME">ENC_VALUE</string>` is:

```
ENC_NAME  = base64( AES_ECB_encrypt( SHA256(seed), plaintext_key  ) )
ENC_VALUE = base64( AES_CBC_encrypt( SHA256(seed), IV, plaintext_value ) )
```

A telltale sign in the XML: 24‑character base64 strings ending in `==` are a
single 16‑byte AES block. Plain base64 would decode to readable text; these
decode to binary — the signature of a real cipher on top.

### Decompiled game source (excerpt)

`com.supercell.id.scid_plugin.SecurePreferences` (HayDay 1.70.96, `classes4.dex`):

```java
private static final String KEY_TRANSFORMATION = "AES/ECB/PKCS5Padding";   // key names
private static final String TRANSFORMATION     = "AES/CBC/PKCS5Padding";   // values
private byte[] createKeyBytes(String s) {                 // key = SHA-256(seed)
    MessageDigest md = MessageDigest.getInstance("SHA-256");
    md.reset();
    return md.digest(s.getBytes("UTF-8"));
}
private IvParameterSpec getIv() {                          // IV = "fldsjfodasjifuds"
    byte[] iv = new byte[writer.getBlockSize()];
    System.arraycopy("fldsjfodasjifudslfjdsaofshaufihadsf".getBytes(), 0, iv, 0, writer.getBlockSize());
    return new IvParameterSpec(iv);
}
// constructor: SecurePreferences(Context, prefsFileName, SEED, encryptKeys)
```

---

## 3. Key derivation — the `seed`

Two seed sources were observed. Both end in `SHA‑256(seed)`.

### 3a. Package‑name seed → **device‑INDEPENDENT**

Used by `storage_new.xml` and the Supercell‑ID stores. From the game's
`EncryptedStorage$securePreferences$2.invoke()`:

```java
char[] map = {102,76,120,89,66,57,77,56,52,65,98,101,117,115,69,82,77,89,57,89,70,122,86,71};
//            = "fLxYB9M84AbeusERMY9YFzVG"
String pkg = context.getPackageName();          // "com.supercell.hayday"
String seed = "";
for (int i = pkg.length() - 1; i >= 0; i--) {     // note: reversed
    int c = ((pkg.charAt(i) ^ map[i % 24]) & 31) + 48;
    seed += (char) c;
}
new SecurePreferences(context, preferenceName, seed, /*encryptKeys=*/true);
```

Python equivalent (this is exactly the `generate_key()` in the public
`Galaxy1036/scCredentialsDecrypt` tool):

```python
XOR_MAP = b'fLxYB9M84AbeusERMY9YFzVG'
def generate_key(pkg: bytes) -> bytes:
    out = [((v ^ XOR_MAP[i % len(XOR_MAP)]) & 0x1f) + 48 for i, v in enumerate(pkg)]
    out.reverse()
    return bytes(out)
# generate_key(b"com.supercell.hayday") == "0HMDC=MI9726MM<AGE35"
# aes_key = sha256(that)
```

Because the only input is the (constant) package name, **anyone** can derive
this key — no device secret involved.

### 3b. `android_id` seed → **device‑BOUND**

Used by the older `storage.xml`. The seed is the raw device
`Settings.Secure.ANDROID_ID` (the `--android-id` path in the python tool,
*without* `generate_key`). Decryption requires that specific install's
`android_id`, which is **not recoverable** from the prefs files alone.

---

## 4. Which file uses which key (verified against the real dump)

Running the package‑name key against every file in `SEND ME 1 COIN!/`:

| File | Result | Scheme |
|---|---|---|
| `storage_new.xml` | **24/24 decrypt** ✅ | custom AES, **package‑name** seed |
| `storage.xml` | 0/24 ❌ | custom AES, **android_id** seed (device‑bound) |
| `com.supercell.id.util.SharedDataStorage.xml` | mixed | AndroidX Security / **Tink** (`AesGcmKey`/`AesSivKey`) + one custom‑AES entry |
| `localPrefs.xml`, `MyPreferences.xml`, `__hs_lite_sdk_store.xml`, `supersonic_shared_preferen.xml` | not pkg‑keyed | custom AES, non‑package seed |
| `paid_storage_sp.xml`, `com.google.android.gms.measurement.prefs.xml`, `admob.xml`, `SharedDataWhitelist.xml`, … | plaintext | not encrypted |

### Decrypted `storage_new.xml` (account token redacted)

```
YoungPlayerKnown      = true          GameSCIDSocial       = TRUE
music_env3            = true          sounds_env3          = true
language_code_env3    = EN            CachedLocation       = DE
lower_env3            = 37608379      higher_env3          = 25      # account id = 25-37608379
SCIDGuestLow_env3     = 37608379      SCIDGuestHigh_env3   = 25
tier_env3             = 1             good_performance_env3= true
current_theme         = _winter       current_theme_loading= sc/loading_screen_winter.sc
current_theme_end     = 1704355202    INSTALL_ID           = 7wGMQOFW
titan.deviceinformation.sent = v1
PLAY_REFERRER_URL     = utm_source=google-play&utm_medium=organic
passToken_env3        = <REDACTED — Supercell login token>
SCIDGuestPass_env3    = <REDACTED — same token>
```

> ⚠️ **`passToken_env3` is the account's login credential.** Possession of
> `storage_new.xml` + the (public) package key is enough to extract it. This is
> why these files get traded. Never commit a real dump to the repo.

---

## 5. "What changed" — summary

1. HayDay moved its local state out of plaintext XML into the custom
   AES‑ECB(names)/AES‑CBC(values) scheme above.
2. It introduced **`storage_new.xml`**, keyed off the **package name**
   (portable/restorable across devices — and therefore decryptable by anyone),
   alongside the legacy **`storage.xml`** keyed off the device `android_id`.
3. The Supercell‑ID component additionally adopted **AndroidX Security / Tink**
   (`AesGcmKey` / `AesSivKey`, Keystore‑backed) for
   `com.supercell.id.util.SharedDataStorage.xml` — the strongest tier.

Cross‑confirmation: the identical scheme (same IV, same `generate_key`
constant, same ECB‑names/CBC‑values split) appears independently in
(a) the real game binary, (b) the `HD Manager` bot's `ru.xomka.haydaymanager.Cryptor`,
and (c) the public `Galaxy1036/scCredentialsDecrypt` tool.

---

## 6. How to decrypt

```bash
pip install pycryptodome
python3 docs/hayday/hd_prefs_crypto.py decrypt storage_new.xml --pkg com.supercell.hayday
# old device-bound file (needs that install's android_id):
python3 docs/hayday/hd_prefs_crypto.py decrypt storage.xml --android-id <ANDROID_ID>
```

---

## 7. Environment / tooling notes

- This machine has **no Java** → `jadx`/`apktool`/`baksmali` unavailable.
- Decompilation done with `androguard` (`pip install --user androguard`).
  **Quirk in this build:** `EncodedMethod.get_instructions()` and the analysis
  xref helpers (`get_xref_from`) return empty — they're effectively no‑ops.
  Use class‑level `DalvikVMFormat.get_classes()` → `c.get_source()` (the DAD
  decompiler) and grep the source text instead.
- `androguard.db*` files are scratch session state — safe to delete / gitignore.
- The 1.70.96 APKPure build also bundles **Flutter** (`libapp.so` + `libflutter.so`
  with the `pointycastle` Dart crypto lib) and several ad SDKs
  (applovin / ironsource / vungle), pulled in via the `com.supercell.id` /
  `com.supercell.titan` modules — not the C++ game core.

## 8. Open questions

- Exact game version that flipped `storage.xml` → `storage_new.xml` is not
  pinned down (no clean public changelog). Diffing two HayDay APK versions
  would confirm it.
- The old `storage.xml` can be decrypted only with the originating device's
  `android_id`.

## 9. Sources

- `Galaxy1036/scCredentialsDecrypt` — https://github.com/Galaxy1036/scCredentialsDecrypt
- "Clash of Clans – Supercell new encryption reverse engineering" — http://www.giovanni-rocca.com/clash-clans-supercell-new-encryption-reverse-engineering/
- Primary binaries in this folder (`Hay+Day_1.70.96`, `HD Manager_new`).
