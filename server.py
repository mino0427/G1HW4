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
    buffer=b""
    print(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})\n")
    try:
        while True:
        
            # request_queue에 데이터가 4개 있으면 반복 실행
            if not request_queue.empty() and request_queue.qsize() == 4:
                for _ in range(4):
                    request_msg = request_queue.get()
                    _, req_client_id,target_client_id, chunk_id = request_msg.split(":")
                    chunk_id = int(chunk_id)

                    for client_sock, client_address, cid in clients:
                        if cid == target_client_id:
                            print(f"[서버] 클라이언트 {target_client_id}에게 요청 메시지 전달: {request_msg}")
                            #############여기서 send 할 때 <END> 안붙이고 보냄
                            client_sock.send((request_msg).encode())
                            time.sleep(0.01)  # 하프 듀플렉스 전송 대기
                            break

            # response_queue에 데이터가 4개 있으면 반복 실행
            if not response_queue.empty() and response_queue.qsize() == 4:
                for _ in range(4):
                    response_msg = response_queue.get()
                    header, chunk_data = response_msg.split(b":", 4)[:4], response_msg.split(b":", 4)[-1]
                    _, req_client_id ,sender_client_id, chunk_id = [part.decode() for part in header]  # b'' 제거
                    chunk_id = int(chunk_id)
                    
                    for client_sock, client_address, cid in clients:
                        if cid == req_client_id:
                            print(f"[서버] 클라이언트 {req_client_id}에게 청크 전송: CHUNK_ID {sender_client_id}:{chunk_id}\n")
                            client_sock.send(f"SEND_CHUNK:{sender_client_id}:{chunk_id}:<EoH>".encode() + chunk_data)
                            
                            
            # 클라이언트로부터 데이터 수신
            # buffer에 값이 있는 경우 우선 처리
            if b"<END>" in buffer:

                if buffer:
                    if buffer.startswith(b"REQUEST_CHUNK"):
                        newline_index = buffer.index(b"<END>")
                        message = buffer[:newline_index].decode(errors='ignore').strip()
                        buffer = buffer[newline_index + 5:]  # 처리한 부분을 제거하고 나머지 저장
                        print(f"[서버] 요청 수신: {message}\n")
                        request_queue.put(message)
                        continue
                    
                    elif buffer.startswith(b"CHUNK_DATA"):

                        newline_index = buffer.index(b"<EoH>")
                        message = buffer[:newline_index].decode(errors='ignore').strip()
                        buffer = buffer[newline_index + 5:]  # 처리한 부분을 제거하고 나머지 저장

                        chunk_data_end_index = buffer.index(b"<END>")
                        chunk_data = buffer[:chunk_data_end_index+5]
                        buffer = buffer[chunk_data_end_index + 5:]  # 처리한 부분을 제거하고 나머지 저장


                        # chunk_data = buffer
                        # buffer=b""
                        
                        response_queue.put(message.encode() + chunk_data)
                        print(f"[서버] 응답 수신: {message}\n")
                        continue
                        
                        
            # buffer에 <END>이 없으면 새 데이터를 수신
            if b"<END>" not in buffer:
                data = client_socket.recv(4096)  # 일단 첫 번째 데이터를 받음
                if not data:
                    print("data가 아닌 무언가가 들어옴<END>\n")
                else:
                    buffer += data
                    while b"<END>" not in buffer:  # <END>가 없을 동안 반복
                        data = client_socket.recv(4096)
                        if not data:
                            print("data가 아닌 무언가가 들어옴<END>\n")
                            break
                        buffer += data  # 새로 받은 데이터를 buffer에 추가





    except ConnectionResetError:
        print(f"[연결 종료] 클라이언트 {client_address} 연결 종료\n")
    finally:
        client_socket.close()
        clients = [(sock, addr, cid) for sock, addr, cid in clients if sock != client_socket]
        print(f"[연결 종료] 클라이언트 {client_id} 연결 제거 완료\n")

# 서버 실행 함수
def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...\n")

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
            print(f"[서버] 클라이언트 {client_id}에게 FLAG 전송 완료\n")

            thread = threading.Thread(target=handle_client, args=(client_socket, client_address, client_id))
            thread.start()
            threads.append(thread)
        
        # 모든 스레드가 종료될 때까지 대기
        for thread in threads:
            thread.join()

    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.\n")
    finally:
        for client_socket, _, _ in clients:
            client_socket.close()
        server.close()

if __name__ == "__main__":
    start_server()
