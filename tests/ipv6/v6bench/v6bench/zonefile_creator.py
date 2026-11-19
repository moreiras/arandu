from pathlib import Path
import ipaddress
import argparse
import datetime
import socket


# The lab DNS device is 2001:db8:1::53 (lab.conf); 2001:db8::53 was a typo.
DEFAULT_NS   = ["192.168.0.53", "2001:db8:1::53"]  # noqa: E221
DEFAULT_SIIT = ["192.168.46.1"]


def ip2dnsrec(ip, host):
    match ipaddress.ip_address(ip).version:
        case 4:
            return f"{host}\tIN\tA\t{ip}"
        case 6:
            return f"{host}\tIN\tAAAA\t{ip}"


def parseargs():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "domain",
        help="Domain of the service to be tested",
    )

    parser.add_argument(
        "--ns-ips",
        nargs="+",
        default=DEFAULT_NS,
        metavar="NS",
        help="List of Name Server IPs containing at least one IPv4 and one IPv6 address",  # noqa:E501
    )

    parser.add_argument(
        "--siit-ips",
        nargs="+",
        default=DEFAULT_SIIT,
        metavar="SIIT",
        help="List of SIIT IPv4 addresses",
    )

    parser.add_argument(
        "--target-ipv4",
        nargs="+",
        default=[],
        metavar="IPV4",
        help="Target IPv4 address(es); with --target-ipv6, skips resolving the domain (lab-local target)",  # noqa: E501
    )

    parser.add_argument(
        "--target-ipv6",
        nargs="+",
        default=[],
        metavar="IPV6",
        help="Target IPv6 address(es); with --target-ipv4, skips resolving the domain (lab-local target)",  # noqa: E501
    )

    parser.add_argument(
        "--out-dir",
        default=None,
        help="Where to write db.lab and named.conf.lab-zones (default: the lab's dns/etc/bindfiles)",  # noqa: E501
    )

    parser.add_argument(
        "--env-out",
        default=None,
        help="Also write TARGET_IPV4/TARGET_IPV6 to this env file (read by siit.startup)",  # noqa: E501
    )

    args = parser.parse_args()

    if bool(args.target_ipv4) != bool(args.target_ipv6):
        parser.error("--target-ipv4 and --target-ipv6 go together")
    if any(ipaddress.ip_address(a).version != 4 for a in args.target_ipv4):
        parser.error("--target-ipv4 must contain only IPv4 addresses")
    if any(ipaddress.ip_address(a).version != 6 for a in args.target_ipv6):
        parser.error("--target-ipv6 must contain only IPv6 addresses")

    # Validate NS-IPs list
    has_v4 = any(ipaddress.ip_address(a).version == 4 for a in args.ns_ips)
    has_v6 = any(ipaddress.ip_address(a).version == 6 for a in args.ns_ips)

    if not has_v4 or not has_v6:
        parser.error("--ns-ips must contain at least one IPv4 and one IPv6 address")  # noqa:

    # Validate SIIT-IPs list
    if any(ipaddress.ip_address(a).version != 4 for a in args.siit_ips):
        parser.error("--siit-ips must contain exclusivelly IPv4 addresses")

    return args


def dom2ips(domain):
    ips = socket.getaddrinfo(domain, None, family=socket.AF_UNSPEC)

    ip_dict = {socket.AF_INET: set(), socket.AF_INET6: set()}
    for entry in ips:
        family = entry[0]
        ip = entry[-1][0]
        ip_dict[family].add(ip)
    return ip_dict


def target_ips(args):
    """Target addresses, sorted so the zone and target.env are deterministic."""
    if args.target_ipv4:
        v4, v6 = set(args.target_ipv4), set(args.target_ipv6)
    else:
        ip_dict = dom2ips(args.domain)
        v4, v6 = ip_dict[socket.AF_INET], ip_dict[socket.AF_INET6]
    key = ipaddress.ip_address
    return sorted(v4, key=key), sorted(v6, key=key)


def build_zf_string(args, v4, v6):
    serial = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d01")
    siit_recs = [ip2dnsrec(a, 'siit') for a in args.siit_ips]
    ns_recs = [ip2dnsrec(a, 'ns') for a in args.ns_ips]

    lines = [
        "$TTL 3600",
        f"@\tIN\tSOA\tns.lab.{args.domain}.\thostmaster.lab.{args.domain}. (",
        f"\t{serial}",
        "\t3600",
        "\t900",
        "\t1209600",
        "\t300",
        ")",
        "",
        "@\tIN\tNS\tns",
    ]
    lines.extend(ns_recs)
    lines.append("")
    lines.extend(siit_recs)

    zone_dict = {
        "dual": v6 + v4,
        "ipv4": v4,
        "ipv6": v6,
    }

    for host, addrs in zone_dict.items():
        for addr in addrs:
            lines.append(ip2dnsrec(addr, host))
    lines.append("")

    return "\n".join(lines)


def main():

    SCRIPT_PATH = Path(__file__).resolve().parent
    args = parseargs()
    BIND_PATH = args.out_dir or f"{SCRIPT_PATH}/kathara/dns/etc/bindfiles"

    v4, v6 = target_ips(args)
    zf_string = build_zf_string(args, v4, v6)

    with open(f"{BIND_PATH}/db.lab", "w") as f:
        f.write(zf_string)

    with open(f"{BIND_PATH}/named.conf.lab-zones", "w") as f:
        f.write(f"""zone "lab.{args.domain}" {{
        type master;
        file "/etc/bind/db.lab"; # Path to the zone file
    }};
""")

    if args.env_out:
        # The SIIT maps 192.168.46.1 to ONE IPv6: the first of the zone's.
        with open(args.env_out, "w") as f:
            f.write(f'TARGET_IPV4="{v4[0] if v4 else ""}"\n')
            f.write(f'TARGET_IPV6="{v6[0] if v6 else ""}"\n')


if __name__ == '__main__':
    main()
