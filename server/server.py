# echo-server.py

import socket
import json
import struct
import multiprocessing


HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
TCP_PORT = 8080  # The port used by the TCP server

UDP_PORT = 64700  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)
UDP_PORT1 = 64701  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)
UDP_PORT2 = 64702  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)
UDP_PORT3 = 64703  # The port used by the UDP server  # Port to listen on (non-privileged ports are > 1023)

ACK_UDP_PORT = 63700  # The port used by the UDP server for sending ack
ACK_UDP_PORT1 = 63701  # The port used by the UDP server for sending ack
ACK_UDP_PORT2 = 63702  # The port used by the UDP server for sending ack
ACK_UDP_PORT3 = 63703  # The port used by the UDP server for sending ack

BUFFER = 1600 #ack_message,packetPos, lastPos, shared_packets, ack_sockets[i], ack_udp_ports[i]
def recievePackets(ack_message,packetPos,lastPos,server_socket,packets,ack_socket,ack_port):
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
            
        print(f"packets received {len(packets)}")
if __name__ == '__main__':   
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to a host and port
    server_socket.bind((HOST, TCP_PORT))

    # Listen for incoming connections
    server_socket.listen()

    # Accept a client connection
    client_socket, address = server_socket.accept()

    # Receive the JSON data
    received_data = client_socket.recv(1024).decode()

    # Convert JSON to dictionary
    received_json = json.loads(received_data)

    # Close the sockets
    client_socket.close()
    server_socket.close()

    # Create a socket
    server_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(4)]
    ack_sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(4)]

    udp_ports = [UDP_PORT, UDP_PORT1, UDP_PORT2, UDP_PORT3]
    ack_udp_ports = [ACK_UDP_PORT, ACK_UDP_PORT1, ACK_UDP_PORT2, ACK_UDP_PORT3]

    for i in range(4):
        server_sockets[i].bind((HOST, udp_ports[i]))
        server_sockets[i].setblocking(True)
  
    # Create a multiprocessing manager
    manager = multiprocessing.Manager()

    # Create a shared list
    shared_packets = manager.list()
    
    ack_message = "ACK"
    total_packets = received_json["total_packets"]
    print(total_packets)
    processes = []
    lastPos = total_packets // 4
    # Receive data from clients using multiprocessing
    for i in range(4):
        packetPos = i * lastPos + 1
        if i == 3:
            lastPos = total_packets
        else:
            lastPos = (i + 1) * lastPos
        receiver_process = multiprocessing.Process(target=recievePackets, args=(ack_message,packetPos, lastPos,server_sockets[i], shared_packets, ack_sockets[i], ack_udp_ports[i]))
        processes.append(receiver_process)
        receiver_process.start()

    for process in processes:
        process.join()
               
    reconstructed_data = b''.join([shared_packets[i]["data"] for i in range(total_packets)])

    with open(received_json["filename"], 'wb') as file:
        file.write(reconstructed_data)
    for server_socket in server_sockets:
        server_socket.close()
    for ack_socket in ack_sockets:
        ack_socket.close()