import errno
import socket
import struct
import sys
import time
import threading

from ping import ICMP_ECHO_REPLY
from watchdog import create_watchdog_tcp_socket

# Constants
WATCHDOG_PORT = 3000
WATCHDOG_IP = 'localhost'

# Global variables
host = 0
seq = 0


def generate_checksum(packet) -> int:
    """
    Calculates the checksum of the packet.
    """
    checksum = 0
    count_to = (len(packet) // 2) * 2
    for i in range(0, count_to, 2):
        checksum += (packet[i] << 8) + packet[i + 1]
    if count_to < len(packet):
        checksum += packet[len(packet) - 1] << 8
    checksum = (checksum >> 16) + (checksum & 0xFFFF)
    checksum += checksum >> 16
    return (~checksum) & 0xFFFF


def create_packet():
    """
    Creates an ICMP packet to send.
    """
    global seq
    seq += 1
    header = bytearray(struct.pack('!BBHHH', 8, 0, 0, 0, seq))
    data = bytearray(b'Hello world')
    checksum = generate_checksum(header + data)
    header[2:4] = divmod(checksum, 256)
    packet = header + data
    return data, packet


def send_ping(raw_socket, packet):
    """
    Sends the ICMP packet to the specified host.
    """
    try:
        addr = (host, 1)
        raw_socket.sendto(packet, addr)
    except socket.error as e:
        print('Error: Failed to send packet')
        if raw_socket:
            raw_socket.close()
        sys.exit(1)


def recv_ping(betterping_socket):
    """
    Receives and parses the ICMP packet reply from the host.
    :param betterping_socket: socket to receive from
    :return: string of statistics or 0 (if fails)
    """
    start_time = time.time()
    betterping_socket.settimeout(0.1)  # Set a timeout for socket receive

    try:
        while True:
            packet, address = betterping_socket.recvfrom(1024)
            icmp_header = packet[20:28]
            respond_type, code, checksum, p_id, seq_number = struct.unpack("bbHHh", icmp_header)

            if respond_type == ICMP_ECHO_REPLY:
                return f'{len(packet[28:])} bytes from {address[0]} icmp_seq={int(seq_number / 256)}' \
                       f' ttl={packet[8]} time={(time.time() - start_time) * 1000:.3f} ms'
    except socket.timeout:
        return 0


def betterping_flow(betterping_socket, watchdog_thread):
    """
    The main flow of the betterping program.
    """
    global host
    host = sys.argv[1]
    raw_socket = None

    try:
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except socket.error:
        print('Failed to create socket')
        exit(1)

    first_send = True
    status = True

    try:
        while watchdog_thread.is_alive():
            data, packet = create_packet()
            send_ping(raw_socket, packet)

            if first_send:
                print('Pinging', host, 'with', len(data), 'bytes of data:')
                first_send = False

            if status:
                betterping_socket.send("ping".encode())

            statistics = recv_ping(raw_socket)

            if statistics:
                print('Reply from', host, ':', statistics)
                status = True

            if not statistics:
                print('Request timed out.')
                time.sleep(1)
                status = False
                continue

            time.sleep(1)

        print('Ping request could not find host', host)
    except KeyboardInterrupt:
        print('\nPing stopped.')
    finally:
        betterping_socket.close()
        raw_socket.close()
        exit(1)


def create_tcp_socket(watchdog_thread):
    """
    Establishes a TCP connection with the watchdog and starts the ping flow.
    """
    ping_socket = None

    try:
        # Create a TCP socket
        ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set socket options
        ping_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ping_socket.settimeout(5.0)  # Set a timeout for the connection attempt

        # Connect to the watchdog
        watchdog_address = (WATCHDOG_IP, WATCHDOG_PORT)
        ping_socket.connect(watchdog_address)

        # Start the ping flow
        betterping_flow(ping_socket, watchdog_thread)
    except socket.error:
        print(f"Error: Failed to establish a TCP connection with the watchdog")
        if ping_socket is not None:
            ping_socket.close()
        exit(1)





def betterping_starter():
    """
    Starts the betterping program.
    """
    if len(sys.argv) != 2:
        print('Usage: python3 betterping.py <ip>')
        exit(1)

    # Create a watchdog thread
    watchdog_thread = threading.Thread(target=watchdog_ping)
    watchdog_thread.daemon = True
    watchdog_thread.start()

    # Wait for the watchdog to start
    time.sleep(1)

    # Establish a TCP connection with the watchdog and start the ping flow
    create_tcp_socket(watchdog_thread)


def watchdog_ping():
    """
    Performs the ping flow with the watchdog.
    """
    while True:
        # Perform the necessary operations with the watchdog
        # For example, send ping request and receive ping reply
        # Adjust the code according to your requirements

        time.sleep(1)  # Add appropriate delay between pings



if __name__ == '__main__':
    betterping_starter()
