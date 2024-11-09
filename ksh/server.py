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

# 클라이언트 정보 및 보유 파일 상태
client_files = {
    'A': [],  # 초기 상태에서 각 클라이언트의 파일 정보
    'B': [],
    'C': [],
    'D': []
}

class SystemClock(threading.Thread):
    def run(self):
        global system_clock
        while True:
            time.sleep(0.001)  # 1 msec 단위로 증가
            system_clock += 1

class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, client_id):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.client_id = client_id
        self.chunk_send_delay = client_speeds[client_id]['chunk_send']
        self.msg_send_delay = client_speeds[client_id]['msg_send']

    def run(self):
        try:
            while True:
                with lock:  # 하프 듀플렉스: 송수신이 교대로 이루어짐
                    request = self.client_socket.recv(4096).decode().strip()
                    if request.startswith("REQUEST_CHUNK"):
                        _, chunk_id = request.split(":")
                        chunk_id = int(chunk_id)
                        print(f"[서버 - {system_clock} msec] 클라이언트 {self.client_id}로부터 청크 {chunk_id} 요청 수신")

                        # 요청 큐에 요청 추가
                        request_queue.put((self.client_id, chunk_id))
                        print(f"[서버] 요청 큐에 {self.client_id}의 청크 {chunk_id} 저장")

                        # 요청된 청크를 다른 클라이언트에서 검색 및 처리
                        for client_key, file_chunks in client_files.items():
                            if client_key != self.client_id and chunk_id in file_chunks:
                                print(f"[서버 - {system_clock} msec] 클라이언트 {client_key}에게 청크 {chunk_id} 요청 전송")
                                time.sleep(client_speeds[client_key]['msg_send'])  # 요청 메시지 전송 시간 지연

                                # 해당 클라이언트로부터 청크 수신 및 응답 큐에 저장
                                time.sleep(client_speeds[client_key]['chunk_send'])  # 청크 전송 시간 지연
                                chunk_size = int(self.client_socket.recv(4096).decode().strip())
                                chunk_data = self.client_socket.recv(chunk_size)
                                response_queue.put((chunk_id, chunk_data))
                                print(f"[서버 - {system_clock} msec] 응답 큐에 청크 {chunk_id} 저장 완료")

                                # 클라이언트로 청크 전송
                                self.client_socket.send(f"SEND_CHUNK:{chunk_id}\n".encode())
                                self.client_socket.send(f"{chunk_size}\n".encode())
                                self.client_socket.send(chunk_data)  # 실제 클라이언트로부터 받은 데이터 전송
                                print(f"[서버 - {system_clock} msec] 클라이언트 {self.client_id}에게 청크 {chunk_id} 전송 완료")

                                # 클라이언트의 전송 완료 메시지 대기
                                time.sleep(self.msg_send_delay)  # 메시지 전송 시간 지연
                                response = self.client_socket.recv(4096).decode().strip()
                                if response == f"RECEIVED:{chunk_id}":
                                    print(f"[서버 - {system_clock} msec] 클라이언트 {self.client_id}로부터 청크 {chunk_id} 전송 완료 메시지 수신")
                                    client_files[self.client_id].append(chunk_id)
                                    break
        except Exception as e:
            print(f"[오류] 클라이언트 {self.client_address} 처리 중 오류 발생: {e}")
        finally:
            self.client_socket.close()
            print(f"[연결 종료] 클라이언트 {self.client_address} 연결 종료")

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

            handler = ClientHandler(client_socket, addr, client_id)
            handler.start()

    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        for client in clients:
            client.close()
        server.close()

if __name__ == "__main__":
    start_server()
