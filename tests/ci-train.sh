#!/usr/bin/env bash
# CI релизного поезда 3.38–3.41 (онлайн-сборки) + регресс 3.36/3.37.
set -e
cd "$(dirname "$0")/.."
echo "--- регресс 3.36 ---"; bash tests/ci-336.sh
echo "--- регресс 3.37 ---"; bash tests/ci-337.sh
echo "--- поезд: смоуки 3.38–3.41 ---"
node tests/smoke-338.mjs План-табель-WFM-3.38.html
node tests/smoke-339.mjs План-табель-WFM-3.39.html
node tests/smoke-340.mjs План-табель-WFM-3.40.html
node tests/smoke-341.mjs План-табель-WFM-3.41.html
echo "--- поезд: мобильный UX 3.38 ---"
HOME="${HOME:-/tmp}" node tests/ux-338.mjs План-табель-WFM-3.38.html
echo "CI-TRAIN 3.38–3.41: PASS (smoke 19+18+19+21, ux-338, плюс регресс 3.36/3.37)"
