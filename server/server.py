# echo-server.py

import socket
import json
import struct
import threading

lock = threading.Lock()

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

BUFFER = 1600
def recievePackets(packetPos,lastPos,server_socket,packets,ack_socket,ack_port):
    with lock:
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
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to a host and port
server_socket.bind((HOST, UDP_PORT))
server_socket1.bind((HOST, UDP_PORT1))
server_socket2.bind((HOST, UDP_PORT2))
server_socket3.bind((HOST, UDP_PORT3))

# Create a socket for sending ACK
ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("UDP server listening on {}:{}".format(HOST, UDP_PORT))
  
# Receive data from clients
ack_message = "ACK"
packets = []
packetPos = 0
lastPos = received_json["total_packets"]//4
receiver_thread = threading.Thread(target=recievePackets, args=(packetPos, lastPos, server_socket, packets , ack_socket, ACK_UDP_PORT))

packets1 = []
packetPos = lastPos + 1
lastPos = received_json["total_packets"] // 4 * 2
receiver_thread1 = threading.Thread(target=recievePackets, args=(packetPos, lastPos, server_socket, packets , ack_socket1, ACK_UDP_PORT1))

packets2 = []
packetPos = lastPos + 1
lastPos = received_json["total_packets"] // 4 * 3
receiver_thread2 = threading.Thread(target=recievePackets, args=(packetPos, lastPos, server_socket, packets , ack_socket2, ACK_UDP_PORT2))

packets3 = []
packetPos = lastPos + 1
lastPos = received_json["total_packets"] // 4 * 4 + received_json["total_packets"] % 4
receiver_thread3 = threading.Thread(target=recievePackets, args=(packetPos, lastPos, server_socket, packets , ack_socket3, ACK_UDP_PORT3))

# Start the sender thread

receiver_thread.start()
receiver_thread1.start()
receiver_thread2.start()
receiver_thread3.start()

# Wait for the sender thread to complete (optional)
receiver_thread.join()
receiver_thread1.join()
receiver_thread2.join()
receiver_thread3.join()
    
packets.append(packets1)
packets.append(packets2)
packets.append(packets3)

reconstructed_data = b''.join([packets[i]["data"] for i in range(received_json["total_packets"])])
with open(received_json["filename"], 'wb') as file:
    file.write(reconstructed_data)

# Access the received JSON data
server_socket.close()