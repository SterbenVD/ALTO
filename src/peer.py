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

files = {}
my_ip = ''
my_port = ''
server_ip = ''
server_port = ''

# Function to write HTTP request

def write_http_request(method, path, data):
    request = method + " " + path + " HTTP/1.1\r\n"
    request += "Host: " + server_ip + ":" + str(server_port) + "\r\n"
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

# Files are just strings in this implementation

# Function to receive file

def receive_file(file_name, file_size, conn):
    global data
    print("Receiving file: " + file_name)
    value = conn.recv(1024).decode()
    files[file_name] = value
    print("File received: " + file_name)

# Function to send file

def send_file(file_name, conn):
    global data
    print("Sending file: " + file_name)
    if file_name not in files:
        print("File not found")
        print("Creating file: " + file_name)
        value = input("Enter file contents: ")
        files[file_name] = value
    value = files[file_name]
    conn.send(value.encode())
    print("File sent: " + file_name)

# Function to send file to peer

def send_file_to_peer(peer_ip, peer_port, file_name):
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect((peer_ip, peer_port))
    send_file(file_name, peer_socket)
    peer_socket.close()

# Function to receive file from peer

def receive_file_from_peer(peer_ip, peer_port, file_name):
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect((peer_ip, peer_port))
    receive_file(file_name, peer_socket)
    peer_socket.close()

# Function to register with ALTO server

def register_with_server():
    # Create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    # Create HTTP request
    data = {'ip': my_ip, 'port': my_port}
    request = write_http_request('POST', '/register', json.dumps(data))
    # Send HTTP request
    client_socket.send(request)
    # Receive HTTP response
    response = client_socket.recv(1024).decode()
    response = response.split('\r\n')
    response = response[-1]
    response = json.loads(response)
    # Close socket
    client_socket.close()
    # Return response
    return response

# Function to unregister with ALTO server

def unregister_with_server():
    # Create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    # Create HTTP request
    data = {'ip': my_ip}
    request = write_http_request('POST', '/unregister', json.dumps(data))
    # Send HTTP request
    client_socket.send(request)
    # Receive HTTP response
    response = client_socket.recv(1024).decode()
    response = response.split('\r\n')
    response = response[-1]
    response = json.loads(response)
    # Close socket
    client_socket.close()
    # Return response
    return response

# Function to get best peer from ALTO server

def get_best_peer_from_server():
    # Create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    # Create HTTP request
    data = {'ip': my_ip}
    request = write_http_request('POST', '/bestpeer', json.dumps(data))
    # Send HTTP request
    client_socket.send(request)
    # Receive HTTP response
    response = client_socket.recv(1024).decode()
    response = response.split('\r\n')
    response = response[-1]
    response = json.loads(response)
    # Close socket
    client_socket.close()
    # Return response
    # print(response)
    return response

# Function to start server: To send files to other peers

def start_server():
    global my_ip
    global my_port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((my_ip, my_port))
    server_socket.listen(5)
    while True:
        # print("Waiting for peer...")
        conn, addr = server_socket.accept()
        print("Peer connected: " + str(addr))
        data = conn.recv(1024).decode()
        data = data.split('\r\n')
        data = data[-1]
        data = json.loads(data)
        if data['type'] == "send_file":
            file_name = data['file_name']
            file_size = data['file_size']
            receive_file(file_name, file_size, conn)
        elif data['type'] == "get_file":
            file_name = data['file_name']
            send_file(file_name, conn)
        conn.close()
        print("Peer disconnected: " + str(addr))

# Function to handle a user

def handle_user():
    global my_ip
    global my_port
    global server_ip
    global server_port
    while True:
        print("1. Register with ALTO server")
        print("2. Unregister with ALTO server")
        print("3. Get best peer from ALTO server")
        print("4. Create file")
        print("5. Delete file")
        print("6. Exit")
        choice = int(input("Enter choice: "))
        if choice == 1:
            response = register_with_server()
            print(response['message'])
        elif choice == 2:
            response = unregister_with_server()
            print(response['message'])
        elif choice == 3:
            print("Enter file name: ")
            file_name = input()
            response = get_best_peer_from_server()
            if response['message'] == 'No peer found':
                print(response['message'])
            elif response['message'] == 'Best peer found':
                pass
                peer_ip = response['ip']
                peer_port = response['port']
                receive_file_from_peer(peer_ip, peer_port, file_name)
            else:
                print(response['message'])
        elif choice == 4:
            print("Enter file name: ")
            file_name = input()
            print("Enter file contents: ")
            file_contents = input()
            files[file_name] = file_contents
        elif choice == 5:
            print("Enter file name: ")
            file_name = input()
            if file_name in files:
                del files[file_name]
            else:
                print("File not found")
        else:
            print("Invalid choice")

# Main function

def main():
    global data
    global my_ip
    global my_port
    global server_ip
    global server_port
    # Read server IP and port from "../config/server.json"
    server_config_file = open("../config/server.json", 'r')
    server_config = json.load(server_config_file)
    server_config_file.close()
    server_ip = server_config['ip']
    server_port = server_config['port']
    # Read my IP from hostname
    my_ip = socket.gethostbyname(socket.gethostname())
    # Read my port from argv
    my_port = int(sys.argv[1])
    # Read file data from "../config/data.json"
    # data_file = open("../config/data.json", 'r')
    # data = json.load(data_file)
    # data_file.close()
    # Start user thread
    user_thread = threading.Thread(target=handle_user)
    user_thread.start()
    # Start server thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

# Call main function

if __name__ == "__main__":
    main()

