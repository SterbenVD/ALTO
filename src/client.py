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

# Function to write HTTP request

def write_http_request(method, path, data):
    request = method + " " + path + " HTTP/1.1\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Content-Length: " + str(len(data)) + "\r\n"
    request += "\r\n"
    request += data
    return request.encode()

# Function to write HTTP response

def write_http_response(status_code, status_message, data):
    response = "HTTP/1.1 " + str(status_code) + " " + status_message + "\r\n"
    response += "Content-Type: application/json\r\n"
    response += "\r\n"
    response += json.dumps(data)
    return response.encode()

# Function to send file to a peer

def send_file(peer_ip, peer_port, file_name):
    print("Sending file to peer: " + peer_ip + ":" + str(peer_port))
    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the peer
    s.connect((peer_ip, peer_port))
    # Open the file to be sent
    f = open(file_name, 'rb')
    # Read the file and send it to the peer
    l = f.read(1024)
    while(l):
        s.send(l)
        l = f.read(1024)
    f.close()
    s.close()
    print("File sent to peer: " + peer_ip + ":" + str(peer_port))

# Function to receive file from a peer

def receive_file(peer_ip, peer_port, file_name):
    print("Receiving file from peer: " + peer_ip + ":" + str(peer_port))
    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to a port
    s.bind((my_ip, my_port))
    # Listen for incoming connections
    s.listen(1)
    # Accept the incoming connection
    conn, addr = s.accept()
    # Open the file to store the received file
    f = open(file_name, 'wb')
    # Receive the file and store it
    l = conn.recv(1024)
    while(l):
        f.write(l)
        l = conn.recv(1024)
    f.close()
    conn.close()
    s.close()
    print("File received from peer: " + peer_ip + ":" + str(peer_port))

# Function to get the best peer to download a file from ALTO server

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

def get_best_peer(file_name):
    print("Getting best peer to download file: " + file_name)
    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the ALTO server
    s.connect((server_ip, server_port))
    # Write the HTTP request
    request = write_http_request("GET", "/bestpeer/" + file_name, "")
    s.send(request)
    # Read the HTTP response
    response = s.recv(1024)
    response = response.decode()
    # Parse the HTTP response
    response = response.split("\r\n\r\n")
    response = response[1]
    response = json.loads(response)
    # Return the peer IP and port
    return response['ip'], response['port']

# Function to handle requests from other peers

def handle_peer(peer_socket, peer_address):
    print("Handling peer: " + peer_address[0] + ":" + str(peer_address[1]))
    # Read the HTTP request
    request = peer_socket.recv(1024)
    request = request.decode()
    # Parse the HTTP request
    request = request.split("\r\n\r\n")
    request = request[1]
    request = json.loads(request)
    # If the request is for a file, send the file
    if request['type'] == "file":
        file_name = request['file_name']
        send_file(peer_address[0], peer_address[1], file_name)
    # Else if the request is for the best peer, get the best peer from ALTO server and send it
    elif request['type'] == "best_peer":
        file_name = request['file_name']
        peer_ip, peer_port = get_best_peer(file_name)
        response = write_http_response(200, "OK", {"ip": peer_ip, "port": peer_port})
        peer_socket.sendall(response)
    # Else if the request is for the list of files, send the list of files
    elif request['type'] == "list_files":
        response = write_http_response(200, "OK", {"files": data})
        peer_socket.sendall(response)
    # Else error
    else:
        response = write_http_response(400, "Bad Request", {"message": "Invalid request"})
        peer_socket.sendall(response)
    peer_socket.close()
    print("Peer handled: " + peer_address[0] + ":" + str(peer_address[1]))

# Function to handle input/output requests from the user 

def handle_user():
    global data
    global my_ip
    global my_port
    global server_ip
    global server_port
    while True:
        # Read the user input
        command = input()
        command = command.split(' ')
        # If the command is to add a file, add the file to the list of files
        if command[0] == "add":
            file_name = command[1]
            data.append(file_name)
            print("File added: " + file_name)
        # Else if the command is to register with ALTO server, register with the server
        elif command[0] == "register":
            if register_with_server(server_ip, server_port):
                print("Registered with server")
            else:
                print("Error registering with server")
        # Else if the command is to unregister with ALTO server, unregister with the server
        elif command[0] == "unregister":
            if unregister_with_server(server_ip, server_port):
                print("Unregistered with server")
            else:
                print("Error unregistering with server")
        # Else if the command is to download a file, get the best peer from ALTO server and download the file from the peer
        elif command[0] == "download":
            file_name = command[1]
            peer_ip, peer_port = get_best_peer(file_name)
            receive_file(peer_ip, peer_port, file_name)
            print("File downloaded: " + file_name)
        # Else if the command is to get the list of files, get the list of files from ALTO server
        elif command[0] == "list":
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, server_port))
            request = write_http_request("GET", "/list", "")
            s.send(request)
            response = s.recv(1024)
            response = response.decode()
            response = response.split("\r\n\r\n")
            response = response[1]
            response = json.loads(response)
            data = response['files']
            print("List of files received")
        # Else if the command is to exit, exit
        elif command[0] == "exit":
            print("Exiting")
            sys.exit(0)
        # Else error
        else:
            print("Invalid command")

# Function to start the peer

def start_peer():
    global data
    global my_ip
    global my_port
    global server_ip
    global server_port
    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to a port
    s.bind((my_ip, my_port))
    # Listen for incoming connections
    s.listen(5)
    # Start a thread to handle user input/output
    user_thread = threading.Thread(target=handle_user)
    user_thread.start()
    while True:
        # Accept the incoming connection
        conn, addr = s.accept()
        # Start a thread to handle the peer
        peer_thread = threading.Thread(target=handle_peer, args=(conn, addr))
        peer_thread.start()

# Function to get the IP and port of the peer

def get_ip_port():
    global my_ip
    global my_port
    global server_ip
    global server_port
    my_ip = socket.gethostbyname(socket.gethostname())
    my_port = int(sys.argv[1])

# Function to get the IP and port of the ALTO server

def get_server_ip_port():
    global my_ip
    global my_port
    global server_ip
    global server_port
    # Read the ALTO server IP and port from the config file
    with open('../config/server.json') as f:
        config = json.load(f)
    server_ip = config['ip']
    server_port = config['port']

# Function to setup the peer

def setup():
    get_ip_port()
    get_server_ip_port()

# Main function

if __name__ == '__main__':
    setup()
    start_peer()
