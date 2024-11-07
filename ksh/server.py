import socket
import threading

MAX_CLIENTS = 4  # 클라이언트 4개 대기
clients = []  # 클라이언트 연결을 저장할 리스트

# 각 클라이언트를 독립적으로 처리할 스레드 핸들러
class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, client_id):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.client_id = client_id

    def run(self):
        try:
            self.client_socket.send(f"FLAG:{self.client_id}\n".encode())
            print(f"[플래그 전송] 클라이언트 {self.client_address}에게 ID '{self.client_id}' 할당 및 전송 완료")
            # 클라이언트와의 추가 통신 로직이 필요하다면 여기에 작성
        except Exception as e:
            print(f"[오류] 클라이언트 {self.client_address} 처리 중 오류 발생: {e}")
        finally:
            self.client_socket.close()
            print(f"[연결 종료] 클라이언트 {self.client_address} 연결 종료")

# 서버 실행
def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...")

    client_ids = ['A', 'B', 'C', 'D']

    try:
        while len(clients) < MAX_CLIENTS:
            client_socket, addr = server.accept()
            client_id = client_ids[len(clients)]
            clients.append((client_socket, addr, client_id))  # 연결을 리스트에 추가
            print(f"클라이언트 연결 완료: {addr} (ID: {client_id})\n")

            handler = ClientHandler(client_socket, addr, client_id)
            handler.start()
    except KeyboardInterrupt:
        print("[서버 종료] 서버가 종료됩니다.")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
