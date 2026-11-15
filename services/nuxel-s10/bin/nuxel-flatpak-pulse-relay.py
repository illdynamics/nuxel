#!/usr/bin/python3
"""Per-sandbox PulseAudio relay.

A Flatpak sandbox cannot reach the real PulseAudio/PipeWire-Pulse socket: its
XDG_RUNTIME_DIR is remapped to /run/user/0, backed by
/root/.cache/.flatpak/<app>/xdg-run on the host.

The launcher maps this directory into the sandbox at /run/flatpak/pulse
(flatpak sets PULSE_SERVER=unix:/run/flatpak/pulse/native for every app that
declares --socket=pulseaudio) and passes the same PULSE_SERVER explicitly.
The relay listens HERE and forwards the byte stream to the real session
server.  Nothing is interpreted.

A client.conf is written next to the socket as well: some PulseAudio clients
inside the sandbox read PULSE_CLIENTCONFIG for the default-server instead of
the environment, and a missing file makes them fall back to a dead path.
"""
import os, socket, sys, threading, time

LISTEN = os.environ.get("NUXEL_FLATPAK_PULSE_SLOT", "/run/user/0/pulse/native")
TARGET = os.environ.get("NUXEL_PULSE_SERVER", "/run/nuxel-wayland/pulse/native")
LOG = "/run/nuxel-flatpak-pulse-relay.log"


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except OSError:
        pass


def pump(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                s.close()
            except OSError:
                pass


def handle(client):
    try:
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.connect(TARGET)
    except OSError as exc:
        log("upstream connect failed: %s" % exc)
        client.close()
        return
    threading.Thread(target=pump, args=(upstream, client), daemon=True).start()
    pump(client, upstream)


def write_client_conf(slot):
    """Publish a minimal PulseAudio client.conf in the sandbox slot."""
    conf = os.path.join(slot, "client.conf")
    body = (
        "# Written by nuxel-flatpak-pulse-relay.  Sandbox-side PulseAudio\n"
        "# clients read this through PULSE_CLIENTCONFIG.\n"
        "default-server = unix:%s\n"
        "autospawn = no\n"
        "daemon-binary = /bin/true\n"
        "enable-shm = no\n" % LISTEN
    )
    tmp = conf + ".tmp"
    try:
        with open(tmp, "w") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        os.replace(tmp, conf)
    except OSError as exc:
        log("client.conf write failed: %s" % exc)


def main():
    slot = os.path.dirname(LISTEN)
    if os.path.islink(slot):
        # The audio session publishes a link here on some boots; a link must
        # never be followed for the relay's own slot.
        os.unlink(slot)
    os.makedirs(slot, mode=0o755, exist_ok=True)
    # The slot lives on the sandbox-visible path while the relay runs as root.
    # A 0750 root:root directory is untraversable for the sandboxed uid 1000,
    # which silently produced "Connection refused" and no microphone in every
    # Flatpak.  Keep the directory traversable; the socket below is the only
    # entry and is proxy-only (no audio is interpreted or recorded here).
    os.chmod(slot, 0o755)
    try:
        os.unlink(LISTEN)
    except FileNotFoundError:
        pass
    # The sandbox path Flatpak advertises is /run/flatpak/pulse.  The launcher
    # mounts this slot there, but /run itself (tmpfs) is recreated at boot, so
    # the sandbox destination only needs to exist on the host when a client
    # asks for it directly; create it as a traversable empty dir so a stale
    # root-owned directory can never make the mount fail.
    dest = os.environ.get("NUXEL_FLATPAK_PULSE_DEST", "/run/flatpak/pulse")
    try:
        os.makedirs(dest, mode=0o755, exist_ok=True)
        os.chmod(dest, 0o755)
    except OSError as exc:
        log("sandbox pulse dir unavailable: %s" % exc)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(LISTEN)
    os.chmod(LISTEN, 0o777)
    srv.listen(64)
    write_client_conf(slot)
    log("listening %s -> %s (client.conf published)" % (LISTEN, TARGET))
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
