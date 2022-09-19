from albert import *
from enum import Enum
from pydbus import SystemBus
import os
from pathlib import Path

__title__ = "NetworkManager Control"
__doc__ = "Manage NetworkManager connections over DBus"
__authors__ = "Nightfeather"
__version__ = "0.4.1"
__triggers__ = "nm "
__py_deps__ = ["pydbus"]
__exec_deps__ = ["NetworkManager", "nm-connection-editor"] # make sure we have NetworkManager on the system

bus = SystemBus()
bus.autoclose = True
daemon = None

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

def initialize():
    global daemon
    daemon = bus.get("org.freedesktop.NetworkManager")

def make_connItem(*, device, connection, active = None):
    connName = connection.GetSettings()['connection']['id']
    desc = f"Interface: {device.Interface}"
    actions = []
    
    icon = iconLookup('unknown', 'default')

    if device.DeviceType in ( 2, 5, 6, 7, 30 ):
        icon = iconLookup('network-wireless', 'default')
    elif device.DeviceType in ( 16, 17, 29 ):
        icon = iconLookup('network-vpn', 'default')
    elif device.DeviceType in (1, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19):
        icon = iconLookup('network-wired', 'default')

    if connection.Flags & 0x8 > 0:
        desc += ", External"
    else:
        if active is not None:
            connName = "* " + connName
            actions.append(
                FuncAction("Reactivate", callable=lambda *_: daemon.ActivateConnection(connection._path, device._path, "/")),
            )
            actions.append(
                FuncAction("Deactivate", callable=lambda *_: daemon.DeactivateConnection(active._path))
            )
        else:
            actions.append(
                FuncAction("Activate", callable=lambda *_: daemon.ActivateConnection(connection._path, device._path, "/")),
            )

    return Item(
        id=f"nm-connection-{device.Interface}-{connName}",
        icon=icon,
        text=connName,
        subtext= desc,
        completion=f"nm {device.Interface} {connName}",
        actions=actions
    )

def enumerate_connections(candA = None, candB = None):
    candidates = []
    for d in daemon.AllDevices:
        dev = bus.get('org.freedesktop.NetworkManager', d)
        if not dev.Managed or not dev.Real:
            continue

        if dev.ActiveConnection != '/':
            aconn = bus.get('org.freedesktop.NetworkManager', dev.ActiveConnection)
            conn = bus.get('org.freedesktop.NetworkManager', aconn.Connection)
            candidates.append({ 'device': dev, 'connection': conn, 'active': aconn})

        for c in dev.AvailableConnections:
            if c is dev.ActiveConnection:
                continue
            conn = bus.get('org.freedesktop.NetworkManager', c)
            candidates.append({ 'device': dev, 'connection': conn, 'active': None})

    if candA is not None:
        candidates = filter(lambda c: c['device'].Interface.startswith(candA) or c['connection'].GetSettings()['connection']['id'].lower().startswith(candA), candidates)
    if candB is not None:
        candidates = filter(lambda c: c['connection'].GetSettings()['connection']['id'].lower().startswith(candB), candidates)

    return [ make_connItem(**ct) for ct in sorted(candidates, key=lambda c: (c['active'] is None, c['connection'].GetSettings()['connection']['id'], c['device'].Interface) )]

def handleQuery(query: Query):

    if not query.isTriggered:
        return

    query.disableSort()
    cand = (query.string.strip().split() + [ None, None])[:2]

    return enumerate_connections(*cand)

