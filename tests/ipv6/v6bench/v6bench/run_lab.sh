#!/bin/sh

# Runs the V6Bench lab once, in a throwaway copy of kathara/, and exits 0 only
# if every client passed every scenario. Needs no root: no privileged devices.
#
# Usage: run_lab.sh -d DOMAIN [-4 IPV4]... [-6 IPV6]... [-t TARGET_DIR] [-p PLAN]
#                   [-c CHECKS_DIR] [-e ENV_FILE] [-w DEVICE] [-x DEVICE] [-r RESULTS_DIR]
#
#   -d DOMAIN      domain under test (BASE_DOMAIN); scenarios are <sdom>.lab.DOMAIN
#   -4, -6         target addresses (repeatable). With them the target is local to
#                  the lab and the domain is not resolved; without them it is.
#   -t TARGET_DIR  overlay merged into the lab copy: TARGET_DIR/lab.conf.fragment
#                  is appended to lab.conf and everything else (device folders,
#                  *.startup, shared/) is copied over the lab
#   -p PLAN        ScanAPI plan (scanapi.yaml); without it only the checks run
#   -c CHECKS_DIR  copied to /shared/checks; its "run" is called per scenario
#   -e ENV_FILE    extra variables for test_vars.env (BASE_PROTO, BASE_PORT, ...)
#   -w DEVICE      before the clients, waits until /shared/target/ready.sh succeeds
#                  on DEVICE (up to WAIT_SECONDS, default 120); fails if it never does
#   -x DEVICE      after the tests, runs /shared/target/collect.sh on DEVICE
#   -r RESULTS_DIR where shared/results is copied (default: ./results-<timestamp>)
#
# Environment: KATHARA (command that runs Kathara, default "kathara"),
#              PYTHON (default "python3", runs zonefile_creator.py).

set -eu

SCRIPT_PATH="$(dirname "$(realpath "$0")")"
KATHARA="${KATHARA:-kathara}"
PYTHON="${PYTHON:-python3}"

usage() {
    sed -n '3,23p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
}

domain=""; target_dir=""; plan=""; checks_dir=""; env_file=""; collect_device=""; ready_device=""
results_dir="./results-$(date +%Y%m%d-%H%M%S)"
v4_args=""; v6_args=""
while getopts "d:4:6:t:p:c:e:w:x:r:h" opt; do
    case "$opt" in
        d) domain="$OPTARG" ;;
        4) v4_args="${v4_args} ${OPTARG}" ;;
        6) v6_args="${v6_args} ${OPTARG}" ;;
        t) target_dir="$(realpath "$OPTARG")" ;;
        p) plan="$(realpath "$OPTARG")" ;;
        c) checks_dir="$(realpath "$OPTARG")" ;;
        e) env_file="$(realpath "$OPTARG")" ;;
        w) ready_device="$OPTARG" ;;
        x) collect_device="$OPTARG" ;;
        r) results_dir="$OPTARG" ;;
        *) usage ;;
    esac
done
[ -n "$domain" ] || usage

