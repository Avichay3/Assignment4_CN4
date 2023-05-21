import socket
from time import sleep

# constant
PORT = 3000


def create_watchdog_tcp_socket() -> None:
    """
    Creates a watchdog TCP socket and opens the watchdog timer.
    """
    try:
        # Create the watchdog TCP socket and make the port reusable
        watchdog = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        watchdog.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        watchdog.bind(('', PORT))
        # This line starts listening for incoming connections on the watchdog socket.
        # The argument 1 specifies the maximum number of queued connections that can be pending
        # before they are accepted by the server.
        watchdog.listen(1)
        print("-----WATCHDOG IS UP-------")

        while True:
            better_ping_socket, address = watchdog.accept()
            print(f"-----PING Program connected------")
            status = watchdog_timer(better_ping_socket)
            if status == -1:
                watchdog.close()
                better_ping_socket.close()
                # Indicates termination due to watchdog timeout
                exit(2)

    except socket.error:
        print(f"Socket Error {socket.error}")
        exit(1)


def watchdog_timer(better_ping_socket):
    """
    Opens a timer for 10 seconds and resets it if a life signal is received.
    :param better_ping_socket: The socket to receive life signals from
    :return: -1 if no life signal is received for 10 seconds
    """
    better_ping_socket.setblocking(False)
    timer = 0
    while timer < 10:
        sleep(1)
        timer += 1
        if timer == 10:
            break
        try:
            # Check if a life signal is received from better ping
            message_received = better_ping_socket.recv(5)
            if len(message_received) > 0:
                timer = 0

        except BlockingIOError:
            pass
    return -1
