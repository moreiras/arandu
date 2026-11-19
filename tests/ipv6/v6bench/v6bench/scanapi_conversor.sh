#!/bin/sh

# Set error handling: exit on error, unset variable usage
set -eu

# Test if scanapi is installed
if ! command -v scanapi >/dev/null 2>&1; then
    printf '%s\n' "Error: required command 'scanapi' not found." >&2
    exit 1
fi

# Print usage information
usage() {
    cat << EOF
Usage: $(basename "$0") -i OPENAPI_PATH [-o PLAN_PATH] [-c CONFIG_PATH] [-l LOG_LEVEL]

Wrapper script to convert an OpenAPI document into ScanAPI format.

Required:
  -i  PATH    OpenAPI file path (JSON or YAML)

Options:
  -o  PATH    Where to write the plan (default: ./scanapi.yaml); pass it to
              run_lab.sh -p. The variables it uses are printed as an env-file
              template for run_lab.sh -e.
  -c  PATH    Configuration file path
  -l  LEVEL   Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  -h          Display this help message
EOF
    exit 1
}

# Initialize variables
openapi_path=""
config_path=""
log_level=""
output_path="scanapi.yaml"

# Parse flags using getopts
while getopts "i:o:c:l:h" opt; do
    case "$opt" in
        i) openapi_path="$OPTARG" ;;
        o) output_path="$OPTARG" ;;
        c) config_path="$OPTARG" ;;
        l) log_level="$OPTARG" ;;
        h) usage ;;
        ?) usage ;;
    esac
done

# --- 1. Validation: Required argument ---
if [ -z "$openapi_path" ]; then
    echo "Error: Missing required argument (-i OPENAPI_PATH)." >&2
    usage
fi

if [ ! -f "$openapi_path" ]; then
    echo "Error: OpenAPI file '$openapi_path' does not exist or is not a regular file." >&2
    exit 1
fi

# --- 2. Validation: Optional arguments ---

# Validate config path if provided
if [ -n "$config_path" ] && [ ! -f "$config_path" ]; then
    echo "Error: Config file '$config_path' does not exist." >&2
    exit 1
fi

# Validate log level if provided
if [ -n "$log_level" ]; then
    case "$log_level" in
        DEBUG|INFO|WARNING|ERROR|CRITICAL) ;;
        *)
            echo "Error: Invalid log level '$log_level'. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL." >&2
            exit 1
            ;;
    esac
fi

# --- 3. Build Command Array / String safely ---
set -- "$openapi_path"
set -- "$@" -o "scanapi.yaml"

if [ -n "$config_path" ]; then
    set -- "$@" -c "$config_path"
fi

if [ -n "$log_level" ]; then
    set -- "$@" -ll "$log_level"
fi

echo "Executing: scanapi from openapi $*"
scanapi from openapi "$@"

echo "Normalizing 'scanapi.yaml' Environment variable naming"
sed -Eri 's/(\$\{\w+)\.?(\w*\})/\U\1\2/g' scanapi.yaml

SCRIPT_PATH="$(dirname "$(realpath "$0")")"

# The lab is now run from a throwaway copy (run_lab.sh), so nothing is written
# into kathara/shared: the plan goes to -o and the variables to stdout.
echo "# Variables used by the plan (env file for run_lab.sh -e):"
grep -Po '(?<=\$\{)\w+(?=\})' scanapi.yaml |\
    grep -vFx 'BASE_URL' |\
    sort -u |\
    sed 's/$/=""/'
echo 'BASE_PROTO="https" # http or https'
echo 'BASE_PORT=""       # empty = default port of BASE_PROTO'

python3 "${SCRIPT_PATH}/add_host_header.py"
if [ "$output_path" != "scanapi.yaml" ]; then
    mv -v scanapi.yaml "$output_path"
fi

echo "Done!"
