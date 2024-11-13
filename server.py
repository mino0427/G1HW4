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


# 시스템 클락 초기화 (msec 단위)
clients_system_clock = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

# 클라이언트별 메시지 처리 시간 설정 (단위: msec)
client_message_times = {
    'A': {'CHUNK_DATA': 6, 'OTHER': 0.6},
    'B': {'CHUNK_DATA': 7, 'OTHER': 0.7},
    'C': {'CHUNK_DATA': 8, 'OTHER': 0.8},
    'D': {'CHUNK_DATA': 9, 'OTHER': 0.9}
}

# 시스템 클락을 업데이트하는 함수
def update_client_clock(client_id, message_type):
    # 각 클라이언트의 시간을 업데이트
    if client_id in client_message_times:
        # 클라이언트별 메시지 처리 시간 결정
        if message_type == 'CHUNK_DATA' or message_type == 'SEND_CHUNK':
            delay = client_message_times[client_id]['CHUNK_DATA']
        else:
            delay = client_message_times[client_id]['OTHER']
        
        # 해당 클라이언트의 시스템 클락 증가
        clients_system_clock[client_id] += delay
        
    # 클라이언트의 시스템 클락 값을 반환
    return round(clients_system_clock[client_id], 1)


# 클라이언트 시스템 클락 중 가장 큰 값으로 모든 클라이언트의 클락 동기화
def sync_with_max_client_time():
    # clients_system_clock에서 가장 큰 시간을 찾음
    max_time = max(clients_system_clock.values())
    for client in clients_system_clock:
        clients_system_clock[client] = max_time




def handle_client(client_socket, client_address, client_id,log_file):
    global clients
    clock_lock=1
    buffer=b""
    print(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})\n")
    log_file.write(f"[연결됨] 클라이언트 {client_address} (ID: {client_id})\n")
    try:
        while True:
        
            # request_queue에 데이터가 4개 있으면 반복 실행
            if not request_queue.empty() and request_queue.qsize() == 4:
                
                if(clock_lock==1):
                    sync_with_max_client_time()#시간 동기화
                    clock_lock=-3
                    print("\n")
                clock_lock+=1
                
                log_file.write("\n")
                for _ in range(4):
                    request_msg = request_queue.get()
                    message_type, req_client_id,target_client_id, chunk_id = request_msg.split(":")
                    chunk_id = int(chunk_id)

                    for client_sock, client_address, cid in clients:
                        if cid == target_client_id:
                            #######################################3
                            clock=update_client_clock(target_client_id,message_type)
                            request_msg=request_msg+":"+str(clock)
                            ###################################3
                            print(f"{clock}[서버] 클라이언트 {target_client_id}에게 요청 메시지 전달: {request_msg}\n")
                            log_file.write(f"{clock}[서버] 클라이언트 {target_client_id}에게 요청 메시지 전달: {request_msg}\n")
                            #############여기서 send 할 때 <END> 안붙이고 보냄
                            client_sock.send((request_msg).encode())
                            time.sleep(0.01)  # 하프 듀플렉스 전송 대기
                            break

            # response_queue에 데이터가 4개 있으면 반복 실행
            if not response_queue.empty() and response_queue.qsize() == 4:
                if(clock_lock==1):
                    sync_with_max_client_time()#시간 동기화
                    clock_lock=-3
                    print("\n")
                clock_lock+=1
                
                log_file.write("\n")
                for _ in range(4):
                    response_msg = response_queue.get()
                    header, chunk_data = response_msg.split(b":", 4)[:4], response_msg.split(b":", 4)[-1]
                    message_type, req_client_id ,sender_client_id, chunk_id = [part.decode() for part in header]  # b'' 제거
                    chunk_id = int(chunk_id)

                    for client_sock, client_address, cid in clients:
                        if cid == req_client_id:
                            clock=str(update_client_clock(req_client_id,message_type))
                            client_sock.send(f"SEND_CHUNK:{sender_client_id}:{chunk_id}:{clock}:<EoH>".encode() + chunk_data)
                            print(f"{clock}[서버] 클라이언트 {req_client_id}에게 청크 전송: CHUNK_ID {sender_client_id}:{chunk_id}\n")
                            log_file.write(f"{clock}[서버] 클라이언트 {req_client_id}에게 청크 전송: CHUNK_ID {sender_client_id}:{chunk_id}\n")
                            
                            
            # 클라이언트로부터 데이터 수신
            # buffer에 값이 있는 경우 우선 처리
            if b"<END>" in buffer:

                if buffer:
                    if buffer.startswith(b"REQUEST_CHUNK"):
                        newline_index = buffer.index(b"<END>")
                        message = buffer[:newline_index].decode(errors='ignore').strip()
                        buffer = buffer[newline_index + 5:]  # 처리한 부분을 제거하고 나머지 저장
                        message_type, req_client_id,target_client_id, chunk_id = message.split(":") # 요청 메시지 파싱
                        clock=round(update_client_clock(req_client_id,message_type),1)
                        print(f"{clock}[서버] 요청 수신: {message}\n")
                        log_file.write(f"{clock}[서버] 요청 수신: {message}\n")
                        request_queue.put(message)
                        continue
                    
                    elif buffer.startswith(b"CHUNK_DATA"):

                        newline_index = buffer.index(b"<EoH>")
                        message = buffer[:newline_index].decode(errors='ignore').strip()
                        buffer = buffer[newline_index + 5:]  # 처리한 부분을 제거하고 나머지 저장
                        chunk_data_end_index = buffer.index(b"<END>")
                        chunk_data = buffer[:chunk_data_end_index+5]
                        buffer = buffer[chunk_data_end_index + 5:]  # 처리한 부분을 제거하고 나머지 저장
                        
                        message2=message[:-1]
                        message_type, req_client_id, sender_client_id, chunk_id = message2.split(":")
                        clock=round(update_client_clock(sender_client_id,message_type),1)
                        print(f"{clock}[서버] {sender_client_id}로부터 데이터 수신: {message}\n")
                        log_file.write(f"{clock}[서버] {sender_client_id}로부터 데이터 수신: {message}\n")
                        
                        response_queue.put(message.encode() + chunk_data)
                        continue
                        
                        
            # buffer에 <END>이 없으면 새 데이터를 수신
            if b"<END>" not in buffer:
                data = client_socket.recv(4096)  # 일단 첫 번째 데이터를 받음
                if not data:
                    print("data가 아닌 값 수신\n")
                    log_file.write("data가 아닌 값 수신\n")
                    break
                else:
                    buffer += data
                    while b"<END>" not in buffer:  # <END>가 없을 동안 반복
                        data = client_socket.recv(4096)
                        if not data:
                            print("data가 아닌 값 수신\n")
                            log_file.wrtie("data가 아닌 값 수신\n")
                            break
                        buffer += data  # 새로 받은 데이터를 buffer에 추가


    except ConnectionResetError:
        print(f"[연결 종료] 클라이언트 {client_address} 연결 종료\n")
        log_file.write(f"[연결 종료] 클라이언트 {client_address} 연결 종료\n")
        
    finally:
        client_socket.close()
        clients = [(sock, addr, cid) for sock, addr, cid in clients if sock != client_socket]
        print(f"{round(clients_system_clock[client_id],1)}[연결 종료] 클라이언트 {client_id} 연결 제거 완료\n")
        log_file.write(f"{round(clients_system_clock[client_id],1)}[연결 종료] 클라이언트 {client_id} 연결 제거 완료\n")
        
