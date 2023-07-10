# echo-client.py

import socket
import os
import json
import struct
import threading

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
def sendSegments(segments,server_socket,ack_socket,udp_port):
    global progress
    segmentIndex=0
    while segmentIndex < len(segments):   
        segment_data = segments[segmentIndex]
        segment_header = struct.pack("!IH", segmentIndex, len(segment_data))
        segment_packet = segment_header + segment_data
        server_socket.sendto(segment_packet, (HOST, udp_port))
        try:
            response, address = ack_socket.recvfrom(128)
        except socket.timeout:
            response = ""
        if response == b"ACK":
                segmentIndex=segmentIndex+1
                progress = segmentIndex
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

file_path = "client/uploads/512MB.zip"
list_files_in_folder("client/uploads/")
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

# Create a UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ack_socket.bind((HOST, ACK_UDP_PORT))
ack_socket1.bind((HOST, ACK_UDP_PORT1))
ack_socket2.bind((HOST, ACK_UDP_PORT2))
ack_socket3.bind((HOST, ACK_UDP_PORT3))


segments=segment_file(file_path)
# Receive data from clients
ack_socket.settimeout(1)
ack_socket1.settimeout(1)
ack_socket2.settimeout(1)
ack_socket3.settimeout(1)
segmentsArr = divide_list(segments)
totalPackets = metadata["total_packets"]
# Create a separate thread for sending segments
sender_thread = threading.Thread(target=sendSegments, args=(segmentsArr[0], server_socket, ack_socket, UDP_PORT))
sender_thread1 = threading.Thread(target=sendSegments, args=(segmentsArr[1], server_socket1, ack_socket1, UDP_PORT1))
sender_thread2 = threading.Thread(target=sendSegments, args=(segmentsArr[2], server_socket2, ack_socket2, UDP_PORT2))
sender_thread3 = threading.Thread(target=sendSegments, args=(segmentsArr[3], server_socket3, ack_socket3, UDP_PORT3))

progress_thread = threading.Thread(target=printProgress, args=())

# Start the sender thread
progress_thread.start()
sender_thread.start()
sender_thread1.start()
sender_thread2.start()
sender_thread3.start()

# Wait for the sender thread to complete (optional)
sender_thread.join()
sender_thread1.join()
sender_thread2.join()
sender_thread3.join()
progress_thread.join()