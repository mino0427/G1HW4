# server.py

import socket
import threading
from queue import Queue

MAX_CLIENTS = 4
lock = threading.Lock()
request_queue = Queue()
response_queue = Queue()

clients = []  # 연결된 클라이언트: (소켓, 주소, 클라이언트 ID)
threads = []

def handle_client(client_socket, client_address, client_id):
    global clients
    print(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})")
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break  # 클라이언트가 연결을 끊음

            # 수신된 메시지 처리
            if data.startswith(b"REQUEST_CHUNK"):
                # 대상 클라이언트에게 요청 전달
                with lock:
                    request_queue.put((client_id, data))
            elif data.startswith(b"CHUNK_DATA"):
                # 요청자에게 청크 데이터 전달
                with lock:
                    response_queue.put((client_id, data))
            else:
                print(f"[서버] {client_id}로부터 알 수 없는 메시지 수신")

        print(f"[연결 종료] 클라이언트 {client_id} 연결 종료")
    except ConnectionResetError:
        print(f"[연결 종료] 클라이언트 {client_id} 연결이 리셋됨")
    finally:
        client_socket.close()
        with lock:
            clients = [c for c in clients if c[0] != client_socket]
        print(f"[제거됨] 클라이언트 {client_id} 제거됨")

def message_dispatcher():
    while True:
        # 요청 메시지 전달
        if not request_queue.empty():
            sender_id, request_msg = request_queue.get()
            _, target_client_id, _ = request_msg.decode().strip().split(":")
            with lock:
                for client_sock, _, cid in clients:
                    if cid == target_client_id:
                        client_sock.send(request_msg)
                        print(f"[서버] {sender_id}의 요청을 {target_client_id}에게 전달")
                        break

        # 응답 메시지 전달
        if not response_queue.empty():
            sender_id, response_msg = response_queue.get()
            # 메시지에서 요청자 클라이언트 ID 추출
            header_end_index = response_msg.index(b"\n")
            header = response_msg[:header_end_index].decode()
            header_parts = header.split(":")
            if len(header_parts) == 4:
                _, sender_client_id, chunk_index, requester_id = header_parts
                with lock:
                    for client_sock, _, cid in clients:
                        if cid == requester_id:
                            client_sock.send(response_msg)
                            print(f"[서버] {sender_id}의 청크를 {requester_id}에게 전달")
                            break
            else:
                print(f"[서버] 헤더 형식 오류: {header}")


def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...")

    client_ids = ['A', 'B', 'C', 'D']

    # 메시지 디스패처 스레드 시작
    dispatcher_thread = threading.Thread(target=message_dispatcher, daemon=True)
    dispatcher_thread.start()

    try:
        while len(clients) < MAX_CLIENTS:
            client_socket, client_address = server.accept()
            client_id = client_ids[len(clients)]
            clients.append((client_socket, client_address, client_id))
            print(f"[클라이언트 연결] {client_address} (ID: {client_id})")

            # 클라이언트에게 FLAG 전송
            client_socket.send(f"FLAG:{client_id}\n".encode())
            print(f"[서버] 클라이언트 {client_id}에게 FLAG 전송 완료")

            # 클라이언트 핸들러 스레드 시작
            thread = threading.Thread(target=handle_client, args=(client_socket, client_address, client_id))
            thread.start()
            threads.append(thread)

        # 모든 스레드가 종료될 때까지 대기
        for thread in threads:
            thread.join()

    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        for client_socket, _, _ in clients:
            client_socket.close()
        server.close()

if __name__ == "__main__":
    start_server()
