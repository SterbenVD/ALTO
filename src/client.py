# This is an implementation of the P2P client
# Such a node can: Send/Receive files, Ask for the best peer to download from ALTO server
# Nodes can also go offline(Does not happen during file transfer) and come back online

import socket
import sys
import os
import time
import threading
import json

data = []
my_ip = ''
my_port = ''

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
        sock.sendall(request.encode())
        # Receive response from the server
        response = sock.recv(1024)
        response = response.decode()
        print(response)
        if response == "Peer not registered" or response == "No peer found":
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
        sock.sendall(request.encode())
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
                client_socket.sendall(str(my_port).encode())
                send_file(req_file, peer_ip, peer_port)
            else:
                client_socket.sendall("File not found".encode())
        else:
            client_socket.sendall("Invalid request".encode())
    client_socket.close()
    print("Connection closed from " + str(client_address))

# Function to start the client

def start_client():
    global data
    global my_ip
    global my_port

# Main function

def main():
    global data
    global my_ip
    global my_port
    # Get my IP address
    my_ip = socket.gethostbyname(socket.gethostname())
    # Get my port number
    my_port = int(sys.argv[1])
    # Start the client
    start_client()

# Start the main function in a thread

t = threading.Thread(target=main)
t.start()

# Main thread

while True:
    # Get user input
    pass
