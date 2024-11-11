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
    expression_file = os.path.join("C:/Users/n3225/OneDrive/Desktop/test", f"{client_id}.file")
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

    # 순회 방식 설정
    request_order = [
        {'A': 'B', 'B': 'C', 'C': 'D', 'D': 'A'},
        {'A': 'C', 'B': 'D', 'C': 'A', 'D': 'B'},
        {'A': 'D', 'B': 'A', 'C': 'B', 'D': 'C'}
    ]

    order_index = 0

    while not all_chunks_received():
        # 1. 현재 순회에 맞는 요청 순서를 설정
        current_order = request_order[order_index % len(request_order)]
        target_client_id = current_order[client_id]

        # 2. 서버에 요청 메시지 전송
        for chunk_index in range(total_chunks):
            if received_chunks[target_client_id][chunk_index] is None:
                client.send(f"REQUEST_CHUNK:{client_id}:{target_client_id}:{chunk_index}<END>".encode())#여기
                print(f"[청크 요청] 클라이언트 {target_client_id}에게 청크 ID {chunk_index} 요청")
                break
            

        # 3. 서버로부터 데이터 수신 및 처리
        response = client.recv(4096)
        # 요청 메시지를 처리하고 청크 데이터를 전송
        if response.startswith(b"REQUEST_CHUNK"):
            decoded_response = response.decode()
            _, req_client_id,_, chunk_index = decoded_response.split(":")#여기
            chunk_index = int(chunk_index)
            chunk_data = chunks[chunk_index]

            # 이진 데이터와 헤더를 함께 전송
            header = f"CHUNK_DATA:{req_client_id}:{client_id}:{chunk_index}:<EoH>".encode()
            end = "<END>".encode()
            send_chunk_data=header+chunk_data + end
            client.send(send_chunk_data)
            print(f"[청크 전송] 클라이언트 {client_id}가 청크 ID {chunk_index} 전송 완료")


            #response = client.recv(4096)
            #######################################
            response = client.recv(4096)  # 일단 첫 번째 데이터를 받음
            if not response:
                print("data가 아닌 무언가가 들어옴<END>\n")
            else:
                while b"<END>" not in response:  # <END>가 없을 동안 반복
                    data = client.recv(4096)
                    if not data:
                        print("data가 아닌 무언가가 들어옴<END>\n")
                        break
                    response += data  # 새로 받은 데이터를 buffer에 추가

            
            
            #######################################
            try:
                # 수신된 데이터를 텍스트로 변환해 헤더와 데이터 분리
                if response.startswith(b"SEND_CHUNK"):
                    header_end_index = response.index(b"<EoH>")
                    header = response[:header_end_index].decode()
                    chunk_data = response[header_end_index + 5:]  # 헤더 다음의 이진 데이터 부분

                    _, sender_client_id, chunk_index,_ = header.split(":")#################데이터 받는 형식이상 ,_ 추가함
                    chunk_index = int(chunk_index)

                    received_chunks[sender_client_id][chunk_index] = chunk_data
                    client_chunks[sender_client_id][chunk_index] = 1
                    print(f"[청크 수신] 클라이언트{client_id}가 {sender_client_id}로부터 청크 ID {chunk_index} 수신 및 저장")

            except UnicodeDecodeError:
                print("[클라이언트] 이진 데이터 수신 처리 오류")

    
        order_index += 1

    print(f"[완료] 클라이언트 {client_id}는 모든 파일의 청크를 보유하고 있으므로 연결을 종료합니다.")

    # 파일이 완성되었는지 확인하고 합치기
    for file_key, chunks_list in received_chunks.items():
        if all(chunks_list):
            output_file_path = os.path.join("C:/Users/n3225/OneDrive/Desktop/test", f"{client_id}_{file_key}_complete.file")
            with open(output_file_path, 'wb') as output_file:
                for chunk in chunks_list:
                    output_file.write(chunk)
            print(f"[파일 생성 완료] {output_file_path}에 파일이 저장되었습니다.")

    client.close()

if __name__ == "__main__":
    start_client()
