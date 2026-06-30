#!/bin/sh
#
# verify.sh — smoke test for AI Job Search AU.
#
# Confirms the SEEK endpoints still work (they are unofficial and can change shape).
# Exits 0 if both search and detail return data, non-zero otherwise.
#
#   ./verify.sh
#   ./verify.sh --assets   # cover-letter fonts + cover.cls only (no network)
#
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--assets" ]; then
    exec "$ROOT/scripts/verify-assets.sh"
fi

SEEK="$ROOT/tools/seek-search/seek_search.py"

echo "==> Cover letter assets"
"$ROOT/scripts/verify-assets.sh"
python3 --version

echo "==> Python"
python3 --version

echo "==> SEEK search (1 page, 'Software Engineer', All Australia)"
ids=$(python3 "$SEEK" --keywords "Software Engineer" --where "All Australia" --pages 1 \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(j['id'] for j in d[:1])); sys.stderr.write('jobs: %d\n' % len(d))")

if [ -z "$ids" ]; then
    echo "FAIL: search returned no jobs — the SEEK search API may have changed." >&2
    echo "      See tools/seek-search/README.md -> Known limitations." >&2
    exit 1
fi
echo "    search OK"

echo "==> SEEK detail (GraphQL) for job $ids"
if python3 "$SEEK" --detail "$ids" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('title') else 1)"; then
    echo "    detail OK"
else
    echo "FAIL: detail fetch returned no title — the SEEK GraphQL API may have changed." >&2
    echo "      Update _DETAIL_QUERY / fetch_detail() in tools/seek-search/seek_search.py." >&2
    exit 1
fi

echo "==> parse_posting (SEEK URL -> normalized JSON)"
if python3 "$ROOT/tools/parse_posting.py" "https://www.seek.com.au/job/$ids" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='ok' and d.get('role') else 1)"; then
    echo "    parse_posting OK"
else
    echo "FAIL: parse_posting did not return status=ok for SEEK job $ids." >&2
    exit 1
fi

echo
echo "All checks passed. SEEK endpoints are working."
