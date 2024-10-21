from __future__ import annotations
from albert import *
from enum import Enum
from pydbus import SystemBus
import os
from pathlib import Path
from typing import List

md_iid = "2.4"
md_version = "0.6"
md_name = "NetworkManager Control"
md_description = "Manage NetworkManager connections over DBus"
md_license = "MIT"
md_url = "https://github.com/Nightfeather/albert-nm"
md_authors = "@Nightfeather"
md_lib_dependencies = [ 'pydbus', 'pygobject' ]
md_bin_dependencies = [ "NetworkManager", "nm-connection-editor" ]

NM_DBUS_NAME = 'org.freedesktop.NetworkManager'

class DeviceType(Enum):
    UNKNWON = 0
    ETHERNET = 1
    WIFI = 2
    UNUSED1 = 3
    UNUSED = 4
    BT = 5
    OLPC_MESH = 6
    WIMAX = 7
    MODEM = 8
    INFINIBAND = 9
    BOND = 10
    VLAN = 11
    ADSL = 12
    BRIDGE = 13
    GENERIC = 14
    TEAM = 15
    TUN = 16
    IP_TUNNEL = 17
    MACVLAN = 18
    VXLAN = 19
    VETH = 20
    WIREGUARD = 29
    WIFI_P2P = 30

class Plugin(PluginInstance, TriggerQueryHandler):
    def __init__(self):
        TriggerQueryHandler.__init__(self, md_id, md_name, md_description, '<Connection> [Device]', 'nm')
        PluginInstance.__init__(self, [self])

        self.bus = SystemBus()
        self.bus.autoclose = True
        self.daemon = self.bus.get(NM_DBUS_NAME)

    def make_item(self, *, device, connection, active = None):
        connName = connection.GetSettings()['connection']['id']
        desc = f"Interface: {device.Interface}"
        actions = []

        icon = ['xdg:unknown']

        if device.DeviceType in ( 2, 5, 6, 7, 30 ):
            icon = ['xdg:network-wireless']
        elif device.DeviceType in ( 16, 17, 29 ):
            icon = ['xdg:network-vpn']
        elif device.DeviceType in (1, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19):
            icon = ['xdg:network-wired']

        disp = connName

        if connection.Flags & 0x8 > 0:
            desc += ", External"

        if active:
            disp = f"* {disp}"
            actions.append(
                Action("reactivate", "Reactivate", lambda *_: self.daemon.ActivateConnection(connection._path, device._path, "/")),
            )
            actions.append(
                Action("deactivate", "Deactivate", lambda *_: self.daemon.DeactivateConnection(active._path))
            )
        else:
            actions.append(
                Action("activate", "Activate", lambda *_: self.daemon.ActivateConnection(connection._path, device._path, "/")),
            )

        return StandardItem(
            f"nm-connection-{device.Interface}-{connName}",
            disp, desc, f"{connName} {device.Interface}",
            icon, actions
        )

    def list_devices(self):
        devices = []
        for d in self.daemon.AllDevices:
            dev = self.bus.get(NM_DBUS_NAME, d)
            if not dev.Managed or not dev.Real:
                continue
            devices.append(dev)
        return devices

    def list_available_connections(self, devices):
        connections = []
        for dev in devices:
            for c in dev.AvailableConnections:
                conn = self.bus.get(NM_DBUS_NAME, c)
                connections.append((conn, dev))
        return connections

    def list_active_connections(self, devices):
        connections = []
        for dev in devices:
            if dev.ActiveConnection != '/':
                aconn = self.bus.get(NM_DBUS_NAME, dev.ActiveConnection)
                conn = self.bus.get(NM_DBUS_NAME, aconn.Connection)
                connections.append((conn, dev))
        return connections

    def enumerate_connections(self, matchConnection = "", matchDevice = ""):
        devices = self.list_devices()
        if matchDevice != "":
            devices = [ dev for dev in devices if dev.Interface.startswith(matchDevice.lower()) ]

        connections = self.list_available_connections(devices)
        if matchConnection != "":
            connections = [ conn for conn in connections if conn[0].GetSettings()['connection']['id'].lower().startswith(matchConnection.lower()) ]
        active_connections = self.list_active_connections(devices)

        items = []

        for conn, dev in connections:
            is_active = next(filter((lambda args: args[0].Filename == conn.Filename and args[1].Interface == dev.Interface), active_connections), None) is not None
            item = self.make_item(device=dev, connection=conn, active=is_active)
            items.append(item)

        return items

    def handleTriggerQuery(self, query: TriggerQuery):
        args = query.string.strip().split()

        query.add(self.enumerate_connections(*args))

