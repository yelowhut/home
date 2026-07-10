# draw.io Kit — параметрические шаблоны схем (стиль Primo)

Этот файл — единственный источник правды по генерации `.drawio` в скилле.
Агенты, у которых есть визуальный артефакт, **обязаны** создавать схему по шаблону отсюда,
а не сочинять координаты с нуля.

## Жёсткие правила формата

1. **Только plain XML.** Файл начинается с `<mxfile>` и содержит читаемый `<mxGraphModel>`.
   Никакого base64/deflate-сжатия. Не использовать конвертеры в PNG/SVG — пишем сам `.drawio`.
2. **Кодировка UTF-8**, переносы строк `\n`. Кириллица — как есть, без экранирования.
3. В `value` HTML экранируется: `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, `"` → `&quot;`.
   Внутри `value` допустим простой HTML: `&lt;b&gt;...&lt;/b&gt;`, `&lt;br&gt;`, `&lt;font color=...&gt;`.
4. **Координаты считаются по формуле** (см. каждый шаблон), модель НЕ расставляет блоки на глаз.
5. Каждый файл — один `<diagram>`. Имя диаграммы = тема (например `Positioning`).
6. Файл кладётся в `diagrams/<slug>.drawio` внутри папки исследования.

## Палитра Primo (брать строго отсюда)

| Назначение | Цвет |
|---|---|
| Акцент (оранжевый) | `#E8602C` |
| Тёмный текст / заголовки | `#1A1C22` |
| Приглушённый текст | `#6E6452` / `#857C6E` |
| Вторичная линия | `#B98A6E` |
| Слабая пунктирная линия | `#D8C6B0` / `#D9C9B5` |
| Зона A (наша, бежевая) | fill `#FBF1E8` · stroke `#E7D8C4` · text `#B8451B` |
| Зона B (внешняя, синяя) | fill `#EDF1F7` · stroke `#D2DDEA` · text `#2E4A66` |
| Зона C (нейтральная) | fill `#F1EEE8` · stroke `#D9D3C7` · text `#6E6452` |
| Карточка | fill `#FFFFFF` · stroke `#E7D8C4` · `shadow=1;rounded=1;arcSize=14` |
| Позитив / «зелёное» | fill `#F2FAF5` · stroke `#2F8F5B` · text `#246B45` |
| Опасность / риск | fill `#FBE9E4` · stroke `#E8602C` · text `#B8451B` |

Стандартный шрифт — Helvetica (дефолт draw.io). Заголовок 22–24, подзаголовок 12–14, тело 11–13.

---

## Каркас файла (общий для всех шаблонов)

