import socket
import os
import threading

lock = threading.Lock()

def split_file_into_chunks(expression_file, chunk_size=128 * 1024):
    """파일을 청크 단위로 나누고 각 청크를 리스트에 저장"""
    chunks = []
    try:
        with open(expression_file, 'rb') as file:
            print("[진행 중] 청크 단위를 나누는 중...")
            chunk_id = 0
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                print(f"[진행 중] 청크 ID {chunk_id} 생성 완료")
                chunk_id += 1
            print("[완료] 청크 단위로 파일을 나누는 작업이 완료되었습니다.")
    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {expression_file}")
    except Exception as e:
        print(f"[오류] 파일 청크 나누기 중 예외 발생: {e}")
    
    return chunks

def request_chunk(client, chunk_id):
    """서버에 특정 청크를 요청"""
    with lock:
        client.send(f"REQUEST_CHUNK:{chunk_id}\n".encode())
        print(f"[청크 요청] 청크 ID {chunk_id} 요청")

def receive_chunk(client, chunk_id, client_chunks, received_chunks):
    """서버로부터 청크를 수신하고 리스트에 반영 및 저장"""
    with lock:
        response = client.recv(4096).decode().strip()
        if response == f"SEND_CHUNK:{chunk_id}":
            chunk_size = int(client.recv(4096).decode().strip())
            chunk_data = client.recv(chunk_size)
            received_chunks[chunk_id] = chunk_data  # 받은 청크를 저장 리스트에 저장
            client_chunks[chunk_id] = 1  # 보유 청크 리스트에 반영
            print(f"[청크 수신 및 반영] 청크 ID {chunk_id}를 수신하여 리스트에 저장 및 보유 리스트에 반영")

def send_chunk(client, chunk_id, chunks):
    """서버에 필요한 청크를 요청받고 전송"""
    with lock:
        client.send(f"CHUNK_DATA:{chunk_id}:{len(chunks[chunk_id])}\n".encode())
        client.send(chunks[chunk_id])
        print(f"[청크 전송] 청크 ID {chunk_id} 전송 완료 (크기: {len(chunks[chunk_id])} 바이트)")

# 서버에 연결하고 청크 단위로 파일을 나누는 클라이언트 함수
def start_client(host="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    print(f"[서버 연결] {host}:{port}에 연결됨.")
    
    # 서버로부터 플래그 수신
    flag_msg = client.recv(4096).decode().strip()
    client_id = flag_msg.split(":")[1]  # FLAG:A, FLAG:B 등에서 ID만 추출
    print(f"[클라이언트 ID 설정] ID: {client_id}")

    # 클라이언트 접속 순서에 맞는 파일 선택
    expression_file = os.path.join("C:\\Users\\ksh07\\Desktop\\file", f"{client_id}.file")
    print(f"[파일 선택] {expression_file}\n")

    # 파일을 청크 단위로 나누기
    chunks = split_file_into_chunks(expression_file)
    total_chunks = len(chunks)
    if chunks:
        print(f"[청크 생성 완료] 총 {total_chunks}개의 청크 생성")
    else:
        print("[오류] 파일 청크가 생성되지 않았습니다.")

    # 각 클라이언트가 보유한 청크 리스트 설정
    client_chunks = {
        'A': [1 if client_id == 'A' else 0 for _ in range(total_chunks)],  # A는 A 파일만 가짐
        'B': [1 if client_id == 'B' else 0 for _ in range(total_chunks)],  # B는 B 파일만 가짐
        'C': [1 if client_id == 'C' else 0 for _ in range(total_chunks)],  # C는 C 파일만 가짐
        'D': [1 if client_id == 'D' else 0 for _ in range(total_chunks)]   # D는 D 파일만 가짐
    }

    # 각 클라이언트가 보유하지 않은 3개의 파일을 저장할 리스트 생성 (각 파일의 청크를 None으로 초기화)
    received_chunks = {
        file_key: [None] * total_chunks for file_key in client_chunks if file_key != client_id
    }

    # 클라이언트 종료 조건: 모든 파일의 청크가 완전히 채워졌는지 확인
    def all_chunks_received():
        return all(
            all(chunk == 1 for chunk in client_chunks[file_key])
            for file_key in client_chunks
        )

    # 서버에 없는 청크를 요청
    for chunk_id in range(total_chunks):
        if client_chunks[client_id][chunk_id] == 0:  # 현재 클라이언트가 보유하지 않은 청크만 요청
            request_chunk(client, chunk_id)
            for file_key in received_chunks:
                if received_chunks[file_key][chunk_id] is None:
                    receive_chunk(client, chunk_id, client_chunks[client_id], received_chunks[file_key])

        if all_chunks_received():
            print(f"[완료] 클라이언트 {client_id}는 모든 파일의 청크를 보유하고 있으므로 연결을 종료합니다.")
            client.close()
            return

    # 파일이 완성되었는지 확인하고 합치기
    for file_key, chunks_list in received_chunks.items():
        if all(chunks_list):
            output_file_path = os.path.join("C:\\Users\\ksh07\\Desktop\\file", f"{client_id}_{file_key}_complete.file")
            with open(output_file_path, 'wb') as output_file:
                for chunk in chunks_list:
                    output_file.write(chunk)
            print(f"[파일 생성 완료] {output_file_path}에 파일이 저장되었습니다.")

    # 서버가 요청할 때 필요한 청크를 제공
    while True:
        request = client.recv(4096).decode().strip()
        if request.startswith("REQUEST_CHUNK"):
            _, chunk_id = request.split(":")
            chunk_id = int(chunk_id)
            send_chunk(client, chunk_id, chunks)

    client.close()

if __name__ == "__main__":
    start_client()
