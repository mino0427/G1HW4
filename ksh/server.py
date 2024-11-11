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
threads = []

def handle_client(client_socket, client_address, client_id):
    global clients
    print(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})")
    try:
        while True:
            if not request_queue.empty():
                request_msg = request_queue.get()
                _, target_client_id, chunk_id = request_msg.split(":")
                chunk_id = int(chunk_id)

                for client_sock, client_address, cid in clients:
                    if cid == target_client_id:
                        print(f"[서버] 클라이언트 {target_client_id}에게 요청 메시지 전달: {request_msg}")
                        client_sock.send(request_msg.encode())
                        time.sleep(0.01)  # 하프 듀플렉스 전송 대기
                        break
            if not response_queue.empty():
                response_msg = response_queue.get()
                header, chunk_data = response_msg.split(b":", 3)[:3], response_msg.split(b":", 3)[-1]
                _, sender_client_id, chunk_id = header.split(":")
                chunk_id = int(chunk_id)

                print(f"[서버] 클라이언트 {client_id}에게 청크 전송: CHUNK_ID {chunk_id}")
                client_socket.send(f"SEND_CHUNK:{sender_client_id}:{chunk_id}:".encode() + chunk_data)

            # 클라이언트로부터 데이터 수신
            data = client_socket.recv(4096)
            try:
                decoded_data = data.decode(errors='ignore').strip()
                if decoded_data.startswith("REQUEST_CHUNK"):
                    print(f"[서버] 요청 수신: {decoded_data}")
                    request_queue.put(decoded_data)
                    print(f"[디버깅] 요청 큐에 데이터 삽입 완료: {decoded_data}")  # 큐 삽입 후 확인
                elif decoded_data.startswith("CHUNK_DATA"):
                    # 헤더 끝 부분을 찾아서 분리
                    header_end_index = data.index(b":", data.index(b":") + 1) + 1  # 마지막 콜론 뒤 인덱스 찾기
                    header = data[:header_end_index].decode(errors='ignore')
                    chunk_data = data[header_end_index:]  # 헤더 다음의 이진 데이터 부분

                    # response_queue에 넣을 때 형식을 맞춰서 넣음
                    response_queue.put(header.encode() + chunk_data + b"\n")
                    print(f"[서버] 응답 수신: {header}")
            except UnicodeDecodeError:
                print("데이터 수신 실패")

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
            
        for client_socket, _, client_id in clients:
            # 접속 순서에 따라 FLAG 전송
            client_socket.send(f"FLAG:{client_id}\n".encode())
            print(f"[서버] 클라이언트 {client_id}에게 FLAG 전송 완료")

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
