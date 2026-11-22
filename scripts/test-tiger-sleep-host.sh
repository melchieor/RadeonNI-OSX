#!/bin/bash
# Host-only regression bundle. Never contacts the G5 or requests sleep.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/rdn-sleep-tests.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
printf '\n=== quiesce generation and admission model ===\n'
cc -std=c99 -Wall -Wextra -Werror -Ihw tests/quiesce_model.c hw/rdn_quiesce.c -o "$tmp/quiesce-model"
"$tmp/quiesce-model"
for test in test_snapshot_plan.py test_live_plan.py test_live_plan_driver.py test_live_image.py test_mapping_probe.py test_hidden_index_access.py test_sleep_dma.py test_sleep_guarded.py test_sleep_sequence.py test_sleep_sequence_bridge.py test_sleep_owner.py test_sleep_runtime.py test_sleep_transaction.py test_sleep_gart_integration.py \
            test_cp_try_submit.py test_tiger_sleep_stage.py test_tiger_sleep_buffer.py test_tiger_sleep_owner_adapter.py test_tiger_sleep_client_guard.py test_tiger_sleep_fence_guard.py test_tiger_sleep_stop_order.py test_client_cleanup.py test_quiesce_driver.py \
            test_resource_rehearsal.py test_sleep_rehearsal_access.py test_sleep_veto.py test_surface_mirrors.py test_tiger_target_descriptor_abi.py; do
    printf '\n=== %s ===\n' "$test"
    python3 "tests/$test"
done
printf '\n=== inert Tiger link probe ===\n'
python3 scripts/check-tiger-sleep-link.py --probe-dir "${RDN_SLEEP_PROBE_DIR:-build/tiger-v7900/sleep-link-probe-retirement-admission-20261115}" --require-owner --require-tiger-owner
