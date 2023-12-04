# This is an implementation of ALTO server
# The server can: Register a peer, Unregister a peer, Get the best peer for a peer
# ALTO server cannot go offline, it is always online
# It uses networkx library to store the topology and all the metrics
# Topology is stored in a json file (../config/topology.json)
# Peers are stored in a json file (../config/peers.json)
# Server IP and port are stored in a json file (../config/server.json)
# It uses HTTP protocol to communicate with the peers

# Importing required libraries

import socket
import sys
import json
import threading
import time
import os
import subprocess
import networkx as nx

# Global variables

peers = {}
data = {}
graph = nx.Graph()
peer_lock = threading.Lock()
graph_lock = threading.Lock()

topo_file = '../config/topology.json'
peer_file = '../config/peers.json'

server_IP = ''
server_port = ''

# Function to write HTTP response

def write_http_response(status_code, status_message, data):
    response = "HTTP/1.1 " + str(status_code) + " " + status_message + "\r\n"
    response += "Content-Type: application/json\r\n"
    response += "\r\n"
    response += json.dumps(data)
    return response.encode()

# Function to set up Global variables from peers.json and topo_file

def setup():
    global peers
    global graph
    # with open(peer_file) as f:
    #     peers = json.load(f)
    with open(topo_file) as f:
        graph = nx.readwrite.json_graph.node_link_graph(json.load(f))
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
        return write_http_response(409, "Conflict", {"message": "Peer already registered"})
    else:
        peers[peer_ip] = {"ip": peer_ip, "port": peer_port}
        peer_lock.release()
        graph_lock.acquire()
        graph.add_node(peer_ip)
        graph_lock.release()
        with open(peer_file, 'w') as f:
            json.dump(peers, f, indent=4)
        print("Peer registered successfully")
        return write_http_response(200, "OK", {"message": "Peer registered successfully"})
    
# Function to unregister a peer

def unregister_peer(peer_ip):
    global peers
    global graph
    global peer_lock
    global graph_lock
    peer_lock.acquire()
    if peer_ip not in peers:
        peer_lock.release()
        return write_http_response(404, "Not Found", {"message": "Peer not registered"})
    else:
        del peers[peer_ip]
        peer_lock.release()
        graph_lock.acquire()
        graph.remove_node(peer_ip)
        graph_lock.release()
        with open(peer_file, 'w') as f:
            json.dump(peers, f, indent=4)
        print("Peer unregistered successfully")
        return write_http_response(200, "OK", {"message": "Peer unregistered successfully"})
    
# Function to get hop count between two peers

def get_hop_count(peer1, peer2):
    global graph
    return nx.shortest_path_length(graph, peer1, peer2)

# Function to get bandwidth between two peers

def get_bandwidth(peer1, peer2):
    global graph
    return graph[peer1][peer2]['bw']

# Function to get delay between two peers

def get_delay(peer1, peer2):
    global graph
    return graph[peer1][peer2]['delay']

# Function to get the cost between two peers

def get_cost(peer1, peer2):
    global graph
    if peer1 not in graph:
        return -1
    if peer2 not in graph:
        return -1
    hc = get_hop_count(peer1, peer2)
    bw = get_bandwidth(peer1, peer2)
    delay = get_delay(peer1, peer2)
    return -1 # TODO: Calculate cost
    
# Function to get the best peer for a peer

def get_best_peer(peer_ip):
    global peers
    global peer_lock
    global graph_lock
    peer_lock.acquire()
    if peer_ip not in peers:
        peer_lock.release()
        return write_http_response(404, "Not Found", {"message": "Peer not registered"})
    else:
        peer_lock.release()
        graph_lock.acquire()
        best_peer = None
        best_cost = -1
        for peer in peers:
            if peer == peer_ip:
                continue
            peer2_ip = peers[peer]['ip']
            cost = get_cost(peer_ip, peer2_ip)
            if cost == -1:
                continue
            if cost > best_cost:
                best_cost = cost
                best_peer = peer
        graph_lock.release()
        if best_peer == None:
            return write_http_response(404, "Not Found", {"message": "No peer found"})
        return write_http_response(200, "OK", {"peer": peers[best_peer]})
    
# Function to get list of available files

def get_list_files():
    global data
    return write_http_response(200, "OK", {"files": data})


# Function to handle a client

def handle_client(client_socket, client_address):
    global peers
    global peer_lock
    global graph_lock
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        data = data.decode()
        data = data.split('\r\n')
        data = data[-1]
        data = json.loads(data)
        if data['type'] == "register":
            response = register_peer(data['ip'], data['port'])
        elif data['type'] == "unregister":
            response = unregister_peer(data['ip'])
        elif data['type'] == "get_best_peer":
            response = get_best_peer(data['ip'])
        else:
            response = write_http_response(400, "Bad Request", {"message": "Invalid request"})
        client_socket.sendall(response)
    client_socket.close()
    print("Client disconnected")

# Function to start the server

def start_server():
    global peers
    global peer_lock
    global graph_lock
    print("Starting server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_IP, server_port))
    server_socket.listen(5)
    print("Server started successfully")
    while True:
        client_socket, client_address = server_socket.accept()
        print("Client connected")
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()

# Main function

if __name__ == '__main__':
    setup()
    start_server()        