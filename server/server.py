# echo-server.py

import socket
import json
import struct
import multiprocessing
import os
from multiprocessing import Pool
import time

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
TCP_PORT = 8080  # The port used by the TCP server
UDP_PORT = 64700  # The starting port used by the UDP server
CORES = multiprocessing.cpu_count()

ACK_UDP_PORT = 63700  # The starting port used by the UDP server for sending ack
BUFFER = 1600

def recievePackets(args):
    ack_message, packetPos, lastPos, server_socket, packets, ack_socket, ack_port = args
    print(f"Process ID: {os.getpid()}")  # Print the process ID    
    while packetPos < lastPos:
        
        data, address = server_socket.recvfrom(BUFFER)
        
        segment_header = data[:6]  # Extract the fixed-size header (6 bytes)
        position, segment_size = struct.unpack("!IH", segment_header)
        segment_data = data[6:]  # Extract the segment data
        
        packet = {
            "pos":position, 
            "data":segment_data
        }
        
        if int(position) == packetPos:
            packets.append(packet)
            ack_socket.sendto(ack_message.encode(), (HOST, ack_port))
            packetPos=packetPos+1
        if packetPos == lastPos:
            packets.append(packet)
            print(f"pos {lastPos} achieved on process {os.getpid()}")
    
            
            # print(f"packets received {len(packets)}")
if __name__ == '__main__': 
    # Create a socket
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to a host and port
    tcp_server_socket.bind((HOST, TCP_PORT))

    # Listen for incoming connections
    tcp_server_socket.listen()

    # Accept a client connection
    client_socket, address = tcp_server_socket.accept()

    # Receive the JSON data
    received_data = client_socket.recv(1024).decode()

    # Convert JSON to dictionary
    received_json = json.loads(received_data)

    # Close the sockets
    client_socket.close()
    tcp_server_socket.close()

    # Create a multiprocessing manager
    manager = multiprocessing.Manager()

    # Create a shared list
    shared_packets = manager.list()

    ack_message = "ACK"
    total_packets = received_json["total_packets"]
    print(total_packets)
    
    # Get the number of CPU cores
    num_cores = CORES#multiprocessing.cpu_count()

    # Calculate the number of processes and sockets based on the number of CPU cores
    num_processes = num_cores
    num_sockets = num_cores
    
    # Create server_sockets and ack_sockets lists dynamically
    server_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(num_sockets)]
    ack_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(num_sockets)]

    # Bind server_sockets and setblocking
    for i in range(num_sockets):
        udp_port = UDP_PORT + i
        server_sockets[i].bind((HOST, udp_port))
        server_sockets[i].setblocking(True)
        

    # Divide the work among the processes
    packetPosL = []
    lastPosL = []
    
   # Calculate the number of packets per core
    packets_per_core = total_packets // num_cores

    # Calculate the remaining packets
    remaining_packets = total_packets % num_cores

    # Create division values based on the number of cores
    division_values = []
    packetPos = 0
    for i in range(num_cores):
        lastPos = packetPos + packets_per_core - 1
        if i < remaining_packets:
            lastPos += 1
        division_values.append([packetPos, lastPos])
        packetPos = lastPos + 1
    # Create a pool of processes
    pool = Pool(processes=num_processes)

    # Create a list of arguments for the recievePackets function
    args_list = []
    for i in range(num_processes):
        args = ("ACK", division_values[i][0], division_values[i][1], server_sockets[i], shared_packets, ack_sockets[i], ACK_UDP_PORT + i)
        args_list.append(args)

    # Use the pool to map the lambda function to the arguments
    pool.map(recievePackets, args_list)
    # Retrieve the results from the iterator
    # results = [result for result in results_iter]

    # Close the pool
    
    pool.close()
    pool.join()
    
    # Close the server_sockets and ack_sockets
    for server_socket in server_sockets:
        server_socket.close()
    for ack_socket in ack_sockets:
        ack_socket.close()
    print(len(shared_packets))               
    reconstructed_data = b''.join([shared_packets[i]["data"] for i in range(total_packets)])

    with open("uploads/"+received_json["filename"], 'wb') as file:
        file.write(reconstructed_data)