```xml
<mxfile host="app.diagrams.net">
  <diagram name="{{DIAGRAM_NAME}}" id="{{slug}}">
    <mxGraphModel dx="1000" dy="700" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{{PAGE_W}}" pageHeight="{{PAGE_H}}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- ЯЧЕЙКИ ШАБЛОНА -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Каждая ячейка: `<mxCell id="..." parent="1" style="..." vertex="1" value="..."><mxGeometry x=".." y=".." width=".." height=".." as="geometry"/></mxCell>`.

---

## Шаблон 1 — Positioning 2×2 (карта позиционирования)

Холст 900×700. Поле графика: `X0=150, Y0=140, W=600, H=460`.
Точка с нормализованными координатами `nx,ny ∈ [0..1]`:
`px = X0 + nx*W - 11`, `py = Y0 + (1-ny)*H - 11` (минус 11 = половина диаметра чипа 22).

Заполнить: заголовок, подписи осей (`X_LEFT/X_RIGHT`, `Y_BOTTOM/Y_TOP`), 3–6 точек (наш продукт = оранжевый, конкуренты = серые).

```xml
<mxCell id="title" parent="1" vertex="1" value="{{TITLE}}" style="text;html=1;align=left;fontSize=22;fontStyle=1;fontColor=#1A1C22;"><mxGeometry x="40" y="36" width="760" height="32" as="geometry"/></mxCell>
<mxCell id="plot" parent="1" vertex="1" value="" style="rounded=1;arcSize=2;html=1;fillColor=#FBF1E8;strokeColor=#E7D8C4;"><mxGeometry x="150" y="140" width="600" height="460" as="geometry"/></mxCell>
<mxCell id="axisH" parent="1" vertex="1" value="" style="shape=line;html=1;strokeColor=#D8C6B0;strokeWidth=1.5;dashed=1;"><mxGeometry x="150" y="370" width="600" height="8" as="geometry"/></mxCell>
<mxCell id="axisV" parent="1" vertex="1" value="" style="shape=line;direction=north;html=1;strokeColor=#D8C6B0;strokeWidth=1.5;dashed=1;"><mxGeometry x="446" y="140" width="8" height="460" as="geometry"/></mxCell>
<mxCell id="xRight" parent="1" vertex="1" value="{{X_RIGHT}}" style="text;html=1;align=right;fontSize=11;fontColor=#6E6452;"><mxGeometry x="600" y="606" width="150" height="18" as="geometry"/></mxCell>
<mxCell id="xLeft" parent="1" vertex="1" value="{{X_LEFT}}" style="text;html=1;align=left;fontSize=11;fontColor=#6E6452;"><mxGeometry x="150" y="606" width="150" height="18" as="geometry"/></mxCell>
<mxCell id="yTop" parent="1" vertex="1" value="{{Y_TOP}}" style="text;html=1;align=center;fontSize=11;fontColor=#6E6452;"><mxGeometry x="375" y="116" width="150" height="18" as="geometry"/></mxCell>
<mxCell id="yBottom" parent="1" vertex="1" value="{{Y_BOTTOM}}" style="text;html=1;align=center;fontSize=11;fontColor=#6E6452;"><mxGeometry x="375" y="604" width="150" height="18" as="geometry"/></mxCell>
<!-- точка-конкурент (серая): пример nx=0.7, ny=0.6 → px=150+420-11=559, py=140+184-11=313 -->
<mxCell id="pt_comp1" parent="1" vertex="1" value="{{COMP_1}}" style="ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#B98A6E;strokeWidth=2;fontColor=#6E6452;fontSize=10;labelPosition=right;align=left;verticalLabelPosition=middle;spacingLeft=6;"><mxGeometry x="559" y="313" width="22" height="22" as="geometry"/></mxCell>
<!-- наш продукт (оранжевый): пример nx=0.3, ny=0.8 → px=150+180-11=319, py=140+92-11=221 -->
<mxCell id="pt_us" parent="1" vertex="1" value="{{OUR_PRODUCT}}" style="ellipse;whiteSpace=wrap;html=1;fillColor=#E8602C;strokeColor=#FFFFFF;strokeWidth=2;fontColor=#B8451B;fontStyle=1;fontSize=10;labelPosition=right;align=left;verticalLabelPosition=middle;spacingLeft=6;"><mxGeometry x="319" y="221" width="22" height="22" as="geometry"/></mxCell>
```

---

## Шаблон 2 — TAM / SAM / SOM (концентрические круги)

Холст 760×620. Центр `CX=380`. Три круга, общий низ:
TAM `d=460 → x=150,y=70`; SAM `d=300 → x=230,y=230`; SOM `d=150 → x=305,y=380`.
Подписи цифр — текстом справа.

```xml
<mxCell id="title" parent="1" vertex="1" value="{{TITLE}} — TAM / SAM / SOM" style="text;html=1;align=left;fontSize=22;fontStyle=1;fontColor=#1A1C22;"><mxGeometry x="40" y="30" width="680" height="32" as="geometry"/></mxCell>
<mxCell id="tam" parent="1" vertex="1" value="" style="ellipse;html=1;fillColor=#FBF1E8;strokeColor=#E7D8C4;"><mxGeometry x="150" y="70" width="460" height="460" as="geometry"/></mxCell>
<mxCell id="sam" parent="1" vertex="1" value="" style="ellipse;html=1;fillColor=#F6E2CF;strokeColor=#E0C29F;"><mxGeometry x="230" y="230" width="300" height="300" as="geometry"/></mxCell>
<mxCell id="som" parent="1" vertex="1" value="" style="ellipse;html=1;fillColor=#E8602C;strokeColor=#FFFFFF;strokeWidth=2;"><mxGeometry x="305" y="380" width="150" height="150" as="geometry"/></mxCell>
<mxCell id="tamLbl" parent="1" vertex="1" value="&lt;b&gt;TAM&lt;/b&gt;&lt;br&gt;{{TAM_VALUE}}" style="text;html=1;align=center;fontSize=12;fontColor=#6E6452;"><mxGeometry x="240" y="92" width="280" height="40" as="geometry"/></mxCell>
<mxCell id="samLbl" parent="1" vertex="1" value="&lt;b&gt;SAM&lt;/b&gt;&lt;br&gt;{{SAM_VALUE}}" style="text;html=1;align=center;fontSize=12;fontColor=#8A5A30;"><mxGeometry x="280" y="250" width="200" height="40" as="geometry"/></mxCell>
<mxCell id="somLbl" parent="1" vertex="1" value="&lt;b&gt;SOM&lt;/b&gt;&lt;br&gt;{{SOM_VALUE}}" style="text;html=1;align=center;fontSize=11;fontColor=#FFFFFF;fontStyle=1;"><mxGeometry x="305" y="435" width="150" height="40" as="geometry"/></mxCell>
```

---

## Шаблон 3 — Матрица рисков (вероятность × влияние)

Холст 720×640. Сетка 3×3, ячейка 180×150, начало `X0=180, Y0=130`.
Цвет ячейки по сумме (низ-лево зелёный → верх-право оранжевый). Риск — чип в нужной ячейке.
Колонка `c∈{0,1,2}` (влияние), строка `r∈{0,1,2}` сверху вниз (вероятность: 0=высокая).
`cellX = X0 + c*180`, `cellY = Y0 + r*150`.

```xml
<mxCell id="title" parent="1" vertex="1" value="{{TITLE}} — Карта рисков" style="text;html=1;align=left;fontSize=22;fontStyle=1;fontColor=#1A1C22;"><mxGeometry x="40" y="30" width="640" height="32" as="geometry"/></mxCell>
<mxCell id="yAxis" parent="1" vertex="1" value="Вероятность →" style="text;html=1;align=center;horizontal=0;fontSize=11;fontColor=#6E6452;"><mxGeometry x="40" y="130" width="20" height="450" as="geometry"/></mxCell>
<mxCell id="xAxis" parent="1" vertex="1" value="Влияние →" style="text;html=1;align=center;fontSize=11;fontColor=#6E6452;"><mxGeometry x="180" y="586" width="540" height="20" as="geometry"/></mxCell>
<!-- 9 ячеек: повторить с нужными fill. Зелёная #F2FAF5/#2F8F5B, жёлтая #FBF1E8/#E0C29F, красная #FBE9E4/#E8602C -->
<mxCell id="cell00" parent="1" vertex="1" value="" style="rounded=0;html=1;fillColor=#FBF1E8;strokeColor=#FFFFFF;strokeWidth=3;"><mxGeometry x="180" y="130" width="180" height="150" as="geometry"/></mxCell>
<mxCell id="cell10" parent="1" vertex="1" value="" style="rounded=0;html=1;fillColor=#FBE9E4;strokeColor=#FFFFFF;strokeWidth=3;"><mxGeometry x="360" y="130" width="180" height="150" as="geometry"/></mxCell>
<mxCell id="cell20" parent="1" vertex="1" value="" style="rounded=0;html=1;fillColor=#FBE9E4;strokeColor=#FFFFFF;strokeWidth=3;"><mxGeometry x="540" y="130" width="180" height="150" as="geometry"/></mxCell>
<!-- ...остальные 6 ячеек по той же схеме... -->
<!-- риск-чип в ячейке (c=2,r=0 → x=540+offset): -->
<mxCell id="risk1" parent="1" vertex="1" value="{{RISK_1}}" style="rounded=1;arcSize=20;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#E8602C;strokeWidth=1.5;fontSize=10;shadow=1;"><mxGeometry x="560" y="170" width="140" height="56" as="geometry"/></mxCell>
```

---

## Шаблон 4 — GTM-воронка (этапы выхода)

Холст 760×640. 4–5 этапов вертикально. Каждый этап — трапеция (`shape=trapezoid`), сужается книзу.
Этап `i` (с 0): `w = 600 - i*100`, `x = (760 - w)/2`, `y = 110 + i*100`, `h=84`.

```xml
<mxCell id="title" parent="1" vertex="1" value="{{TITLE}} — GTM-воронка" style="text;html=1;align=left;fontSize=22;fontStyle=1;fontColor=#1A1C22;"><mxGeometry x="40" y="30" width="680" height="32" as="geometry"/></mxCell>
<mxCell id="s0" parent="1" vertex="1" value="{{STAGE_0}}" style="shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#FBF1E8;strokeColor=#E7D8C4;fontColor=#B8451B;fontStyle=1;fontSize=13;"><mxGeometry x="80" y="110" width="600" height="84" as="geometry"/></mxCell>
<mxCell id="s1" parent="1" vertex="1" value="{{STAGE_1}}" style="shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#F6E2CF;strokeColor=#E0C29F;fontColor=#8A5A30;fontSize=13;"><mxGeometry x="130" y="210" width="500" height="84" as="geometry"/></mxCell>
<mxCell id="s2" parent="1" vertex="1" value="{{STAGE_2}}" style="shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#F2D8BC;strokeColor=#D8B488;fontColor=#8A5A30;fontSize=13;"><mxGeometry x="180" y="310" width="400" height="84" as="geometry"/></mxCell>
<mxCell id="s3" parent="1" vertex="1" value="{{STAGE_3}}" style="shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#E8602C;strokeColor=#FFFFFF;fontColor=#FFFFFF;fontStyle=1;fontSize=13;"><mxGeometry x="230" y="410" width="300" height="84" as="geometry"/></mxCell>
```

---

## Шаблон 5 — Value Proposition Canvas (Strategyzer)

Холст 1000×560. Слева квадрат «Профиль клиента» (круг), справа «Карта ценности» (квадрат).
Каждый делится на 3 сектора текстом-списком. Координаты фиксированы ниже — заполнить только списки.

```xml
<mxCell id="title" parent="1" vertex="1" value="{{TITLE}} — Value Proposition Canvas" style="text;html=1;align=left;fontSize=22;fontStyle=1;fontColor=#1A1C22;"><mxGeometry x="40" y="30" width="920" height="32" as="geometry"/></mxCell>
<!-- Правая часть: Value Map (квадрат) -->
<mxCell id="vmap" parent="1" vertex="1" value="Карта ценности" style="rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#FBF1E8;strokeColor=#E7D8C4;verticalAlign=top;align=center;fontSize=13;fontStyle=1;fontColor=#B8451B;spacingTop=8;"><mxGeometry x="80" y="100" width="420" height="380" as="geometry"/></mxCell>
<mxCell id="vm_products" parent="1" vertex="1" value="&lt;b&gt;Продукты и услуги&lt;/b&gt;&lt;br&gt;{{PRODUCTS}}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#E7D8C4;fontSize=11;align=left;spacingLeft=8;verticalAlign=top;spacingTop=6;"><mxGeometry x="100" y="140" width="180" height="320" as="geometry"/></mxCell>
<mxCell id="vm_gain" parent="1" vertex="1" value="&lt;b&gt;Создатели выгод&lt;/b&gt;&lt;br&gt;{{GAIN_CREATORS}}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F2FAF5;strokeColor=#2F8F5B;fontSize=11;align=left;spacingLeft=8;verticalAlign=top;spacingTop=6;"><mxGeometry x="300" y="140" width="180" height="150" as="geometry"/></mxCell>
<mxCell id="vm_pain" parent="1" vertex="1" value="&lt;b&gt;Обезболивающие&lt;/b&gt;&lt;br&gt;{{PAIN_RELIEVERS}}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FBE9E4;strokeColor=#E8602C;fontSize=11;align=left;spacingLeft=8;verticalAlign=top;spacingTop=6;"><mxGeometry x="300" y="310" width="180" height="150" as="geometry"/></mxCell>
<!-- Левая часть: Customer Profile (круг) -->
<mxCell id="cprof" parent="1" vertex="1" value="Профиль клиента" style="ellipse;whiteSpace=wrap;html=1;fillColor=#EDF1F7;strokeColor=#D2DDEA;verticalAlign=top;align=center;fontSize=13;fontStyle=1;fontColor=#2E4A66;spacingTop=14;"><mxGeometry x="540" y="100" width="380" height="380" as="geometry"/></mxCell>
<mxCell id="cp_jobs" parent="1" vertex="1" value="&lt;b&gt;Задачи&lt;/b&gt;&lt;br&gt;{{JOBS}}" style="whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;fontSize=11;align=center;fontColor=#2E4A66;"><mxGeometry x="640" y="170" width="180" height="80" as="geometry"/></mxCell>
<mxCell id="cp_gains" parent="1" vertex="1" value="&lt;b&gt;Выгоды&lt;/b&gt;&lt;br&gt;{{GAINS}}" style="whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;fontSize=11;align=center;fontColor=#246B45;"><mxGeometry x="560" y="290" width="160" height="120" as="geometry"/></mxCell>
<mxCell id="cp_pains" parent="1" vertex="1" value="&lt;b&gt;Боли&lt;/b&gt;&lt;br&gt;{{PAINS}}" style="whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;fontSize=11;align=center;fontColor=#B8451B;"><mxGeometry x="740" y="290" width="160" height="120" as="geometry"/></mxCell>
```

---

## Соответствие агент → схема

| Агент | Файл схемы | Шаблон |
|---|---|---|
| Market Researcher | `diagrams/tam-sam-som.drawio` | 2 |
| Value Proposition Architect | `diagrams/value-proposition-canvas.drawio` | 5 |
| Go To Market Expert | `diagrams/gtm-funnel.drawio` | 4 |
| Creative Strategist | `diagrams/positioning.drawio` | 1 |
| Critical Reviewer | `diagrams/risk-matrix.drawio` | 3 |

Остальные агенты (Audience, JTBD, Business) — только Markdown с таблицами, без схем.

## Самопроверка перед записью файла

- [ ] Файл начинается с `<mxfile` и содержит `<mxGraphModel>` (не base64)
- [ ] Все `&`, `<`, `>` внутри `value` экранированы
- [ ] Координаты точек/ячеек посчитаны по формуле шаблона, блоки не наезжают
- [ ] Цвета — строго из палитры Primo
- [ ] Файл лежит в `diagrams/` рядом с `.md`-отчётами
