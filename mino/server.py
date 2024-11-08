import socket
import threading

MAX_CLIENTS = 4  # 클라이언트 최대 접속 수
clients = []  # 클라이언트 연결을 저장할 리스트

clients_lock = threading.Lock()
exit_count_lock = threading.Lock()

def start_server(host="0.0.0.0", port=9999):
    global system_clock_time
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...")

    client_id = 1
    while len(clients) < MAX_CLIENTS:
        client_socket, addr = server.accept()
        with clients_lock:
            clients.append((client_socket, addr))  # 연결을 리스트에 추가
        print(f"클라이언트 연결 완료: {addr}")
       
    for client in clients:
        # 접속 순서에 따라 FLAG 전송
        client[0].send(f"FLAG:{client_id}\n".encode())
        client_id += 1  # 다음 클라이언트에 대한 ID 증가


if __name__ == "__main__":
    start_server()