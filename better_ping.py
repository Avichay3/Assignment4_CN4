import os
import sys
import socket
import struct
import select
import time
import threading

# Constants
WATCHDOG_PORT = 3000
WATCHDOG_IP = 'localhost'
ICMP_ECHO_REQUEST = 8


def generate_checksum(source_string):
    """
    Calculates the ICMP packet checksum
    """
    sum = 0
    countTo = (len(source_string) // 2) * 2
    count = 0
    while count < countTo:
        thisVal = source_string[count + 1] * 256 + source_string[count]
        sum += thisVal
        sum &= 0xffffffff
        count += 2

    if countTo < len(source_string):
        sum += source_string[len(source_string) - 1]
        sum &= 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    sum += (sum >> 16)

    answer = ~sum
    answer &= 0xffff

    answer = answer >> 8 | (answer << 8 & 0xff00)

    return answer


def receive_ping(my_socket, ID, timeout):
    """
    Receives ICMP ping reply packet
    """
    timeLeft = timeout

    while True:
        start_select = time.time()
        ready = select.select([my_socket], [], [], timeLeft)
        select_time = (time.time() - start_select)

        if ready[0] == []:
            return None

        timeReceived = time.time()
        recPacket, addr = my_socket.recvfrom(1024)

        icmpHeader = recPacket[20:28]
        type_, code_, checksum_, packetID_, sequence_ = struct.unpack("bbHHh", icmpHeader)

        if packetID_ == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            ttl = ord(struct.unpack("c", recPacket[8:9])[0])
            return timeReceived - timeSent, ttl

        timeLeft -= select_time

        if timeLeft <= 0:
            return None


def send_ping(my_socket, dest_addr, ID):
    """
    Sends ICMP ping request packet
    """
    dest_addr = socket.gethostbyname(dest_addr)

    my_checksum = 0

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    data = struct.pack("d", time.time())
    my_checksum = generate_checksum(header + data)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1)
    packet = header + data

    my_socket.sendto(packet, (dest_addr, 1))


def ping(dest_addr, timeout):
    """
    Performs the ping operation
    """
    icmp = socket.getprotobyname("icmp")

    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    except socket.error as e:
        if e.errno == 1:
            msg = "Operation not permitted"
            raise socket.error(msg)

        raise

    my_ID = os.getpid() & 0xFFFF

    send_ping(my_socket, dest_addr, my_ID)
    result = receive_ping(my_socket, my_ID, timeout)

    my_socket.close()

    if result is None:
        return None, None

    delay, ttl = result

    return delay, ttl


def reset_watchdog():
    """
    Sends a reset message to the watchdog
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((WATCHDOG_IP, WATCHDOG_PORT))
    s.send(bytes('reset', 'utf-8'))


def betterping_flow(dest_addr, timeout, watchdog_thread):
    """
    The main flow of the betterping program
    """
    seq = 1

    while watchdog_thread.is_alive():
        delay, ttl = ping(dest_addr, timeout)
        if delay is None:
            print(f"Request timed out")
        else:
            delay *= 1000
            print(f"Reply from {dest_addr}: bytes=32 seq={seq} TTL={ttl} time={delay:.3f}ms")

        reset_watchdog()

        seq += 1
        time.sleep(1)


def create_watchdog_tcp_socket():
    """
    Creates a TCP socket and connects to the watchdog
    """
    watchdog_thread = threading.Thread(target=lambda: os.system('py watchdog.py'))
    watchdog_thread.start()

    # Waits for watchdog's TCP to initialize
    time.sleep(1)

    return watchdog_thread


def betterping_starter():
    """
    Starts the betterping program
    """
    if len(sys.argv) != 2:
        print('Usage: python3 better_ping.py <ip>')
        sys.exit(1)

    dest_addr = sys.argv[1]
    timeout = 1

    # Creates watchdog thread
    watchdog_thread = create_watchdog_tcp_socket()

    # Starts the betterping flow
    betterping_flow(dest_addr, timeout, watchdog_thread)


if __name__ == '__main__':
    betterping_starter()
