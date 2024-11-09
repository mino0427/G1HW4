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

# 클라이언트 핸들러 스레드 함수
def handle_client(client_socket, client_id, clients):
    global request_queue, response_queue
    try:
        while True:
            # 요청 큐가 비어 있는지 확인
            if not request_queue.empty():
                with lock:
                    req_msg = request_queue.get()
                    _, target_client_id, chunk_id = req_msg.split(":")
                    chunk_id = int(chunk_id)

                    if target_client_id in clients:
                        print(f"[청크 요청 전송] 클라이언트 {target_client_id}에게 청크 ID {chunk_id} 요청")
                        clients[target_client_id].send(f"REQUEST_CHUNK:{chunk_id}\n".encode())
            
            # 응답 큐가 비어 있는지 확인
            if not response_queue.empty():
                with lock:
                    resp_msg = response_queue.get()
                    _, client_id, chunk_id, chunk_data = resp_msg.split(":")
                    chunk_id = int(chunk_id)

                    for receiver_id, receiver_socket in clients.items():
                        if receiver_id != client_id:
                            receiver_socket.send(f"SEND_CHUNK:{client_id}:{chunk_id}:{chunk_data}\n".encode())
                            print(f"[청크 데이터 전송] 클라이언트 {receiver_id}에게 청크 ID {chunk_id} 전송 완료")
            
            # 클라이언트로부터 메시지 수신 대기
            message = client_socket.recv(4096).decode().strip()
            if not message:
                break

            if message.startswith("REQUEST_CHUNK"):
                # 요청 메시지를 request_queue에 저장
                with lock:
                    request_queue.put(message)
                    print(f"[요청 큐 저장] 클라이언트 {client_id}의 요청: {message}")
            elif message.startswith("CHUNK_DATA"):
                # 청크 데이터를 response_queue에 저장
                with lock:
                    response_queue.put(message)
                    print(f"[응답 큐 저장] 클라이언트 {client_id}의 청크 데이터: {message}")

    except ConnectionResetError:
        print(f"[연결 종료] 클라이언트 {client_id}와의 연결이 종료되었습니다.")
    finally:
        client_socket.close()

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
    clients = {}
    client_threads = []

    try:
        for i in range(MAX_CLIENTS):
            client_socket, addr = server.accept()
            client_id = client_ids[i]
            clients[client_id] = client_socket
            print(f"[연결됨] 클라이언트 {addr} 연결 완료 (ID: {client_id})")

            # 클라이언트 핸들러 스레드 시작
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_id, clients))
            client_thread.daemon = True
            client_thread.start()
            client_threads.append(client_thread)

        for client_id, client in zip(client_ids, clients):
            client[0].send(f"FLAG:{client_id}\n".encode())


        # 메인 스레드는 종료되지 않도록 대기
        for thread in client_threads:
            thread.join()

    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        for client in clients.values():
            client.close()
        server.close()

if __name__ == "__main__":
    start_server()
