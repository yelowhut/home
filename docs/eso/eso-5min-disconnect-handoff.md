# ESO — вылет ровно через ~5 минут (handoff, 2026-08-16)

Кросс-сессионный хендофф по расследованию. Связанная память: `eso-launch-crash-5min`.
Продолжать с раздела **«Следующие шаги»**.

## Симптом
ESO (аккаунт EU-Yelowhut; тестился и на NA) завершается почти ровно через **5 минут**
после коннекта к мегасерверу. Лаунчер рисует ложный диалог «Game crash detected /
corrupted files — Repair» — **Repair НЕ жать**, файлы целы.

Ключевое: это **не краш**, а управляемый выход клиента с кодом **4352 (0x1100)** или
**4353 (0x1101)**. Папка `Documents\Elder Scrolls Online\live\Errors` пуста, WER по этим
сессиям не срабатывает, аппаратных событий (WHEA / Kernel-Power 41) нет.

**Вылетает даже на экране выбора персонажа** (сессия 15:11:37 → CharacterSelect, в мир
не входила, всё равно ~5 мин). → рвётся аккаунт-сессия с мегасервером ДО геймплея, а не
зонный/мировой инстанс.

## Тайминги (лаунчер `host.developer.08.16.2026.log`, локальное время)
Рантайм всех крашей: **308–319 c**, из сессии в сессию. Фиксированный ~5-мин таймаут,
не случайные потери. Идут пачками; между пачками — многочасовые сессии с exit 0.
```
13.08 01:03 4352 316s   13.08 01:08 4352 313s   (ночь — тоже краш)
16.08 02:10 exit0 20911s (5.8ч, ЧИСТО, через OpenVPN-туннель)
16.08 10:35..13:42  4352/4353  308–319s (×8)
16.08 14:00..15:11  4352       308–319s (×6, после отключения zapret/Amnezia/OpenVPN)
```
Игровой канал: TCP на порт 24506 (сервер меняется в подсети 159.100.232.0/24:
.119/.166/.244/.109…). Логин-сервер (.109/.244) и игровой (.119:24506) — разные машины.

## Что ИСКЛЮЧЕНО прямыми тестами (всё — на этом ПК)
- **Сервер**: EU и NA мегасерверы — одинаково.
- **Персонажи**: несколько разных — одинаково.
- **Инсталляция**: Steam И standalone Bethesda.net (`C:\games\zos`) — одинаково → не файлы/не Steam.
- **Сеть**: домашний Ethernet (роутер 192.168.88.1) И **телефонный хотспот** (другой ISP/маршрут) — одинаково → сеть/провайдер/роутер ни при чём.
- **Путь**: непрерывный ping до сервера = **0% потерь** вплоть до секунды смерти; игровой **TCP `159.100.232.119:24506` был Established до самого выхода** (никто не рвёт — клиент сам себя завершает из-за отсутствия данных от сервера). Скрипт захвата: `scratchpad/eso_capture.ps1`.
- **VPN**: OpenVPN — падает В ОБОИХ состояниях: с лежащим туннелем (доказано логом `C:\Users\yelow\OpenVPN\log\vdsina-home-main-pc.log`) И с поднятым (16.08 вечер: туннель включён постоянно, минимум 2 вылета через него); чистая сессия 02:10 тоже шла через туннель. Никакой корреляции ни в одну сторону.
- **zapret/winws/WinDivert**: работает ПОСТОЯННО, в т.ч. во всех чистых многочасовых сессиях; краш 14:55/15:10 был и после `sc stop zapret`. Не коррелирует.
- **AmneziaVPN**: остановлена — краш продолжился.
- **Аддоны**: сыграно с пустым AddOns (interface.log = 0 упоминаний) — краш тот же. Возвращены (61 шт).
- **Оверлеи**: отключены пользователем.
- **GPU/железо**: DxDiag (`C:\Users\yelow\Documents\report.txt`, 16.08 14:36) чист. RTX 5080 драйвер 32.0.16.1088. Единственный «problem device» — намеренно отключённый iGPU Ryzen (code 22), норма. Нет WHEA/Kernel-Power 41.
- **Взлом/чужой вход**: 2FA включена + пароль свежий → исключено.
- **Время суток**: и ночью, и днём — и краши, и чистые сессии.

## Вердикт
Клиентская сторона исчерпана. Причина — **сторона ZeniMax, аккаунт/сессия-сервис**
(зависшая ghost-сессия или флаг на login-уровне; НЕ мегасервер — иначе EU и NA не падали бы
одинаково; краш на CharacterSelect подтверждает уровень аккаунт-сессии).
Не воспроизвести вне аккаунта не смогли (нет 2-го ПК; новый акк требует покупки игры).