# 서버 실행 함수
def start_server(host="127.0.0.1", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[서버 시작] {host}:{port}에서 대기 중...\n")

    # 서버 로그 파일 생성
    log_file_path = f"Server.txt"
    log_file = open(log_file_path, 'w', encoding='utf-8')  # 로그 파일 직접 열기
    log_file.write(f"[로그 시작] Server.txt\n")

    client_ids = ['A', 'B', 'C', 'D']
    try:
        while len(clients) < MAX_CLIENTS:
            client_socket, client_address = server.accept()
            client_id = client_ids[len(clients)]
            clients.append((client_socket, client_address, client_id))
            print(f"클라이언트 연결 완료: {client_address} (ID: {client_id})\n")
            log_file.write(f"클라이언트 연결 완료: {client_address} (ID: {client_id})\n")
            
            
        for client_socket, _, client_id in clients:
            # 접속 순서에 따라 FLAG 전송
            client_socket.send(f"FLAG:{client_id}".encode())
            print(f"[서버] 클라이언트 {client_id}에게 FLAG 전송 완료\n")
            log_file.write(f"[서버] 클라이언트 {client_id}에게 FLAG 전송 완료\n")
            thread = threading.Thread(target=handle_client, args=(client_socket, client_address, client_id,log_file))
            thread.start()
            threads.append(thread)
        
        
        
        # 모든 스레드가 종료될 때까지 대기
        for thread in threads:
            thread.join()

    
    except KeyboardInterrupt:
        print(f"[서버 에러]에러 발생 종료 작업을 실행합니다.\n")
        log_file.write(f"[서버 에러]에러 발생 종료 작업을 실행합니다.\n")
    finally:
        for client in clients:
            avg_time = clients_system_clock[client] / (3907*3)
            print(f"client {client}의 평균 전송 시간: {avg_time} msec\n")
            log_file.write(f"client {client}의 평균 전송 시간: {avg_time} msec\n")
            sync_with_max_client_time()
            
        print(f"{clients_system_clock[client_id]}[서버 종료] 서버가 종료됩니다.\n")
        log_file.write(f"{clients_system_clock[client_id]}[서버 종료] 서버가 종료됩니다.\n")
                
        for client_socket, _, _ in clients:
            client_socket.close()
        server.close()
        
        

if __name__ == "__main__":
    start_server()
