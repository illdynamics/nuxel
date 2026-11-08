"""Firewall backend adapters — exactly one authoritative owner per hook."""
from . import base, iptables, nftables, firewalld, ufw

__all__ = ["base", "iptables", "nftables", "firewalld", "ufw"]


def get_backend(name, probe=None):
    probe = probe or {}
    if name == "iptables":
        return iptables.IPTablesBackend(probe)
    if name == "nftables":
        return nftables.NFTablesBackend(probe)
    if name == "firewalld":
        return firewalld.FirewalldBackend(probe)
    if name == "ufw":
        return ufw.UFWBackend(probe)
    raise ValueError("unknown backend %r" % (name,))