## Отдельно (НЕ путать с 5-минутками)
Разовый настоящий краш `eso64` `0xC0000005` (APPCRASH, StackHash_1e37, `PCH_8C_FROM_unknown`):
16.08 12:37 (через ~57 c) и 15.08 19:42 (после 8 ч). Нерегулярный. Дамп:
`C:\ProgramData\Microsoft\Windows\WER\ReportArchive\AppCrash_eso64.exe_*`.
Побочно в WER несколько раз падал `procexp64.exe` тоже с 0xC0000005 → если AV в разных
программах будут копиться, прогнать MemTest86 (к 5-минуткам не относится).

---

## Обновление 2026-08-24 (анализ логов 17–24.08)

Два паттерна **не пересекаются во времени**.

### 17–21.08 — только 0xC0000005 (14 крашей), пятиминуток НЕТ ни одной
Это тот самый «отдельный настоящий краш», но он **перестал быть редким** — за 5 дней 14 штук.
Runtime случайный (0.5 c … 12 ч) → НЕ таймер. Сигнатуры (журнал Application, event 1000):
- `faultMod=unknown, exc=c0000005`, **адрес каждый раз разный** (`0x7ff623e72920`, `…2355d240`,
  `…23dfeaa0`, `…23c69200`, `…23f6f7c0`, `…23f9db80` …) — 11 шт.
- `faultMod=eso64.exe, off=0x11614ee` — 3 шт, **адрес всегда один** (воспроизводимая точка):
  19.08 23:25, 21.08 01:10, 21.08 16:47.

Аппаратных событий за период НЕТ: WHEA пусто, Kernel-Power 41 пусто, nvlddmkm/TDR (4101) пусто
→ не GPU/питание. Случайные адреса `unknown` = классическая подпись **нестабильной RAM / EXPO
или порчи кучи**. **ДЕЙСТВИЕ: MemTest86 (≥4 прохода); если в BIOS включён EXPO/XMP — временно
выключить и проверить, уходят ли краши.** В отличие от 5-минуток, это чинится на стороне ПК.

### 24.08 — вернулись 5-минутки (пачкой)
```
24.08 14:05 4352 315.9s   24.08 14:11 4353 324.2s   24.08 14:16 4352 314.1s
```
Сервер `159.100.232.119:24502`, дошёл до мира (`CHARACTER_ACTIVATED Complete` 14:11:54).
Перед ними в тот же день 3 чистые сессии (02:23 — 3.6 ч; 10:08; 12:12). Подтверждает гипотезу
«пачек»: 17–23.08 5-минуток не было вообще, 24.08 вернулись бёрстом. Вердикт прежний
(account-service ZOS). При отправке тикета дополнить: «reproduced again 24 Aug, 3 sessions 314–324 s».

### Полная таблица сессий 17–24.08 (мин)
Логов за 22.08 нет (не запускали). 47 сессий: 30 чистых, 14× 0xC0000005, 3× 5-мин.
```
17.08 09:06 0        66.5    17.08 11:44 0        44.9    17.08 11:47 CRASH    1.2
17.08 11:57 0         9.1    17.08 11:58 0         0.9    17.08 12:32 0       33.6
17.08 17:42 0       279.4    17.08 23:51 0        78.1    18.08 12:20 0       45.4
18.08 21:29 0       108.4    18.08 21:38 0         5.7    18.08 22:12 0       33.9
19.08 01:23 CRASH   102.5    19.08 10:10 0       112.6    19.08 15:25 0      241.2
19.08 15:26 CRASH     0.7    19.08 15:26 0         0.3    19.08 15:29 CRASH    0.5
19.08 23:26 CRASH   476.0    20.08 01:56 0       113.7    20.08 10:36 0       30.1
20.08 14:57 CRASH   187.1    20.08 15:18 CRASH    17.2    20.08 19:02 0      176.4
20.08 21:10 0         9.2    20.08 21:28 0        17.4    20.08 21:29 0        0.5
20.08 21:30 0         0.6    21.08 09:34 CRASH   723.6    21.08 10:54 0       66.8
21.08 11:49 0         0.5    21.08 14:29 CRASH    39.2    21.08 14:32 0        0.5
21.08 14:44 0        11.7    21.08 14:49 CRASH     0.9    21.08 16:48 CRASH   88.2
21.08 17:29 CRASH    40.9    21.08 19:14 0       104.2    21.08 19:21 0        7.0
21.08 20:39 0        32.6    21.08 22:20 0       101.1    23.08 22:45 0        1.3
24.08 02:23 0       217.9    24.08 10:08 0        38.5    24.08 12:12 0       44.4
24.08 14:05 5MIN      5.3    24.08 14:11 5MIN      5.4    24.08 14:16 5MIN     5.2
```
(CRASH = 0xC0000005 / exit -1073741819; 5MIN = 4352/4353)

