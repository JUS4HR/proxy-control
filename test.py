import socket
import threading
import time

TEST_HOST = "8.8.8.8"  # DNS Server
TEST_PORT = 53


def callback() -> None:
    print("interrupted")


def networkInterruptDetect() -> None:
    while runFlag:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.sendto(b"heartbeat", (TEST_HOST, TEST_PORT))
            while runFlag:
                time.sleep(1)
                s.sendto(b"heartbeat", (TEST_HOST, TEST_PORT))
                print("heartbeat sent", time.time())
            s.close()
        except (OSError, socket.timeout) as e:
            callback()
            print(e)


runFlag = True

t = threading.Thread(target=networkInterruptDetect)
t.daemon = True
t.start()

input("Press Enter to stop\n")
runFlag = False
t.join()