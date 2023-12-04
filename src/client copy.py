# This is an implementation of the P2P client
# Such a node can: Send/Receive files, Ask for the best peer to download from ALTO server
# Nodes can also go offline(Does not happen during file transfer) and come back online
# It uses HTTP protocol for communication
# To send/receive files, it uses TCP protocol

import socket
import sys
import os
import time
import threading
import json

data = []
my_ip = ''
my_port = ''
server_ip = ''
server_port = ''

# Function to write HTTP response

def write_http_response(status_code, status_message, data):
    response = "HTTP/1.1 " + str(status_code) + " " + status_message + "\r\n"
    response += "Content-Type: application/json\r\n"
    response += "\r\n"
    response += json.dumps(data)
    return response.encode()

# Function to write HTTP request

def write_http_request(method, path, data):
    request = method + " " + path + " HTTP/1.1\r\n"
    request += "Content-Type: application/json\r\n"
    request += "\r\n"
    request += json.dumps(data)
    return request.encode()

# Function to send a file to a peer

def send_file(filename, peer_ip, peer_port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (peer_ip, peer_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    try:
        # Open file to be sent
        f = open(filename, 'rb')
        # Send file in chunks of 1024 bytes
        l = f.read(1024)
        while (l):
            sock.send(l)
            l = f.read(1024)
        f.close()
        print("File sent successfully")
    finally:
        print('closing socket')
        sock.close()

# Function to receive a file from a peer

def receive_file(filename, peer_ip, peer_port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the port
    server_address = (peer_ip, peer_port)
    print('starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)
    while True:
        # Wait for a connection
        print('waiting for a connection')
        connection, client_address = sock.accept()
        try:
            print('connection from', client_address)
            # Open file to be received
            f = open(filename, 'wb')
            # Receive file in chunks of 1024 bytes
            while True:
                data = connection.recv(1024)
                if not data:
                    break
                f.write(data)
            f.close()
            print("File received successfully")
        finally:
            # Clean up the connection
            connection.close()
            break

# Function to get the best peer from the ALTO server

def get_best_peer(server_ip, server_port, req_file):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (server_ip, server_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    try:
        # Send request for the best peer
        request = {}
        request['type'] = 'get_best_peer'
        request['ip'] = my_ip
        request['port'] = my_port
        request['file'] = req_file
        request = json.dumps(request)
        sock.sendall(write_http_request("POST", "/get_best_peer", request))
        # Receive response from the server
        response = sock.recv(1024)
        response = response.decode()
        print(response)
        if response == "No peer found":
            return None
        else:
            return response
    finally:
        print('closing socket')
        sock.close()

# Function to handle a peer

def handle_peer(peer_ip, peer_port, req_file):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (peer_ip, peer_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    try:
        # Send request for the file
        request = {}
        request['type'] = 'get_file'
        request['ip'] = my_ip
        request['port'] = my_port
        request['file'] = req_file
        request = json.dumps(request)
        sock.sendall(write_http_request("POST", "/get_file", request))
        # Receive response from the server
        response = sock.recv(1024)
        response = response.decode()
        if response == "Peer not registered" or response == "File not found":
            print(response)
        else:
            print("File found")
            # Receive file
            receive_file(req_file, peer_ip, int(response))
    finally:
        print('closing socket')
        sock.close()

# Function to handle a client

def handle_client(client_socket, client_address):
    global data
    print("Connection from " + str(client_address))
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        data = data.decode()
        data = json.loads(data)
        if data['type'] == 'get_file':
            peer_ip = data['ip']
            peer_port = data['port']
            req_file = data['file']
            if req_file in os.listdir():
                client_socket.sendall(write_http_response(200, "OK", my_port))
                send_file(req_file, peer_ip, peer_port)
            else:
                client_socket.sendall(write_http_response(400, "Bad Request", "File not found"))
        else:
            client_socket.sendall(write_http_response(400, "Bad Request", "Invalid request"))
    client_socket.close()
    print("Connection closed from " + str(client_address))

def register_with_server(server_ip, server_port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (server_ip, server_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    try:
        # Send request for registration
        request = {}
        request['type'] = 'register'
        request['ip'] = my_ip
        request['port'] = my_port
        request = json.dumps(request)
        sock.sendall(write_http_request("POST", "/register", request))
        # Receive response from the server
        response = sock.recv(1024)
        response = response.decode()
        print(response)
        if response == "Registered successfully":
            return True
        else:
            return False
    finally:
        print('closing socket')
        sock.close()

def unregister_with_server(server_ip, server_port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (server_ip, server_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    try:
        # Send request for unregistration
        request = {}
        request['type'] = 'unregister'
        request['ip'] = my_ip
        request = json.dumps(request)
        sock.sendall(write_http_request("POST", "/unregister", request))
        # Receive response from the server
        response = sock.recv(1024)
        response = response.decode()
        print(response)
        if response == "Unregistered successfully":
            return True
        else:
            return False
    finally:
        print('closing socket')
        sock.close()

# Function to start the client

def start_client():
    global data
    global my_ip
    global my_port
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the port
    server_address = (my_ip, my_port)
    # print('starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)
    while True:
        # Wait for a connection
        # print('waiting for a connection')
        connection, client_address = sock.accept()
        try:
            print('connection from', client_address)
            # Handle the client
            t = threading.Thread(target=handle_client, args=(connection, client_address))
            t.start()
        finally:
            pass

# Main function

def main():
    global data
    global my_ip
    global my_port
    global server_ip
    global server_port
    # Get my IP address
    my_ip = socket.gethostbyname(socket.gethostname())
    # Get my port number
    my_port = int(sys.argv[1])
    # Set up the server
    with open('../config/server.json') as f:
        server = json.load(f)
    server_ip = server['ip']
    server_port = server['port']

    # Start the client
    start_client()

# Start the main function in a thread

t = threading.Thread(target=main)
t.start()

# Main thread

while True:
    # Get the command
    cmd = input("Enter command: ")
    cmd = cmd.split()
    if cmd[0] == "get":
        # Get the file name
        req_file = cmd[1]
        # Get the best peer from the ALTO server
        best_peer = get_best_peer(server_ip, server_port, req_file)
        if best_peer == None:
            print("No peer found")
        else:
            # Handle the peer
            best_peer = best_peer.split()
            handle_peer(best_peer[0], int(best_peer[1]), req_file)
    elif cmd[0] == "register":
        # Register with the ALTO server
        if register_with_server(server_ip, server_port):
            print("Registered successfully")
        else:
            print("Registration failed")
    elif cmd[0] == "unregister":
        # Unregister with the ALTO server
        if unregister_with_server(server_ip, server_port):
            print("Unregistered successfully")
        else:
            print("Unregistration failed")
    elif cmd[0] == "exit":
        # Exit the program
        os._exit(0)
    else:
        print("Invalid command")
