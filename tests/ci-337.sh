#!/usr/bin/env bash
# CI 3.37 — «Сценарии ротаций и годовой баланс».
# 3 набора × 2 сборки = 194 проверки. Ненулевой код выхода при любом провале.
set -e
cd "$(dirname "$0")/.."
echo "--- smoke-337 · онлайн ---"
node tests/smoke-337.mjs План-табель-WFM-3.37.html
echo "--- smoke-337 · офлайн ---"
node tests/smoke-337.mjs План-табель-WFM-3.37-offline.html
echo "--- ux-337 · онлайн ---"
HOME="${HOME:-/tmp}" node tests/ux-337.mjs План-табель-WFM-3.37.html
echo "--- ux-337 · офлайн ---"
HOME="${HOME:-/tmp}" node tests/ux-337.mjs План-табель-WFM-3.37-offline.html
echo "--- viz-337 · онлайн ---"
node tests/viz-337.mjs План-табель-WFM-3.37.html
echo "--- viz-337 · офлайн ---"
node tests/viz-337.mjs План-табель-WFM-3.37-offline.html
echo "CI 3.37: PASS — 194 проверки (smoke 49×2 + ux 24×2 + viz 24×2), скриншоты shots-337/"
