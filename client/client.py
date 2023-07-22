# echo-client.py

import socket
import os
import json
import struct
import multiprocessing
from multiprocessing import Pool
import time
from collections import deque
import threading
import concurrent.futures


HOST = "127.0.0.1"  # The server's hostname or IP address
TCP_PORT = 8080  # The port used by the TCP server

UDP_PORT = 64700  # The port used by the UDP server\
ACK_UDP_PORT = 63700  # The port used by the UDP server for sending ack
CORES =     multiprocessing.cpu_count()*2
BUFFER = 2500   # Buffer size of file segments

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
    lastPacketPos, last_packet_size,file_path, server_socket, ack_socket, udp_port, segmentFirst, segmentLast = args
    file_lock = multiprocessing.Lock()
    
    print(f"Process ID: {os.getpid()}")  # Print the process ID    
    index=0
    avgTime = 0.5
    timeS = 0
    segmentIndex=segmentFirst
    median = deque(maxlen=10000)
    while segmentIndex <= segmentLast:   
        epoch = time.time_ns() // 1000000
        with open(file_path, "r+b") as f:
            with file_lock:
                # Calculate the position to seek to based on the segment size and index
                index = 1500 * segmentIndex
                # Move the file pointer to the desired position
                f.seek(index)
                # Write data to the allocated segment
                if(segmentIndex == lastPacketPos):
                    segment_data=f.read(last_packet_size)
                else:
                    segment_data=f.read(1500)
                
        segment_header = struct.pack("!IQ", segmentIndex,epoch)
        segment_packet = segment_header + segment_data
        server_socket.sendto(segment_packet, (HOST, udp_port))
        ack_socket.settimeout(avgTime)
        try:
            rtt, address = ack_socket.recvfrom(128)
            timeS = struct.unpack('!Q', rtt)[0]
            response = True
        except socket.timeout:
            response=False
        median.append(timeS)
        avgTime = (sum(median) / len(median))*1.20
        if avgTime < 0.000001:
            avgTime = 0.000001   
        if response:
            segmentIndex=segmentIndex+1
            index=index+1
            with sharedProgress.get_lock():        
                sharedProgress.value = sharedProgress.value + 1
        if segmentIndex==segmentLast:
            print(f"Process ID: {os.getpid()} has ended sending packets")  # Print the process ID    

def printProgress(totalPackets,sharedProgress):
    bar_length = 100  # Length of the progress bar
    while sharedProgress.value < totalPackets:
        totalProgress = round((sharedProgress.value / totalPackets) * 100,1)
        filled_length = int(bar_length * totalProgress / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'Progress: [{bar}] {totalProgress}%')

def divide_list(lst):
    num_cores = CORES
    n = len(lst)
    k = n // num_cores  # Calculate the size of each sublist
    remainder = n % num_cores  # Calculate the remaining items

    divided_lists = []
    start = 0
    for i in range(num_cores):
        sublist_size = k
        if i == num_cores - 1:
            sublist_size += remainder  # Add remaining items to the last sublist
        sublist = lst[start:start+sublist_size]
        divided_lists.append(sublist)
        start += sublist_size

    return divided_lists
def init_shared_progress(progress):
    global sharedProgress
    sharedProgress = progress
if __name__ == '__main__':
    sharedProgress = multiprocessing.Value('i', 0)
    num_cores = CORES

    file_path = "uploads/Apex.Point.Build.11534915.zip"
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

    
    server_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(num_cores)]
    ack_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(num_cores)]

   
    port_step = 1
    ack_udp_port_start = ACK_UDP_PORT
    # Generate the ack_udp_ports list
    ack_udp_ports = [ack_udp_port_start + i * port_step for i in range(num_cores)]
    for i in range(num_cores):
        ack_sockets[i].bind((HOST, ack_udp_port_start+i))
        ack_sockets[i].setblocking(True)
    # segments=segment_file(file_path)
    # Receive data from clients
    #segmentsArr = divide_list(segments)
    totalPackets = metadata["total_packets"]
    lastPacketSize=metadata["last_packet"]
    # Calculate the number of packets per core
    packets_per_core = totalPackets // num_cores

    # Calculate the remaining packets
    remaining_packets = totalPackets % num_cores

    # Create division values based on the number of cores
    division_values = []
    packetPos = 0
    for i in range(num_cores):
        if i == num_cores - 1:
            lastPos = packetPos + packets_per_core + remaining_packets
        else:
            lastPos = packetPos + packets_per_core
        division_values.append([packetPos, lastPos - 1])
        packetPos = lastPos
    pool = multiprocessing.Pool(processes=num_cores, initializer=init_shared_progress, initargs=(sharedProgress,))
    # Create a list of arguments for the sendSegments function
    args_list = []
    
    for i in range(num_cores):
        args = (totalPackets,lastPacketSize,file_path, server_sockets[i], ack_sockets[i], UDP_PORT+i, division_values[i][0], division_values[i][1])
        args_list.append(args)
    
    # Use the pool to map the sendSegments function to the arguments
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit the pool.map() function to the executor in a separate thread
        future = executor.submit(pool.map, sendSegments, args_list)

        # Start the progress tracking thread
        thread = threading.Thread(target=printProgress, args=(totalPackets, sharedProgress))
        thread.start()

        # Wait for the pool.map() function to complete
        future.result()

        # Join the thread
        thread.join()
    pool.close()
    pool.join()
    
    for server_socket in server_sockets:
        server_socket.close()
    for ack_socket in ack_sockets:
        ack_socket.close()