from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.link import TCLink
from p4_mininet import P4Switch, P4Host
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
P4_JSON_PATH = os.path.join(CURRENT_DIR, 'p4_compiled.json')

class EnterpriseDDoSTopo(Topo):
    def __init__(self, **opts):
        super().__init__(**opts)

        # ==========================================================
        # P4 SWITCH
        # ==========================================================
        s1 = self.addSwitch(
            's1',
            sw_path='simple_switch',
            json_path=P4_JSON_PATH,
            thrift_port=9090,
            pcap_dump=False
        )

        # ==========================================================
        # EXTERNAL ZONE
        # ==========================================================

        # Legitimate User
        h1_user = self.addHost(
            'h1',
            ip='10.0.0.1/24',
            mac='00:00:00:00:00:01'
        )

        # Botnet / Attacker
        h2_attacker = self.addHost(
            'h2',
            ip='10.0.0.2/24',
            mac='00:00:00:00:00:02'
        )

        # ==========================================================
        # DMZ ZONE
        # ==========================================================

        # Victim Server
        h3_server = self.addHost(
            'h3',
            ip='10.0.0.3/24',
            mac='00:00:00:00:00:03'
        )

        # ==========================================================
        # INTERNAL ZONE
        # ==========================================================

        # Internal Employee Workstation
        h4_internal = self.addHost(
            'h4',
            ip='10.0.0.4/24',
            mac='00:00:00:00:00:04'
        )

        # ==========================================================
        # SOC / MONITORING ZONE
        # ==========================================================

        # IDS / SOC Sensor
        h5_soc = self.addHost(
            'h5',
            ip='10.0.0.5/24',
            mac='00:00:00:00:00:05'
        )

        # ==========================================================
        # LINK CONFIGURATION
        # ==========================================================

        # Internet links
        self.addLink(
            h1_user,
            s1,
            port2=1,
            cls=TCLink,
            bw=100,
            delay='5ms'
        )

        self.addLink(
            h2_attacker,
            s1,
            port2=2,
            cls=TCLink,
            bw=100,
            delay='5ms'
        )

        # DMZ Server bottleneck
        self.addLink(
            h3_server,
            s1,
            port2=3,
            cls=TCLink,
            bw=10,
            delay='1ms'
        )

        # Internal LAN
        self.addLink(
            h4_internal,
            s1,
            port2=4,
            cls=TCLink,
            bw=20,
            delay='1ms'
        )

        # SOC Monitoring LAN
        self.addLink(
            h5_soc,
            s1,
            port2=5,
            cls=TCLink,
            bw=20,
            delay='1ms'
        )


def disable_ipv6():
    """
    Disable IPv6 to reduce unwanted background traffic.
    """

    print("[*] Disabling IPv6...")

    cmds = [
        "sysctl -w net.ipv6.conf.all.disable_ipv6=1",
        "sysctl -w net.ipv6.conf.default.disable_ipv6=1",
        "sysctl -w net.ipv6.conf.lo.disable_ipv6=1"
    ]

    for cmd in cmds:
        os.system(f"{cmd} > /dev/null 2>&1")


if __name__ == '__main__':

    disable_ipv6()

    topo = EnterpriseDDoSTopo()

    net = Mininet(
        topo=topo,
        host=P4Host,
        switch=P4Switch,
        controller=None
    )

    print("\n" + "=" * 65)
    print("🚀 ENTERPRISE SDN/P4 DDoS TESTBED")
    print("=" * 65)
    print("Switch:")
    print("  [+] s1 (BMv2 P4 Switch)")
    print("  [+] Thrift Port: 9090")
    print("")
    print("Hosts:")
    print("  [+] h1 = Legitimate User")
    print("  [+] h2 = Botnet Attacker")
    print("  [+] h3 = Victim Server")
    print("  [+] h4 = Internal Client")
    print("  [+] h5 = SOC Sensor")
    print("")
    print("Bandwidth:")
    print("  [+] h1 -> s1 : 100 Mbps")
    print("  [+] h2 -> s1 : 100 Mbps")
    print("  [+] h3 -> s1 : 10 Mbps (Bottleneck)")
    print("  [+] h4 -> s1 : 20 Mbps")
    print("  [+] h5 -> s1 : 20 Mbps")
    print("=" * 65 + "\n")

    net.start()

    print("[+] Tắt checksum/segmentation offload trên mọi host (bắt buộc cho BMv2 + TCP)...")
    for h in net.hosts:
        h.cmd('ethtool -K eth0 tx off rx off tso off gso off gro off lro off 2>/dev/null')
    print("✅ Đã tắt offload trên toàn bộ host.")

    print("[+] Configuring static ARP entries...")
    net.staticArp()            
    print("[+] Static ARP entries configured.")

    print("[+] Network started successfully.")
    print("[+] Verify connectivity with: pingall")
    print("[+] Open terminals:")
    print("    xterm h1 h2 h3 h4 h5")
    print("")

    CLI(net)

    net.stop()