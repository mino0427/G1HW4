import socket
import threading
import time
from queue import Queue

MAX_CLIENTS = 4
lock = threading.Lock()
request_queue = Queue()
response_queue = Queue()
system_clock = 0  # 전역 System Clock (msec 단위)

client_speeds = {
    'A': {'chunk_send': 0.006, 'msg_send': 0.0006},
    'B': {'chunk_send': 0.007, 'msg_send': 0.0007},
    'C': {'chunk_send': 0.008, 'msg_send': 0.0008},
    'D': {'chunk_send': 0.009, 'msg_send': 0.0009}
}

class SystemClock(threading.Thread):
    def run(self):
        global system_clock
        while True:
            time.sleep(0.001)  # 1 msec 단위로 증가
            system_clock += 1



# 서버 실행 함수
def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(MAX_CLIENTS)
    print(f"[서버 시작] {host}:{port}에서 대기 중...")

    # 시스템 클럭 시작
    clock_thread = SystemClock()
    clock_thread.daemon = True
    clock_thread.start()

    client_ids = ['A', 'B', 'C', 'D']
    clients = []


    try:
        while len(clients) < MAX_CLIENTS:
            client_socket, addr = server.accept()
            client_id = client_ids[len(clients)]
            clients.append(client_socket)
            print(f"[연결됨] 클라이언트 {addr} 연결 완료 (ID: {client_id})")

            
        for client in clients:
            # 접속 순서에 따라 FLAG 전송
            client.send(f"FLAG:{client_id}\n".encode())
            client_id += 1  # 다음 클라이언트에 대한 ID 증가


    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        for client in clients:
            client.close()
        server.close()

if __name__ == "__main__":
    start_server()
