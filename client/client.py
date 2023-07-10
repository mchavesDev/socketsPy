# echo-client.py

import socket
import os
import json
import struct
import multiprocessing
from multiprocessing import Pool
HOST = "127.0.0.1"  # The server's hostname or IP address
TCP_PORT = 8080  # The port used by the TCP server

UDP_PORT = 64700  # The port used by the UDP server\
UDP_PORT1 = 64701  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)
UDP_PORT2 = 64702  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)
UDP_PORT3 = 64703  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)

ACK_UDP_PORT = 63700  # The port used by the UDP server for sending ack
ACK_UDP_PORT1 = 63701  # The port used by the UDP server for sending ack
ACK_UDP_PORT2 = 63702  # The port used by the UDP server for sending ack
ACK_UDP_PORT3 = 63703  # The port used by the UDP server for sending ack

BUFFER = 1500   # Buffer size of file segments
progress = 0

def list_files_in_folder(folder_path):
    files = os.listdir(folder_path)
    for file in files:
        print(file)


# Function to segment the file we will send after to server.
def segment_file(file_path):
    segments = [] # List to store file segments
    with open(file_path, "rb") as file:
        counter = 0
        while True:
            chunk = file.read(BUFFER)
            if not chunk:
                break
            segments.append(chunk)
            counter += 1
    return segments

def get_file_metadata(file_path):
    file_stat = os.stat(file_path)
    filename = os.path.basename(file_path)
    size = file_stat.st_size
    file_size = os.path.getsize(file_path)
    total_packets = file_size // BUFFER
    if file_size % BUFFER != 0:
        total_packets += 1
    last_packet = file_stat.st_size%BUFFER
    created_at = file_stat.st_ctime
    modified_at = file_stat.st_mtime

    metadata = {
        "filename": filename,
        "size": size,
        "total_packets":total_packets,
        "last_packet":last_packet,
        "created_at": created_at,
        "modified_at": modified_at
    }

    return metadata
def sendSegments(args):
    segments, server_socket, ack_socket, udp_port, segmentFirst, segmentLast = args
    print(f"Process ID: {os.getpid()}")  # Print the process ID    
    
    segmentIndex=segmentFirst
    index=0
    while segmentIndex < segmentLast:   
            # Print the process ID    
        segment_data = segments[index]
        segment_header = struct.pack("!IH", segmentIndex, len(segment_data))
        segment_packet = segment_header + segment_data
        server_socket.sendto(segment_packet, (HOST, udp_port))
        try:
            response, address = ack_socket.recvfrom(128)
        except socket.timeout:
            response = ""
        if response == b"ACK":
                segmentIndex=segmentIndex+1
                index=index+1
                # progress = segmentIndex
        if segmentIndex==segmentLast:
            print(f"Process ID: {os.getpid()} has ended sending packets")  # Print the process ID    
                
def printProgress():
    global progress
    global totalPackets
    bar_length = 100  # Length of the progress bar
    while progress < totalPackets:
        totalProgress = round((progress / totalPackets) * 100,1)
        filled_length = int(bar_length * totalProgress / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'Progress: [{bar}] {totalProgress}%')
def divide_list(lst):
    n = len(lst)
    k = n // 4  # Calculate the size of each sublist, rounding up
    divided_lists = [lst[i:i+k] for i in range(0, n, k)]
    return divided_lists
if __name__ == '__main__':
    
    file_path = "uploads/100MB.bin"
    list_files_in_folder("uploads/")
    # Get file metadata
    metadata = get_file_metadata(file_path)
    # Convert metadata to JSON
    metadata_json = json.dumps(metadata)
    print(metadata_json)

    # Create a socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    client_socket.connect((HOST, TCP_PORT))

    # Send the JSON data
    client_socket.sendall(metadata_json.encode())

    # Close the socket
    client_socket.close()


    server_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(4)]
    ack_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(4)]

    udp_ports = [UDP_PORT, UDP_PORT1, UDP_PORT2, UDP_PORT3]
    ack_udp_ports = [ACK_UDP_PORT, ACK_UDP_PORT1, ACK_UDP_PORT2, ACK_UDP_PORT3]

    for i in range(4):
        ack_sockets[i].bind((HOST, ack_udp_ports[i]))
        ack_sockets[i].settimeout(1)
        ack_sockets[i].setblocking(True)
    segments=segment_file(file_path)
    # Receive data from clients
    segmentsArr = divide_list(segments)
    totalPackets = metadata["total_packets"]
    # Create a separate thread for sending segments

    division_values = []

    packetPos = 0
    lastPos = totalPackets // 4
    division_values.append([packetPos, lastPos])

    packetPos = lastPos + 1
    lastPos = totalPackets // 4 * 2
    division_values.append([packetPos, lastPos])

    packetPos = lastPos + 1
    lastPos = totalPackets // 4 * 3
    division_values.append([packetPos, lastPos])

    packetPos = lastPos + 1
    lastPos = totalPackets // 4 * 4 + totalPackets % 4
    division_values.append([packetPos, lastPos])

    pool = Pool(processes=4)

    # Create a list of arguments for the sendSegments function
    args_list = []
    for i in range(4):
        args = (segmentsArr[i], server_sockets[i], ack_sockets[i], udp_ports[i], division_values[i][0], division_values[i][1])
        args_list.append(args)

    # Use the pool to map the sendSegments function to the arguments
    pool.map(sendSegments, args_list)

    # Close the pool
    pool.close()
    pool.join()
    # Create the progress thread    
    # progress_thread = threading.Thread(target=printProgress, args=())

    # Start the progress thread
    # progress_thread.start()

    # Wait for the progress thread to complete (optional)
    # progress_thread.join()

    for server_socket in server_sockets:
        server_socket.close()
    for ack_socket in ack_sockets:
        ack_socket.close()