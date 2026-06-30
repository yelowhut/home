# Persona Archetypes & Vocabularies

Fixed vocabularies and pools for deterministic persona generation. Extend by appending rows;
never renumber existing ids (would change seed-based picks).

## Fixed vocabulary — sectors (id : label)

- banking : Банки
- fintech : Финтех
- insurance : Страхование
- manufacturing : Промышленность / производство
- retail : Ритейл / электронная коммерция
- healthcare : Здравоохранение
- public-sector : Госсектор
- telecom : Телеком
- it-services : ИТ-услуги / интеграторы
- energy : Энергетика
- other : (free text, slugified)

## Fixed vocabulary — social groups (id : label)

- early-career : Начинающий специалист (22–28)
- mid-career-professional : Профессионал (29–40)
- senior-leader : Руководитель высшего звена (41–55)
- veteran-expert : Ветеран отрасли (55+)
- skeptical-procurement : Закупщик / контролёр бюджета
- other : (free text, slugified)

## Fixed vocabulary — roles (id : label)

Generic across document types; the suggestion tables below pick subsets.

- ciso : CISO / директор по ИБ
- security-engineer : Инженер по безопасности
- compliance-lawyer : Юрист по комплаенсу
- internal-auditor : Внутренний аудитор
- it-director : ИТ-директор
- procurement-lead : Руководитель закупок
- product-owner : Владелец продукта
- end-user-employee : Рядовой сотрудник-пользователь
- ops-manager : Операционный менеджер
- finance-controller : Финансовый контролёр
- external-consultant : Внешний консультант
- regulator-inspector : Инспектор регулятора
- other : (free text, slugified)

## Suggested panels by document type

SKILL phase 4 proposes (not forces) these. User edits.

| document_type        | suggested sectors                   | suggested roles                                                  |
|----------------------|-------------------------------------|------------------------------------------------------------------|
| infosec-policy       | banking, it-services, public-sector | ciso, compliance-lawyer, internal-auditor, it-director, end-user-employee |
| technical-spec       | it-services, fintech, manufacturing | it-director, product-owner, security-engineer, procurement-lead, ops-manager |
| contract             | banking, retail, manufacturing      | compliance-lawyer, procurement-lead, finance-controller, ops-manager |
| regulation           | public-sector, manufacturing        | internal-auditor, ops-manager, end-user-employee, compliance-lawyer |
| marketing-copy       | retail, fintech, telecom            | product-owner, end-user-employee, external-consultant, finance-controller |
| unknown              | it-services, banking, retail        | it-director, compliance-lawyer, end-user-employee, external-consultant |

## Name pool (deterministic pick by seed slot)

Gender-mixed, locale-neutral-RU. Index via the seed rule in `determinism.md`.

`["Андрей Соколов","Мария Левина","Дмитрий Карпов","Елена Орлова","Сергей Гущин","Ольга Реброва","Игорь Тарасов","Наталья Миронова","Павел Жуков","Анна Кудрина","Роман Беляев","Татьяна Зайцева","Виктор Панин","Юлия Савельева","Алексей Громов","Ирина Лобанова"]`

## Company pool (deterministic pick by seed slot, per sector)

Each sector maps to a pool of plausible fictional company names. Index via seed rule.

- banking: `["Северный Кредит","Аркада Банк","Меридиан Финанс"]`
- fintech: `["ПлатёжниК","Финтейл","Скай Капитал"]`
- insurance: `["Гарант Полис","Защита Плюс","Ренессанс Гарант"]`
- manufacturing: `["МеталлПром","Завод Восход","ТехноЛит"]`
- retail: `["МаркетОдин","Полка","ОптимаТорг"]`
- healthcare: `["МедЛайн","Клиника Вита","ФармаКор"]`
- public-sector: `["Госуслуги Региона","МФЦ Центральный","Ведомство-7"]`
- telecom: `["СвязьОдин","ТелеНорд","МобиКор"]`
- it-services: `["ИнтеграСис","КодБюро","Девком"]`
- energy: `["ЭнергоСеть","ГазТранс","Светополе"]`
- other: `["Компания А","Компания Б","Компания В"]`

## Core-pain pool by role (deterministic pick by seed slot)

One-line "what this role is afraid this document will cost them". Example subset; extend:

- ciso: `["новые векторы атак, за которые отвечать мне","требования без бюджета на их выполнение","ответственность за чужие решения"]`
- compliance-lawyer: `["юридически дырявые формулировки","несоответствие регуляторике","риск штрафов на мне"]`
- procurement-lead: `["скрытые затраты","привязка к одному вендору","сроки, которые сорвут план закупок"]`
- it-director: `["неисполнимые SLA","нагрузка на мою команду","интеграционный ад"]`
- end-user-employee: `["лишняя бюрократия в моей работе","непонятные требования","больше кликов, меньше смысла"]`
- internal-auditor: `["непроверяемые контроли","отсутствие следов аудита","размытая ответственность"]`
- product-owner: `["раздутый скоуп","нечёткие критерии приёмки","риски для срока релиза"]`
- finance-controller: `["непрозрачная стоимость владения","скрытые операционные расходы","ROI на бумаге"]`
- ops-manager: `["рост ручного труда","хрупкие процессы","нет плана отката"]`
- external-consultant: `["неоригинально","не учли рынок","слабая дифференциация"]`
- regulator-inspector: `["несоответствие нормам","недостаточные доказательства","формальная отписка"]`
- security-engineer: `["технически нереализуемо","дыры в архитектуре","нет threat model"]`
