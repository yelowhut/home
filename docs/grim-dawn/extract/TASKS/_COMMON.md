# ОБЩИЙ БРИФ — читать первым, до своего задания

Ты пишешь один экстрактор данных Grim Dawn. Фундамент уже готов и протестирован —
**ничего не реверси заново**, используй готовое.

## Что уже сделано (не трогай, не переписывай)

| Файл | Что |
|---|---|
| `docs/grim-dawn/extract/gdlib.py` | `DB` (слияние 4 `.arz`), `Tags`, `open_sqlite()`, `write_json/jsonl`, `out_path()` |
| `docs/grim-dawn/extract/00_text.py` | распаковал EN-тэги → `tags_en.json` (20245 тэгов) |
| `docs/grim-dawn/extract/01_dump.py` | полный дамп → `gd.sqlite` |
| `docs/grim-dawn/extract/02_templates.py` | распаковал `templates.arc` → `field_schema.json` |
| `D:/git/home/data/grim-dawn/gd.sqlite` | **82132 записи**, 910 MB — твой основной источник |
| `D:/git/home/data/grim-dawn/tags_en.json` | `tagXxx` → английская строка |
| `D:/git/home/data/grim-dawn/field_schema.json` | **словарь схемы: 18968 полей `.dbr`** — тип, класс, категория, описание |
| `D:/git/home/data/grim-dawn/template_types.json` | шаблон записи → список его полей |

### field_schema.json — читать до того, как гадать о поле

Игра поставляет собственные редакторские шаблоны DBR. Это **авторитетный** ответ на вопрос
«что значит поле X», в отличие от вывода по данным. Пример:

```json
"prefixTableName1": {"type": ["file_dbr"], "class": ["variable"],
                     "groups": ["All Groups", "Randomizer Prefix"],
                     "description": ["LootRandomizerTable or LootRandomizer"]}
"offensivePhysicalMin": {"type": ["real"], "class": ["array"],
                         "groups": ["All Groups", "Offensive Absolute"]}
```
`groups` — человекочитаемая категория поля (Offensive Absolute, Conversion Parameters,
Skill Augment, Devotion…). `type`: `real`/`int`/`string`/`file_dbr`/`picklist`/`bool`.
`class`: `variable` (одно значение) / `array` (массив, часто по уровням) / `static`.
Описание есть лишь у 1637 полей из 18968 — но тип, класс и группа есть почти у всех.

Схема `gd.sqlite`:
```sql
records(name PK, orig_name, type, src, fields)  -- name нормализовано: lowercase + '/'
                                                -- fields = JSON {поле_dbr: значение}
                                                -- src = base|gdx1|gdx2|gdx3 (кто победил при слиянии)
tags(tag PK, text)
meta(key PK, value)
```

## Как работать

```python
import json, sqlite3
from gdlib import DB, Tags, open_sqlite, write_jsonl, write_json, out_path, norm

con = open_sqlite(readonly=True)
rows = con.execute("SELECT name, type, src, fields FROM records WHERE type=?", ("ItemRelic",))
for name, typ, src, fields in rows:
    f = json.loads(fields)
    ...
tags = Tags()
print(tags("tagWeaponSwordA000"))   # -> Shiv;  неизвестный тэг вернётся как есть
```

Ссылки между записями — это строки-пути вида `records/skills/playerclass01/cadence.dbr`.
Резолвить через `norm()` + `SELECT ... WHERE name=?`. Пути в полях бывают в любом регистре
и с обратными слэшами — **всегда** прогоняй через `norm()`.

## Жёсткие правила

1. **Не выдумывай семантику полей.** Если не уверен, что значит поле `.dbr` — проверь
   гипотезу минимум на 3 разных записях и сверься с тем, что показывает игра/тэги.
   Неизвестные поля не выбрасывай молча — складывай в `extra` или перечисли в отчёте.
2. **Сохраняй сырьё.** Твой JSON должен содержать `record` (путь к .dbr) для каждой сущности,
   чтобы потом можно было вернуться к первоисточнику.
3. **Резолви тэги, но храни и ключ.** `{"name": "Shiv", "name_tag": "tagWeaponSwordA000"}`.
4. **Нули не пиши.** В `.dbr` тонны полей со значением 0/""/пустой список — выкидывай их,
   иначе выхлоп раздуется в разы. Это главный рычаг размера.
5. **Проверяй покрытие.** В конце скрипта печатай: сколько записей обработано, сколько
   пропущено и почему, сколько полей осталось неопознанными.
6. **Кодировка.** `gdlib` уже чинит cp1252-консоль Windows при импорте. Импортируй его
   первым, и `print` с юникодом не упадёт.
7. **Не делай git commit.** Вообще. Только пиши файлы.
8. **Не трогай чужие файлы.** Только свой скрипт, свой выход, свой отчёт.

## Что сдать

1. **Скрипт** `docs/grim-dawn/extract/<как указано в задании>.py` — идемпотентный,
   запускается как `python <скрипт>.py` из папки `extract`, без аргументов.
2. **Данные** в `D:/git/home/data/grim-dawn/` (через `out_path`/`write_jsonl`/`write_json`).
   JSONL для больших списков сущностей, JSON для справочников/деревьев.
3. **Отчёт** `docs/grim-dawn/extract/REPORTS/<имя>.md` на русском:
   - схема выхода: каждое поле — что значит и из какого поля `.dbr` получено;
   - счётчики (сколько сущностей, размер файла);
   - **что не удалось / в чём не уверен** — этот раздел обязателен и важнее остальных;
   - 2-3 живых примера записи из выхода.

## Definition of Done

- [ ] Скрипт реально запущен и отработал без ошибок, ты видел его вывод.
- [ ] Выходной файл существует, ты открыл его и глазами проверил 3+ записи.
- [ ] Спот-чек: выбери 2 сущности, которые ты знаешь по игре, и подтверди, что цифры
      в выходе бьются с ожиданием. Опиши это в отчёте.
- [ ] Отчёт написан, включая раздел про неуверенности.

Финальным сообщением верни: путь к выходу, размер, количество сущностей, 3 главных
неопределённости. Без воды.
