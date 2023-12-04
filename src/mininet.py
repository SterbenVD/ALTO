# Importing required libraries

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
import json

setup_script = 'setup.sh'

class MyTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        # Topo.json is a file that contains the topology of the network
        with open('../config/topo.json') as f:
            topology = json.load(f)
        # Adding hosts
        for host in topology['hosts']:
            self.addHost(name=host['name'], ip=host['ip'])
        # Adding switches
        for switch in topology['switches']:
            self.addSwitch(name=switch['name'])
        # Adding links
        for link in topology['links']:
            self.addLink(link['src'], link['dst'], delay=link['delay'], bw=link['bw'])

topos = {'mytopo': (lambda: MyTopo())}

if __name__ == '__main__':
    topo = MyTopo()
    net = Mininet(topo)
    net.start()
    CLI(net, script=setup_script)
    CLI(net)
    net.stop()