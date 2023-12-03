# This is an implementation of ALTO server
# The server can: Register a peer, Unregister a peer, Get the best peer for a peer
# ALTO server cannot go offline, it is always online
# It uses networkx library to store the topology and all the metrics
# Topology is stored in a json file (../config/topo.json)

# Importing required libraries

import socket
import sys
import json
import threading
import time
import os
import subprocess
import networkx as nx

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI

# Global variables

peers = {}
graph = nx.Graph()
peer_lock = threading.Lock()
graph_lock = threading.Lock()

topo_file = '../config/topo.json'
peer_file = '../config/peers.json'

server_IP = ''
server_port = ''

# Function to set up Global variables from peers.json and topo_file

def setup():
    global peers
    global graph
    with open(peer_file) as f:
        peers = json.load(f)
    # Fix this later
    # with open(topo_file) as f:
    #     graph = nx.readwrite.json_graph.node_link_graph(json.load(f))
    print("Peers and Graph loaded successfully")
    
    # Read server IP and port from config file
    global server_IP
    global server_port
    with open('../config/server.json') as f:
        server = json.load(f)
    server_IP = server['ip']
    server_port = server['port']

# Function to register a peer

def register_peer(peer_ip, peer_port):
    global peers
    global graph
    global peer_lock
    global graph_lock
    peer_lock.acquire()
    if peer_ip in peers:
        peer_lock.release()
        return False
    peers[peer_ip] = peer_port
    peer_lock.release()
    graph_lock.acquire()
    graph.add_node(peer_ip)
    graph_lock.release()
    return True

# Function to unregister a peer

def unregister_peer(peer_ip):
    global peers
    global graph
    global peer_lock
    global graph_lock
    peer_lock.acquire()
    if peer_ip not in peers:
        peer_lock.release()
        return False
    del peers[peer_ip]
    peer_lock.release()
    graph_lock.acquire()
    graph.remove_node(peer_ip)
    graph_lock.release()
    return True

# This is implementation of finding cost between two peers in mininet network
# The cost is calculated using the following metrics: hop count, bandwidth, delay

# Find hop count between two peers

def find_hop_count(peer1, peer2):
    global graph
    return nx.shortest_path_length(graph, peer1, peer2)

# Find bandwidth between two peers

def find_bandwidth(peer1, peer2):
    global graph
    return graph[peer1][peer2]['bw']

# Find delay between two peers

def find_delay(peer1, peer2):
    global graph
    return graph[peer1][peer2]['delay']

# Find cost between two peers

def find_cost(peer1, peer2):
    hc = find_hop_count(peer1, peer2)
    bw = find_bandwidth(peer1, peer2)
    delay = find_delay(peer1, peer2)
    return -1 # TODO: Calculate cost using hc, bw and delay

# Function to find the best peer for a peer

def find_best_peer(peer_ip):
    global peers
    global peer_lock
    global graph_lock
    peer_lock.acquire()
    if peer_ip not in peers:
        peer_lock.release()
        return False
    peer_lock.release()
    graph_lock.acquire()
    best_peer = None
    best_cost = 0
    for peer in peers:
        if peer == peer_ip:
            continue
        cost = find_cost(peer_ip, peer)
        if best_peer == None or cost < best_cost:
            best_peer = peer
            best_cost = cost
    graph_lock.release()
    return best_peer

# Function to handle a client

def handle_client(client_socket, client_address):
    global peers
    global peer_lock
    global graph_lock
    print("Connection from " + str(client_address))
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        data = data.decode()
        data = json.loads(data)
        if data['type'] == 'register':
            peer_ip = data['ip']
            peer_port = data['port']
            if register_peer(peer_ip, peer_port):
                client_socket.sendall("Registered successfully".encode())
            else:
                client_socket.sendall("Registration failed".encode())
        elif data['type'] == 'unregister':
            peer_ip = data['ip']
            if unregister_peer(peer_ip):
                client_socket.sendall("Unregistered successfully".encode())
            else:
                client_socket.sendall("Unregistration failed".encode())
        elif data['type'] == 'get_best_peer':
            peer_ip = data['ip']
            best_peer = find_best_peer(peer_ip)
            if best_peer == False:
                client_socket.sendall("Peer not registered".encode())
            elif best_peer == None:
                client_socket.sendall("No peer found".encode())
            else:
                client_socket.sendall(best_peer.encode())
        else:
            client_socket.sendall("Invalid request".encode())
    client_socket.close()
    print("Connection closed from " + str(client_address))

# Function to start the server

def start_server():
    global peers
    global peer_lock
    global graph_lock
    setup()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_IP, server_port))
    server_socket.listen(5)
    print("Server started")
    while True:
        client_socket, client_address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == '__main__':
    start_server()