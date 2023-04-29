from albert import *
from enum import Enum
from pydbus import SystemBus
import os
from pathlib import Path

md_iid = "0.5"
md_id = "nm"
md_version = "0.5"
md_name = "NetworkManager Control"
md_description = "Manage NetworkManager connections over DBus"
md_license = "MIT"
md_url = "https://github.com/Nightfeather/albert-nm"
md_maintainers = "@Nightfeather"
md_bin_dependencies = [ "NetworkManager", "nm-connection-editor" ]

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

class Plugin(QueryHandler):

    def id(self):
        return md_id

    def name(self):
        return md_name

    def description(self):
        return md_description

    def initialize(self):
        self.bus = SystemBus()
        self.bus.autoclose = True
        self.daemon = self.bus.get("org.freedesktop.NetworkManager")

    def finalize(self):
        pass

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
        else:
            if active is not None:
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
    
        return Item(
            id=f"nm-connection-{device.Interface}-{connName}",
            icon=icon,
            text=disp,
            subtext=desc,
            completion=f"nm {device.Interface} {connName}",
            actions=actions
        )
    
    def enumerate_connections(self, candA = None, candB = None):
        candidates = []
        for d in self.daemon.AllDevices:
            dev = self.bus.get('org.freedesktop.NetworkManager', d)
            if not dev.Managed or not dev.Real:
                continue
    
            active_conn = None
            if dev.ActiveConnection != '/':
                aconn = self.bus.get('org.freedesktop.NetworkManager', dev.ActiveConnection)
                active_conn = aconn.Connection
                conn = self.bus.get('org.freedesktop.NetworkManager', aconn.Connection)
                candidates.append({ 'device': dev, 'connection': conn, 'active': aconn})
    
            for c in dev.AvailableConnections:
                if c == active_conn:
                    continue
                conn = self.bus.get('org.freedesktop.NetworkManager', c)
                candidates.append({ 'device': dev, 'connection': conn, 'active': None})
    
        if candA is not None:
            candidates = filter(lambda c: (
                c['device'].Interface.startswith(candA) or
                c['connection'].GetSettings()['connection']['id'].lower().startswith(candB or candA)
            ), candidates)
    
        return [ self.make_item(**ct) for ct in sorted(candidates, key=lambda c: (c['active'] is None, c['connection'].GetSettings()['connection']['id'], c['device'].Interface) )]
    
    def handleQuery(self, query: Query):
    
        if not query.isValid:
            return
    
        cand = (query.string.strip().split() + [None, None])[:2]
    
        for item in self.enumerate_connections(*cand):
            query.add(item)

