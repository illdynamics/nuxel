#!/usr/bin/env python3
"""Narrow GeoClue2 agent for the Nuxel bridge UID.

GeoClue2 requires an agent for the caller's UID before Manager.GetClient will
complete.  The agent must answer GeoClue's property callback while the caller is
blocked in GetClient, so it cannot live inside the bridge's single-threaded
D-Bus main loop (that was the original NoReply deadlock).

This process runs as the SAME Unix user as nuxel-bridge and registers itself
with GeoClue.  It authorizes only the bridge's documented desktop id; PWAs never
talk to GeoClue directly and per-app location capabilities remain enforced by
nuxel-bridge.
"""
from __future__ import annotations

import logging
import os
import sys

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    from gi.repository import GLib
except ImportError as exc:  # pragma: no cover - deployment dependency check
    print('nuxel-geoclue-agent: dbus-python/gi missing: %s' % exc, file=sys.stderr)
    sys.exit(1)

BUS = 'org.freedesktop.GeoClue2'
MANAGER_PATH = '/org/freedesktop/GeoClue2/Manager'
AGENT_PATH = '/org/freedesktop/GeoClue2/Agent'
DESKTOP_ID = os.environ.get('NUXEL_GEOCLUE_AGENT_ID', 'org.nuxel.Bridge')
MAX_ACCURACY = int(os.environ.get('NUXEL_GEOCLUE_MAX_ACCURACY', '8'))

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] nuxel-geoclue-agent: %(message)s')
logger = logging.getLogger('nuxel-geoclue-agent')


class Agent(dbus.service.Object):
    @dbus.service.method('org.freedesktop.GeoClue2.Agent',
                         in_signature='su', out_signature='bu')
    def AuthorizeApp(self, desktop_id, requested_accuracy):
        authorized = (str(desktop_id) == DESKTOP_ID)
        logger.info('AuthorizeApp desktop=%s accuracy=%s -> %s',
                    desktop_id, requested_accuracy, authorized)
        try:
            requested = int(requested_accuracy)
        except (TypeError, ValueError):
            requested = MAX_ACCURACY
        return (dbus.Boolean(authorized), dbus.UInt32(min(requested, MAX_ACCURACY)))

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        if prop == 'MaxAccuracyLevel':
            return dbus.UInt32(MAX_ACCURACY)
        raise dbus.exceptions.DBusException(
            'Unknown property %s' % prop,
            name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        return {'MaxAccuracyLevel': dbus.UInt32(MAX_ACCURACY)}


class AgentRegistrar:
    def __init__(self, bus):
        self.bus = bus
        self.agent = Agent(bus, AGENT_PATH)
        self._pending = False
        self._owned = False

    def _manager(self):
        return dbus.Interface(self.bus.get_object(BUS, MANAGER_PATH),
                              'org.freedesktop.GeoClue2.Manager')

    def register(self):
        if self._pending:
            return False
        self._pending = True
        logger.info('registering GeoClue agent for %s', DESKTOP_ID)
        try:
            self._manager().AddAgent(
                DESKTOP_ID,
                timeout=30.0,
                reply_handler=self._on_registered,
                error_handler=self._on_error)
        except Exception as exc:
            self._pending = False
            logger.warning('AddAgent dispatch failed: %s', exc)
        return False

    def _on_registered(self):
        self._pending = False
        self._owned = True
        logger.info('GeoClue agent registered for %s', DESKTOP_ID)

    def _on_error(self, exc):
        self._pending = False
        self._owned = False
        logger.warning('AddAgent failed: %s', exc)

    def on_name_owner_changed(self, name, old_owner, new_owner):
        if str(name) != BUS:
            return
        if new_owner:
            logger.info('GeoClue appeared (%s); registering agent', new_owner)
            GLib.timeout_add_seconds(1, self.register)
        else:
            logger.info('GeoClue exited; agent will re-register on next start')
            self._owned = False


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    registrar = AgentRegistrar(bus)
    bus_iface = dbus.Interface(
        bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'),
        'org.freedesktop.DBus')
    bus_iface.connect_to_signal('NameOwnerChanged', registrar.on_name_owner_changed)
    # If GeoClue is already running, register immediately.  Otherwise the
    # NameOwnerChanged signal above handles activation.
    try:
        bus.get_object(BUS, MANAGER_PATH)
        GLib.timeout_add_seconds(1, registrar.register)
    except Exception:
        pass
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()


if __name__ == '__main__':
    main()
