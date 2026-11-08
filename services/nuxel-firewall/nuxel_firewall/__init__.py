"""Nuxel Firewall — one authoritative policy model and enforcement owner.

On the S10+ (Linux 4.14.253, Samsung-derived) the kernel does NOT enable
nftables (`CONFIG_NF_TABLES is not set`) and does not enable the xtables cgroup
match (`CONFIG_NETFILTER_XT_MATCH_CGROUP is not set`).  The only kernel-usable
backend there is classic xtables/iptables (IPv4 + IPv6, owner match available).
This package implements an honest backend abstraction around that reality.
"""

__version__ = "1.0.0"
