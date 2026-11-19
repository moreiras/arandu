# V6Bench

> **Modified copy.** This is a modified copy of [CEPTRO-br/v6bench](https://github.com/CEPTRO-br/v6bench) at commit `c61474e`, used by the Arandurapé IPv6 test level (T7). It runs without root and without kernel modules (TAYGA instead of Jool), can test a target inside the lab, and returns a non-zero exit code on failure. Every change and its reason is listed in [MODIFICACOES.md](MODIFICACOES.md) (Portuguese); `comparar_com_original.sh` prints the diff against the original.

V6Bench implements the integration testing recommendations from the IETF Internet-Draft [draft-ietf-v6ops-ipv6-app-testing](https://datatracker.ietf.org/doc/draft-ietf-v6ops-ipv6-app-testing/).

The initial focus is on the connectivity scenarios described in Section 3.1 of the draft for APIs defined by an OpenAPI specification (JSON or YAML). Support for additional application types and draft sections will be added over time.

> **⚠️ Project status:** Early development. Functional, but may contain bugs.

Feedback is welcome through GitHub Issues, and contributions are welcome via Pull Requests.

## Overview

V6Bench helps Quality Assurance teams validate IPv6 readiness throughout the software development lifecycle. It can also be used by developers, operators, and system administrators to verify whether applications behave correctly in different IPv6 deployment scenarios.

## Requirements

* [ScanAPI](https://scanapi.dev/)
   * Currently using version 2.13.2
       * Requires `curlify2<2.0.0,>=1.0.1`
   * Preinstalled in the client image (`images/client`)
* Docker
   * IPv6 on the default bridge network is needed only to test a target on the Internet ([ref](https://docs.docker.com/engine/daemon/ipv6/#use-ipv6-for-the-default-bridge-network))
* [Kathará](https://www.kathara.org/) (tested with 3.8.4; no root needed)
* [TAYGA](http://www.litech.org/tayga/) 0.9.2, from Debian, in the translator image (`images/translator`); no kernel module

## Architecture

V6Bench is built around a Kathará topology that creates the required network infrastructure (DNS, NAT64, SIIT, etc.) together with client hosts representing different IPv6 connectivity scenarios.

The diagram below illustrates the architecture and the test workflow.

![Architecture Diagram](doc/architecture_diagram.svg?raw=true&sanitize=true "Architecture Diagram")

## Usage Workflow

1. Build the images:

   ```bash
   docker build -t v6bench/translator:local v6bench/images/translator
   docker build -t v6bench/client:local v6bench/images/client
   ```

2. Optionally, generate a ScanAPI plan from an OpenAPI document (needs GNU `sed`/`grep` and ScanAPI on the host) and review it:

   ```bash
   v6bench/scanapi_conversor.sh -i OPENAPI_PATH -o plan.yaml > vars.env
   ```

   Fill in `vars.env` (it lists the plan's variables plus `BASE_PROTO` and `BASE_PORT`).

3. Run the lab (a throwaway copy of `kathara/` is used; nothing is written to this tree):

   ```bash
   # target on the Internet (its addresses are resolved)
   v6bench/run_lab.sh -d example.com -p plan.yaml -e vars.env -r results
   # target inside the lab: give its addresses and an overlay with the device (lab.conf.fragment, startup, shared/)
   v6bench/run_lab.sh -d example.test -4 192.168.0.80 -6 2001:db8:1::80 -t target/ -p plan.yaml -e vars.env -w target -r results
   ```

   `-c DIR` adds custom checks (`DIR/run`, called per scenario with `CLIENT`, `SDOM` and `BASE_URL`); `-x DEVICE` runs `/shared/target/collect.sh` there after the tests. `run_lab.sh -h` lists all options.

4. The exit code is 0 only if every client passed every scenario. Results: `results/status/` (one file per client and scenario), the ScanAPI CSV reports and `results/logs/`.
