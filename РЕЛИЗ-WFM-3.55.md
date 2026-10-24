# Релиз 3.55 — «Серверные роли бригад и квоты PUT»

Дата: 24.10.2026 · артефакт: `План-табель-WFM-3.55.html` + `…-3.55-offline.html` (цепочка: 3.554 → 3.55, `build-train.py`)
CI: `tests/integ-355.mjs` — 10 проверок (integ-355 с пользователями).

1. Сервер: право brig у admin/hr/editor/tab — PUT /api/v1/brigades без staff; право budget у admin/hr для PUT /api/v1/budgets; часовые квоты PUT бригад PT_BRIG_QUOTA (например editor:60,tab:120): при исчерпании 429 с retryAfterMin и аудитом brig-quota, остаток квоты в ответе PUT.
2. Клиент: ROLE_PERM дополнен brig/budget (матрица прав), toast выгрузки бригад показывает остаток часовой квоты. integ-355: editor 200 → 429 по квоте, viewer 403, admin 200; бюджеты: editor 403, admin 200.

Совместимость: серверные эндпоинты аддитивны; клиент без сервера деградирует подсказками.
