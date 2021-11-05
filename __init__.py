from albert import *
from enum import Enum
from pydbus import SystemBus
import os

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

def make_connItem(dev, c, is_active = False):
    conn = bus.get('org.freedesktop.NetworkManager', c)
    connName = os.path.basename(conn.Filename).rsplit(".", maxsplit=1)[0]
    name = connName
    desc = f"Interface: {dev.Interface}"
    actions = []
    
    icon = iconLookup('unknown', 'default')

    if dev.DeviceType in ( 2, 5, 6, 7, 30 ):
        icon = iconLookup('network-wireless', 'default')
    elif dev.DeviceType in ( 16, 17, 29 ):
        icon = iconLookup('network-vpn', 'default')
    elif dev.DeviceType in (1, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19):
        icon = iconLookup('network-wired', 'default')

    if conn.Flags & 0x8 > 0:
        desc += ", External"
    else:
        actions.append(
            FuncAction("Activate", callable=lambda *_: daemon.ActivateConnection(c, dev._path, "/")),
        )

        if is_active:
            name = "* " + name
            actions.append(
                FuncAction("Disconnect", callable=lambda *_: dev.Disconnect())
            )

    return Item(
        id=f"nm-conn-{dev.Interface}-{connName}",
        icon=icon,
        text=name,
        subtext= desc,
        completion=f"nm {dev.Interface} {connName}",
        actions=actions
    )


def enumerate_connections(devcand = "", conncand = ""):
    items = []
    for d in daemon.GetAllDevices():
        dev = bus.get('org.freedesktop.NetworkManager', d)
        if not dev.Managed or not dev.Real:
            continue

        if len(devcand) > 0 and not dev.Interface.startswith(devcand):
            continue

        active_conn = "/"
        if dev.ActiveConnection != '/':
            aconn = bus.get('org.freedesktop.NetworkManager', dev.ActiveConnection)
            active_conn = aconn.Connection

            items.append(make_connItem(dev, active_conn, True))

        for c in dev.AvailableConnections:
            if c != active_conn:
               items.append(make_connItem(dev, c))

    return items

def handleQuery(query: Query):

    if not query.isTriggered:
        return

    query.disableSort()
    cand = query.string.strip().split() + ["", ""]

    return enumerate_connections(cand[0], cand[1])

