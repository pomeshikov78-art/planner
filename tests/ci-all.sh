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
echo "--- офлайн-сборка финала ---"
node tests/smoke-348.mjs План-табель-WFM-3.48-offline.html
node tests/smoke-346.mjs План-табель-WFM-3.48-offline.html
echo "CI-ALL: PASS (3.36–3.48, онлайн + офлайн финала)"
