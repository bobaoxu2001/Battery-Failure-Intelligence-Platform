#!/usr/bin/env bash
#
# check_data_source_connectivity.sh - lightweight TCP/IP preflight for lab or
# factory data sources before a scheduled ingest job runs.
#
# Usage:
#   BFI_DATA_SOURCES="cycler-db.local:5432,mes-api.local:443" \
#     bash scripts/check_data_source_connectivity.sh
#
# Optional:
#   BFI_PING=1   also run one ICMP ping per host
#   BFI_TIMEOUT=3 seconds to wait per TCP check

set -euo pipefail

SOURCES="${BFI_DATA_SOURCES:-localhost:22}"
TIMEOUT="${BFI_TIMEOUT:-3}"
PING="${BFI_PING:-0}"

check_tcp() {
    local host="$1" port="$2"
    if command -v nc >/dev/null 2>&1; then
        nc -z -w "${TIMEOUT}" "${host}" "${port}" >/dev/null 2>&1
        return $?
    fi
    if command -v perl >/dev/null 2>&1; then
        perl -MIO::Socket::INET -e '
            my ($host, $port, $timeout) = @ARGV;
            my $sock = IO::Socket::INET->new(
                PeerHost => $host,
                PeerPort => $port,
                Proto => "tcp",
                Timeout => $timeout,
            );
            exit($sock ? 0 : 1);
        ' "${host}" "${port}" "${TIMEOUT}" >/dev/null 2>&1
        return $?
    fi
    # Last-resort Bash /dev/tcp fallback for minimal Unix environments.
    bash -c "</dev/tcp/${host}/${port}" >/dev/null 2>&1
}

printf "Data source connectivity preflight\n"
printf "Sources: %s\n\n" "${SOURCES}"

fail_count=0
IFS=',' read -ra endpoints <<< "${SOURCES}"
for endpoint in "${endpoints[@]}"; do
    endpoint="${endpoint//[[:space:]]/}"
    host="${endpoint%:*}"
    port="${endpoint##*:}"
    if [[ -z "${host}" || -z "${port}" || "${host}" == "${port}" ]]; then
        printf "BAD  %-28s invalid endpoint; expected host:port\n" "${endpoint}"
        ((fail_count++))
        continue
    fi

    if [[ "${PING}" == "1" ]] && command -v ping >/dev/null 2>&1; then
        ping -c 1 -W "${TIMEOUT}" "${host}" >/dev/null 2>&1 || true
    fi

    if check_tcp "${host}" "${port}"; then
        printf "OK   %-28s TCP reachable\n" "${endpoint}"
    else
        printf "FAIL %-28s TCP unreachable\n" "${endpoint}"
        ((fail_count++))
    fi
done

if (( fail_count > 0 )); then
    printf "\nConnectivity preflight failed: %d endpoint(s) unreachable or invalid.\n" "${fail_count}"
    exit 1
fi
printf "\nConnectivity preflight passed.\n"
