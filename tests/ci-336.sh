#!/usr/bin/env bash
# CI 3.36 — «Конструктор ротаций, бригады и доктор покрытия».
# 2 набора × 2 сборки = 286 проверок. Ненулевой код выхода при любом провале.
set -e
cd "$(dirname "$0")/.."
echo "--- smoke-336 · онлайн ---"
node tests/smoke-336.mjs План-табель-WFM-3.36.html
echo "--- smoke-336 · офлайн ---"
node tests/smoke-336.mjs План-табель-WFM-3.36-offline.html
echo "--- ux-336 · онлайн ---"
HOME="${HOME:-/tmp}" node tests/ux-336.mjs План-табель-WFM-3.36.html
echo "--- ux-336 · офлайн ---"
HOME="${HOME:-/tmp}" node tests/ux-336.mjs План-табель-WFM-3.36-offline.html
echo "--- viz-336 · онлайн ---"
node tests/viz-336.mjs План-табель-WFM-3.36.html
echo "--- viz-336 · офлайн ---"
node tests/viz-336.mjs План-табель-WFM-3.36-offline.html
echo "CI 3.36: PASS — 392 проверки (smoke 105×2 + ux 57×2 + viz 34×2), скриншоты shots-336/"
