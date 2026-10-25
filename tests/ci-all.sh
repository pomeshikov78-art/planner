#!/usr/bin/env bash
# CI полного контура: регрессы 3.36/3.37 + поезд 3.38–3.45 + финалы 3.46–3.48
# (онлайн) + смоуки на офлайн-сборке финала 3.48.
set -e
cd "$(dirname "$0")/.."
bash tests/ci-336.sh
bash tests/ci-337.sh
bash tests/ci-train.sh
echo "--- финалы поезда: 3.46–3.48 ---"
node tests/smoke-346.mjs План-табель-WFM-3.46.html
node tests/smoke-347.mjs План-табель-WFM-3.47.html
node tests/smoke-348.mjs План-табель-WFM-3.48.html
echo "--- ветка 3.49+: серверный контур, OLAP бюджета, офлайн-кэш ---"
node tests/integ-349.mjs
node tests/smoke-350.mjs План-табель-WFM-3.50.html
node tests/smoke-351.mjs План-табель-WFM-3.51.html
echo "--- ветка 3.52+: OLAP бригад, серверные бюджеты, офлайн-публикации, роли/квоты ---"
node tests/smoke-352.mjs План-табель-WFM-3.52.html
node tests/integ-353.mjs
node tests/smoke-354.mjs План-табель-WFM-3.54.html
node tests/integ-355.mjs
echo "--- ветка 3.56+: серверный скан, табло, ICS ---"
node tests/smoke-356.mjs План-табель-WFM-3.56.html
node tests/integ-356.mjs
node tests/smoke-357.mjs План-табель-WFM-3.57.html
node tests/integ-357.mjs
node tests/smoke-358.mjs План-табель-WFM-3.58.html
echo "--- офлайн-сборки финалов ---"
node tests/smoke-348.mjs План-табель-WFM-3.48-offline.html
node tests/smoke-346.mjs План-табель-WFM-3.48-offline.html
node tests/smoke-351.mjs План-табель-WFM-3.51-offline.html
node tests/smoke-352.mjs План-табель-WFM-3.55-offline.html
node tests/smoke-354.mjs План-табель-WFM-3.55-offline.html
node tests/smoke-357.mjs План-табель-WFM-3.58-offline.html
node tests/smoke-358.mjs План-табель-WFM-3.58-offline.html
echo "--- 3.59: роли бригад и офлайн-снапшот ---"
node tests/smoke-359.mjs План-табель-WFM-3.59.html
node tests/integ-359.mjs
node tests/smoke-359.mjs План-табель-WFM-3.59-offline.html
echo "CI-ALL: PASS (3.36–3.59: регрессы, поезд, серверные интеги, офлайн финалов)"
