import socket
import threading
from queue import Queue
import time

# 하프 듀플렉스 통신을 고려한 서버 구현
MAX_CLIENTS = 4
lock = threading.Lock()
request_queue = Queue()
response_queue = Queue()

clients = []  # 연결된 클라이언트 소켓과 주소를 저장

def handle_client(client_socket, client_address, client_id):
    print(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})")
    try:
        while True:
            with lock:
                if not request_queue.empty():
                    request_msg = request_queue.get()
                    _, target_client_id, chunk_id = request_msg.split(":")
                    chunk_id = int(chunk_id)

                    for client_sock, client_addr, cid in clients:
                        if cid == target_client_id:
                            print(f"[서버] 클라이언트 {target_client_id}에게 요청 메시지 전달: {request_msg}")
                            client_sock.send(request_msg.encode())
                            time.sleep(0.01)  # 하프 듀플렉스 전송 대기
                            break

                if not response_queue.empty():
                    response_msg = response_queue.get()
                    _, sender_client_id, chunk_id, chunk_data = response_msg.split(":", 3)
                    chunk_id = int(chunk_id)

                    print(f"[서버] 클라이언트 {client_id}에게 청크 전송: CHUNK_ID {chunk_id}")
                    client_socket.send(f"SEND_CHUNK:{sender_client_id}:{chunk_id}:{chunk_data}\n".encode())

            # 클라이언트로부터 데이터 수신
            data = client_socket.recv(4096).decode().strip()
            if data.startswith("REQUEST_CHUNK"):
                print(f"[서버] 요청 수신: {data}")
                request_queue.put(data)
            elif data.startswith("CHUNK_DATA"):
                print(f"[서버] 응답 수신: {data}")
                response_queue.put(data)
    except ConnectionResetError:
        print(f"[연결 종료] 클라이언트 {client_address} 연결 종료")
    finally:
        client_socket.close()
        clients = [(sock, addr, cid) for sock, addr, cid in clients if sock != client_socket]
        print(f"[연결 종료] 클라이언트 {client_id} 연결 제거 완료")

# 서버 실행 함수
def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...")

    client_ids = ['A', 'B', 'C', 'D']
    try:
        while len(clients) < MAX_CLIENTS:
            client_socket, client_address = server.accept()
            client_id = client_ids[len(clients)]
            clients.append((client_socket, client_address, client_id))
            print(f"클라이언트 연결 완료: {client_address} (ID: {client_id})\n")
            client_socket.send(f"FLAG:{client_id}\n".encode())
            threading.Thread(target=handle_client, args=(client_socket, client_address, client_id)).start()

    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        for client_socket, _, _ in clients:
            client_socket.close()
        server.close()

if __name__ == "__main__":
    start_server()