WORK="$(mktemp -d "${TMPDIR:-/tmp}/v6bench.XXXXXX")"
started=0
cleanup() {
    if [ "$started" -eq 1 ]; then
        # Files written by the devices may belong to root (Linux): let the
        # caller remove them.
        $KATHARA exec -d "$WORK" gateway -- chmod -R a+rwX /shared >/dev/null 2>&1 || true
        $KATHARA lclean -d "$WORK" >/dev/null 2>&1 || true
    fi
    rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 1. Throwaway copy of the lab, plus the optional target overlay.
cp -R "${SCRIPT_PATH}/kathara/." "$WORK/"
if [ -n "$target_dir" ]; then
    for entry in "$target_dir"/* "$target_dir"/.[!.]*; do
        [ -e "$entry" ] || continue
        case "$(basename "$entry")" in
            lab.conf.fragment) { echo; cat "$entry"; } >> "$WORK/lab.conf" ;;
            *) cp -R "$entry" "$WORK/" ;;
        esac
    done
fi
mkdir -p "$WORK/shared/env" "$WORK/shared/results/logs" "$WORK/shared/results/status"

# 2. DNS zone and target.env (same addresses for the zone and the SIIT).
set -- "$domain" --out-dir "$WORK/dns/etc/bindfiles" --env-out "$WORK/shared/env/target.env"
if [ -n "$v4_args$v6_args" ]; then
    # shellcheck disable=SC2086
    set -- "$@" --target-ipv4 $v4_args --target-ipv6 $v6_args
fi
"$PYTHON" -I "${SCRIPT_PATH}/zonefile_creator.py" "$@"

# 3. Test variables, plan and checks.
{
    echo "BASE_DOMAIN=\"${domain}\""
    echo 'BASE_PROTO="https"'
    echo 'BASE_PORT=""'
    if [ -n "$env_file" ]; then cat "$env_file"; fi
} > "$WORK/shared/env/test_vars.env"
if [ -n "$plan" ]; then
    cp "$plan" "$WORK/shared/shared_data/scanapi.yaml"
fi
if [ -n "$checks_dir" ]; then
    cp -R "$checks_dir" "$WORK/shared/checks"
    chmod +x "$WORK/shared/checks/run"
fi

# 4. Start the lab and run each client's scenarios.
started=1
echo "Starting the lab"
$KATHARA lstart --noterminals -d "$WORK" >/dev/null
if ! $KATHARA exec -d "$WORK" gateway -- test -f /shared/env/test_vars.env >/dev/null 2>&1; then
    echo "error: the devices do not see /shared (is shared_mount disabled in kathara.conf?)" >&2
    exit 2
fi

# Fail fast if a device exited at start (e.g. an image whose CMD ends):
# otherwise each scenario would wait for the target until WAIT_SECONDS.
down=""
for dev in $(sed -n 's/^\([a-z0-9_]*\)\[0\]=.*/\1/p' "$WORK/lab.conf"); do
    $KATHARA exec -d "$WORK" "$dev" -- true >/dev/null 2>&1 || down="${down} ${dev}"
done
if [ -n "$down" ]; then
    echo "error: device(s) not running after lstart:${down}" >&2
    exit 2
fi

if [ -n "$ready_device" ]; then
    echo "Waiting for ${ready_device}"
    waited=0
    until $KATHARA exec -d "$WORK" "$ready_device" -- /bin/sh /shared/target/ready.sh >/dev/null 2>&1; do
        waited=$((waited + 2))
        if [ "$waited" -ge "${WAIT_SECONDS:-120}" ]; then
            echo "error: ${ready_device} not ready after ${waited}s (/shared/target/ready.sh)" >&2
            exit 2
        fi
        sleep 2
    done
fi

clients="$(sed -n 's/^\([a-z0-9_]*\)\[env\]="SDOMS=.*/\1/p' "$WORK/lab.conf")"
for client in $clients; do
    echo "Running ${client}"
    $KATHARA exec -d "$WORK" "$client" -- /bin/sh /shared/shared_data/test_runner.sh \
        > "$WORK/shared/results/logs/${client}-runner.log" 2>&1 || true
done

if [ -n "$collect_device" ]; then
    $KATHARA exec -d "$WORK" "$collect_device" -- /bin/sh /shared/target/collect.sh \
        > "$WORK/shared/results/logs/${collect_device}-collect.log" 2>&1 || true
fi

# 5. Results and verdict (one status file per client and scenario).
$KATHARA exec -d "$WORK" gateway -- chmod -R a+rwX /shared/results >/dev/null 2>&1 || true
mkdir -p "$results_dir"
cp -R "$WORK/shared/results/." "$results_dir/"

overall=0
for client in $clients; do
    sdoms="$(sed -n "s/^${client}\[env\]=\"SDOMS=\(.*\)\"/\1/p" "$WORK/lab.conf")"
    for sdom in $sdoms; do
        st="$(cat "$results_dir/status/${client}-${sdom}" 2>/dev/null || echo missing)"
        printf '%-20s %-6s %s\n' "$client" "$sdom" "$st"
        [ "$st" = "ok" ] || overall=1
    done
done
echo "Results in ${results_dir}"
exit "$overall"