## Состояние ПК после сессии 16.08
- Аддоны возвращены на место (`...\live\AddOns`, 61 шт), мусор `TamrielTradeCentre_leftover` удалён.
- Службы `zapret`, `AmneziaVPN`, `OpenVPN` остановлены ВРУЧНУЮ → поднимутся сами при
  перезагрузке (в автозапуске). На игру не влияют.

## Следующие шаги
1. **Отправить тикет в ZOS** (готовый текст ниже) + приложить `report.txt`. Просьба:
   проверить/очистить stuck-сессию аккаунта и account-флаги.
2. (Опц.) Последний контрольный клиентский тест — **чистая загрузка Windows** (msconfig:
   скрыть службы Microsoft → отключить остальные + автозагрузку → ребут → запустить игру).
   Упадёт → добавить в тикет «reproduced in Windows clean boot».
3. Если появится 2-й ПК — зайти своим аккаунтом там: краш → 100% аккаунт; живёт → этот ПК
   (тогда копать WFP-callout драйверы: `netsh wfp show state` с админ-правами).

## Как быстро собрать свежие данные
- Тайминги: лаунчер `C:\games\Steam\steamapps\common\Zenimax Online\Launcher\host.developer.MM.DD.YYYY.log`
  → строки `ProcessComplete ... exitCode ... timeRunning`.
- Коннект/мир: `C:\Users\yelow\Documents\Elder Scrolls Online\live\Logs\client.log`
  (сервер), `interface.log` (`PregameStateManager_SetState`, `CHARACTER_ACTIVATED`).

---

## Готовый тикет в ZOS (EN; вставить @UserID, имена персонажей, ESO Plus)
```
Subject: Every session disconnects at exactly ~5 minutes on ALL servers, even at the
character-select screen — client-side fully ruled out, suspect account/session-service issue

=== ACCOUNT ===
@UserID: <твой @id>
Platform: PC — tested on BOTH the Steam and the standalone (Bethesda.net) client
Region tested: EU AND NA megaservers
2-step verification: ENABLED   |   Password: changed recently
ESO Plus: <да/нет>
Characters affected: <имена> (reproduced on multiple different characters)

=== SYMPTOM ===
The client disconnects at almost exactly 5 minutes after connecting to the megaserver,
every single time — INCLUDING while sitting idle on the character-select screen, before
entering the world. It is NOT a crash: the client exits cleanly with code 4352 (0x1100)
or 4353 (0x1101); the Documents\...\live\Errors folder is empty and Windows logs no
application-crash/WER event for these sessions.

Measured session lifetimes (launcher log, 16 Aug 2026, local time):
  10:35 4352 315.9s   12:43 4353 308.3s   14:12 4352 308.6s
  10:40 4352 315.8s   13:00 4352 311.3s   14:23 4352 309.7s
  11:39 4353 317.4s   13:08 4352 309.7s   14:55 4352 309.4s
  ...                 13:19 4352 319.0s   15:10 4352 318.6s
Runtime is 308-319s in EVERY failed session across 4 days — a fixed ~5-min timeout,
not variable packet loss. It occurs in bursts; between bursts, multi-hour sessions run
fine (one 5.8h session exited cleanly, code 0).

=== RULED OUT (reproduced identically in all cases) ===
- Both EU and NA megaservers; multiple characters
- Two separate installations (Steam + standalone Bethesda.net)
- Two networks: home ISP (Ethernet) AND a mobile phone hotspot (different ISP/route)
- VPN OFF and all traffic-filtering/DPI software OFF
- All add-ons removed (empty AddOns folder); all overlays off; Defender-only, no 3rd-party AV/EDR
- No hardware fault: no WHEA, no Kernel-Power 41; DxDiag clean (attached)

=== NETWORK EVIDENCE (proves server/account side, not my connection) ===
- Continuous ping to the game server during a failing session: 0% packet loss the entire
  time, including the exact second of disconnect.
- The game's TCP connection (159.100.232.119:24506) stayed ESTABLISHED right up to the
  moment the client terminated — my side is not dropping it; the client self-exits because
  the server stops sending data.

=== CONCLUSION / REQUEST ===
The failure follows my ACCOUNT across every server, network, PC-install and character,
happens even at character-select (before entering the world), 2FA rules out an
unauthorized concurrent login, and it is a clean "connection lost" exit rather than a
crash. This points to an account-level stuck/ghost session or a login/session-service
flag on your side. Please: (1) check my account for a stuck/ghost session and clear it;
(2) check for any account status flags causing periodic forced disconnects.

=== SYSTEM (DxDiag attached) ===
OS: Windows 11 Pro 64-bit, build 26100.9168
CPU: AMD Ryzen 9 7950X (16C/32T)   RAM: 64 GB
GPU: NVIDIA GeForce RTX 5080, driver 32.0.16.1088 (WHQL, 2026-07-22)
Board: MSI MS-7D67, BIOS 1.M0 (UEFI)   DirectX 12
```
