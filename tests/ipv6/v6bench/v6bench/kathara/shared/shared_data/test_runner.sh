#!/bin/sh

# Runs the test plan of one client against each scenario subdomain in $SDOMS.
# run_lab.sh calls it inside each client with "kathara exec"; the exit status
# (0 = every scenario passed) is also written to /shared/results/status/.

# Exported (set -a): ScanAPI resolves ${VAR} in the plan from the environment.
set -a
# shellcheck disable=SC1091
. /shared/env/test_vars.env
if [ -f /shared/env/credentials.env ]; then
    . /shared/env/credentials.env
fi
set +a

HOSTNAME="$(/usr/bin/hostname)"
STATUS_DIR="/shared/results/status"
mkdir -p "${STATUS_DIR}" /shared/results/logs
status=0

URL_TEMPLATE="lab.${BASE_DOMAIN}"
PORT_SUFFIX="${BASE_PORT:+:${BASE_PORT}}"
WAIT_SECONDS="${WAIT_SECONDS:-120}"

for sdom in ${SDOMS}; do
    export BASE_URL="${BASE_PROTO}://${sdom}.${URL_TEMPLATE}${PORT_SUFFIX}"

    # Wait until the target answers through this scenario's path (DNS, routing,
    # NAT64 or SIIT): one generic check instead of a wait per component.
    if ! timeout "${WAIT_SECONDS}" sh -c "until [ \"\$(curl -s -o /dev/null -m 3 -w '%{http_code}' '${BASE_URL}/')\" != 000 ]; do sleep 1; done"; then
        echo "${HOSTNAME}/${sdom}: target not reachable at ${BASE_URL} after ${WAIT_SECONDS}s" >&2
        echo "unreachable" > "${STATUS_DIR}/${HOSTNAME}-${sdom}"
        status=1
        continue
    fi

    sdom_status=0
    if [ -f /shared/shared_data/scanapi.yaml ]; then
        OUTPUT_FILE="/shared/results/${HOSTNAME}-${sdom}-report.csv"
        scanapi run \
            -o "${OUTPUT_FILE}" \
            -t "/shared/shared_data/csv_template.jinja" \
            /shared/shared_data/scanapi.yaml > "/shared/results/logs/${HOSTNAME}-${sdom}.log" 2>&1 || sdom_status=1
        sed -i "2,\$s/^/\"${HOSTNAME}\",/" "${OUTPUT_FILE}"
    fi

    # Optional extra checks (upstream issue #5): any executable at
    # /shared/checks/run, called once per scenario with CLIENT, SDOM and BASE_URL.
    if [ -x /shared/checks/run ]; then
        CLIENT="${HOSTNAME}" SDOM="${sdom}" /shared/checks/run \
            > "/shared/results/logs/${HOSTNAME}-${sdom}-checks.log" 2>&1 || sdom_status=1
    fi

    if [ "${sdom_status}" -eq 0 ]; then
        echo "ok" > "${STATUS_DIR}/${HOSTNAME}-${sdom}"
    else
        echo "failed" > "${STATUS_DIR}/${HOSTNAME}-${sdom}"
        status=1
    fi
done

exit "${status}"
