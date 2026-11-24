#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PWCLI="${CODEX_HOME:-${HOME}/.codex}/skills/playwright/scripts/playwright_cli.sh"
TMP_DIR="$(mktemp -d)"
SESSION="ljannotateqa-$$"
HTML="${TMP_DIR}/review.html"
PACKET="${1:-${SKILL_DIR}/references/synthetic-packet-v2.json}"
RECEIPT="${2:-${TMP_DIR}/receipt.json}"
PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"

pw() {
  (cd "${TMP_DIR}" && "${PWCLI}" -s="${SESSION}" "$@")
}

cleanup() {
  pw close >/dev/null 2>&1 || true
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

command -v npx >/dev/null 2>&1 || { echo "FAIL: npx is required" >&2; exit 1; }
[[ -x "${PWCLI}" ]] || { echo "FAIL: Playwright wrapper not found: ${PWCLI}" >&2; exit 1; }

[[ -f "${PACKET}" ]] || { echo "FAIL: packet not found: ${PACKET}" >&2; exit 1; }
python3 "${SKILL_DIR}/scripts/build_annotation_html.py" \
  "${PACKET}" "${HTML}" --receipt "${RECEIPT}" >/dev/null
python3 "${SKILL_DIR}/scripts/validate_annotation_html.py" "${HTML}" >/dev/null
python3 -m http.server "${PORT}" --bind 127.0.0.1 --directory "${TMP_DIR}" >/dev/null 2>&1 &
SERVER_PID=$!

pw open "http://127.0.0.1:${PORT}/review.html" >/dev/null
PHASES=(geometry generic)
if [[ "$(cd "$(dirname "${PACKET}")" && pwd)/$(basename "${PACKET}")" == "${SKILL_DIR}/references/synthetic-packet-v2.json" ]]; then
  PHASES=(geometry interaction export)
fi
for phase in "${PHASES[@]}"; do
  if ! PHASE_OUTPUT="$(pw run-code --filename "${SKILL_DIR}/scripts/browser_qa_${phase}.js")"; then
    echo "FAIL: browser QA phase ${phase}" >&2
    echo "${PHASE_OUTPUT}" >&2
    exit 1
  fi
  if [[ "${phase}" == "interaction" ]]; then
    MODAL_OUTPUT="$(pw run-code 'async page => { await page.locator("#full").click(); }')"
    grep -q "请先确认全部记录" <<<"${MODAL_OUTPUT}" || { echo "FAIL: incomplete full export was not blocked" >&2; exit 1; }
    pw dialog-accept >/dev/null
  fi
done
CONSOLE_OUTPUT="$(pw console)"
grep -q "Errors: 0" <<<"${CONSOLE_OUTPUT}" || { echo "FAIL: browser console error" >&2; exit 1; }
REQUEST_OUTPUT="$(pw requests)"
if grep -Eq 'https?://' <<<"${REQUEST_OUTPUT}"; then
  echo "FAIL: unexpected dynamic network request" >&2
  exit 1
fi

python3 "${SKILL_DIR}/scripts/finalize_receipt.py" "${RECEIPT}" >/dev/null

echo "PASS lj-annotate browser QA: packet=${PACKET} receipt=${RECEIPT} phases=${PHASES[*]}"
