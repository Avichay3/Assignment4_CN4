import os
import sys
import struct
import socket
import select
import time

ICMP_ECHO_REQUEST = 8  # ICMP Echo Request type code


def calculate_checksum(packet):
    """Calculate checksum for the ICMP packet."""
    checksum = 0
    countTo = (len(packet) // 2) * 2

    for count in range(0, countTo, 2):
        checksum += (packet[count + 1] << 8) + packet[count]

    if countTo < len(packet):
        checksum += packet[len(packet) - 1]

    checksum = (checksum >> 16) + (checksum & 0xFFFF)
    checksum += (checksum >> 16)
    return ~checksum & 0xFFFF


def send_ping_request(dest_ip):
    """Send ICMP ECHO REQUEST packet to the destination IP."""
    icmp_packet = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, 0, 0, 1)
    checksum = calculate_checksum(icmp_packet)
    icmp_packet = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, checksum, 0, 1)
    packet_id = os.getpid() & 0xFFFF
    icmp_packet += struct.pack('!H', packet_id)
    packet_checksum = calculate_checksum(icmp_packet)
    icmp_packet = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, packet_checksum, 0, 1)
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    send_socket.sendto(icmp_packet, (dest_ip, 1))


def receive_ping_reply(send_time):
    """Receive ICMP ECHO REPLY packet and print details."""
    receive_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    receive_socket.settimeout(3)  # Set timeout to 3 seconds

    try:
        received_packet, addr = receive_socket.recvfrom(1024)
        receive_time = time.time()
        icmp_header = received_packet[20:28]
        _, _, _, packet_id, sequence = struct.unpack('!BBHHH', icmp_header)
        elapsed_time = (receive_time - time.time())* 1000
        if packet_id == os.getpid() & 0xFFFF:
            print(f"Reply from {addr[0]}: bytes={len(received_packet)} seq_num={sequence} time={elapsed_time:.2f}ms")
    except socket.timeout:
        print("Request timed out.")


def main():
    if len(sys.argv) != 2:
        print("Usage: python ping.py <ip>")
        sys.exit(1)
    dest_ip = sys.argv[1]
    print(f"Pinging {dest_ip} with ICMP ECHO REQUEST:")

    while True:
        send_time = time.time()
        send_ping_request(dest_ip)
        receive_ping_reply(send_time)
        time.sleep(1)  # Wait for 1 second before sending the next request


main()
