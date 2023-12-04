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
import matplotlib.pyplot as plt

# Global variables

peers = {}
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
    # Draw graph
    nx.draw(graph, with_labels=True)
    # plt.show()
    plt.savefig("../config/topology.png")
    print("Peers and Graph loaded successfully")
    
    # Read server IP and port from config file
    global server_IP
    global server_port
    with open('../config/server.json') as f:
        server = json.load(f)
    server_IP = server['ip']
    server_port = server['port']
    print("Server IP and port loaded successfully")

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
    peers[peer_ip] = peer_port
    peer_lock.release()
    with open(peer_file, 'w') as f:
        json.dump(peers, f)
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
    del peers[peer_ip]
    peer_lock.release()
    with open(peer_file, 'w') as f:
        json.dump(peers, f)
    print("Peer unregistered successfully")
    return write_http_response(200, "OK", {"message": "Peer unregistered successfully"})

# Function to find best peer for a peer

def find_best_peer(peer):
    global peers
    global graph
    global graph_lock
    global peer_lock
    graph_lock.acquire()
    peer_lock.acquire()
    best_peer = None
    best_hop_count = sys.maxsize
    for peer_ip in peers:
        if peer_ip == peer:
            continue
        try:
            hop_count = nx.shortest_path_length(graph, source = peer, target = peer_ip)
        except:
            hop_count = sys.maxsize
        if hop_count < best_hop_count:
            best_hop_count = hop_count
            best_peer = peer_ip
    peer_lock.release()
    graph_lock.release()
    if best_peer == None:
        return None, None
    return best_peer, peers[best_peer]

# # Function to get list of all peers

# def get_peers():
#     global peers
#     global peer_lock
#     peer_lock.acquire()
#     peer_list = []
#     for peer_ip in peers:
#         peer_list.append(peer_ip)
#     peer_lock.release()
#     return peer_list

# Function to handle a client

def handle_client(client_socket, client_address):
    print("Client connected: " + str(client_address))
    request = client_socket.recv(1024).decode()
    request = request.split('\r\n')
    request_line = request[0].split(' ')
    request_method = request_line[0]
    request_url = request_line[1]
    request_protocol = request_line[2]
    if request_method == "GET":
        if request_url == "/":
            response = write_http_response(200, "OK", {"message": "ALTO server is online"})
        elif request_url == "/register":
            response = write_http_response(400, "Bad Request", {"message": "Missing ip or peer_port"})
        elif request_url == "/unregister":
            response = write_http_response(400, "Bad Request", {"message": "Missing ip"})
        elif request_url == "/bestpeer":
            response = write_http_response(400, "Bad Request", {"message": "Missing ip"})
        # elif request_url == "/peers":
        #     response = write_http_response(200, "OK", {"message": "List of all peers", "peers": peers})
        else:
            response = write_http_response(404, "Not Found", {"message": "Invalid URL"})
    elif request_method == "POST":
        if request_url == "/register":
            data = request[-1]
            data = json.loads(data)
            if 'ip' not in data or 'port' not in data:
                response = write_http_response(400, "Bad Request", {"message": "Missing ip or port"})
            else:
                response = register_peer(data['ip'], data['port'])
        elif request_url == "/unregister":
            data = request[-1]
            data = json.loads(data)
            if 'ip' not in data:
                response = write_http_response(400, "Bad Request", {"message": "Missing ip"})
            else:
                response = unregister_peer(data['ip'])
        elif request_url == "/bestpeer":
            data = request[-1]
            data = json.loads(data)
            if 'ip' not in data:
                response = write_http_response(400, "Bad Request", {"message": "Missing ip"})
            elif data['ip'] not in peers:
                response = write_http_response(404, "Not Found", {"message": "Peer not registered"})
            else:
                best_peer, best_peer_port = find_best_peer(data['ip'])
                if best_peer == None:
                    response = write_http_response(404, "Not Found", {"message": "No peer found"})
                else:
                    response = write_http_response(200, "OK", {"message": "Best peer found", "ip": best_peer, "port": best_peer_port})
        else:
            response = write_http_response(404, "Not Found", {"message": "Invalid URL"})
    else:
        response = write_http_response(400, "Bad Request", {"message": "Invalid request"})

    client_socket.sendall(response)
    client_socket.close()

# Function to start the server

def start_server():
    global server_IP
    global server_port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_IP, server_port))
    server_socket.listen(5)
    print("Server started successfully")
    while True:
        client_socket, client_address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

# Main function

if __name__ == "__main__":
    setup()
    start_server()
