import socket
import os
import threading
import hashlib

lock = threading.Lock()

# 클라이언트별 시스템 클락 초기화 (msec 단위)
clients_system_clock = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

# 클라이언트별 메시지 처리 시간 설정 (단위: msec)
client_message_times = {
    'A': {'CHUNK_DATA': 6, 'OTHER': 0.6},
    'B': {'CHUNK_DATA': 7, 'OTHER': 0.7},
    'C': {'CHUNK_DATA': 8, 'OTHER': 0.8},
    'D': {'CHUNK_DATA': 9, 'OTHER': 0.9}
}

# 메시지에 따라 시간을 증가시키는 함수
def increment_client_clock(client_id, message_type):

    if client_id in client_message_times:
        # 메시지 유형에 따라 증가할 시간 결정
        if message_type in ['CHUNK_DATA', 'SEND_CHUNK']:
            delay = client_message_times[client_id]['CHUNK_DATA']
        else:
            delay = client_message_times[client_id]['OTHER']
        
        # 해당 클라이언트의 시스템 클락 증가
        clients_system_clock[client_id] += delay
        
    
    return clients_system_clock[client_id]


# 특정 시간이 주어졌을 때 시간을 동기화하는 함수
def sync_client_clock(client_id, clock):

    clients_system_clock[client_id] = clock
    
    return clients_system_clock[client_id]


def split_file_into_chunks(output_file_path, chunk_size,log_file):
    """파일을 청크 단위로 나누고 각 청크를 리스트에 저장"""
    chunks = []
    try:
        with open(output_file_path, 'rb') as file:
            print("[진행 중] 청크 단위를 나누는 중...")
            log_file.write("[진행 중] 청크 단위를 나누는 중...\n")
            chunk_id = 0
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                print(f"[진행 중] 청크 ID {chunk_id} 생성 완료")
                chunk_id += 1
            print("[완료] 청크 단위로 파일을 나누는 작업이 완료되었습니다.")
            log_file.write("[완료] 청크 단위로 파일을 나누는 작업이 완료되었습니다.\n")
    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {output_file_path}")
        log_file.write(f"[오류] 파일을 찾을 수 없습니다: {output_file_path}\n")
    except Exception as e:
        print(f"[오류] 파일 청크 나누기 중 예외 발생: {e}")
        log_file.write(f"[오류] 파일 청크 나누기 중 예외 발생: {e}\n")
    
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

    # 클라이언트 ID에 따라 로그 파일 지정
    log_file_path = f"Client{client_id}.txt"
    log_file = open(log_file_path, 'w')  # 로그 파일 직접 열기
    log_file.write(f"[로그 시작] 클라이언트 {client_id} 로그 파일\n")

    # 클라이언트 접속 순서에 맞는 파일 선택
    
    path = os.path.dirname(os.path.abspath(__file__))
    output_file_path = path + f"/{client_id}.file"
    # output_file_path = os.path.join("C:/Users/n3225/OneDrive/Desktop/test", f"{client_id}.file")
    print(f"[파일 선택] {output_file_path}")
    log_file.write(f"[파일 선택] {output_file_path}\n")
    
    # 파일을 청크 단위로 나누기
    chunks = split_file_into_chunks(output_file_path,128*1024,log_file)
    total_chunks = len(chunks)
    if chunks:
        print(f"[청크 생성 완료] 총 {total_chunks}개의 청크 생성")
    else:
        print("[오류] 파일 청크가 생성되지 않았습니다.")

    # 각 클라이언트가 보유한 청크 리스트 설정


    # 각 클라이언트가 보유하지 않은 3개의 파일을 저장할 리스트 생성 (각 파일의 청크를 None으로 초기화)
    received_chunks = {
        file_key: [None] * total_chunks for file_key in ['A', 'B', 'C', 'D'] if file_key != client_id
    }
    # 클라이언트 종료 조건: 모든 파일의 청크가 완전히 채워졌는지 확인
    def all_chunks_received():
        return all(
            all(chunk is not None for chunk in received_chunks[file_key])
            for file_key in received_chunks
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
                
                clock=round(increment_client_clock(client_id,"REQUEST_CHUNK"),1)
                print(f"{clock}[청크 요청] 클라이언트 {target_client_id}에게 청크 ID {chunk_index} 요청")
                log_file.write(f"{clock}[청크 요청] 클라이언트 {target_client_id}에게 청크 ID {chunk_index} 요청\n")
                break
            

        # 3. 서버로부터 데이터 수신 및 처리
        response = client.recv(4096)
        # 요청 메시지를 처리하고 청크 데이터를 전송
        if response.startswith(b"REQUEST_CHUNK"):
            decoded_response = response.decode()
            message_type, req_client_id,_, chunk_index,clock = decoded_response.split(":")#여기
            chunk_index = int(chunk_index)
            chunk_data = chunks[chunk_index]
            clock=round(sync_client_clock(client_id,float(clock)),1)
            print(f"{clock}[요청 수신] 클라이언트 {req_client_id}의 청크 요청 수신: CHUNK_ID {client_id}:{chunk_index}")
            log_file.write(f"{clock}[요청 수신] 클라이언트 {req_client_id}의 청크 요청 수신: CHUNK_ID {client_id}:{chunk_index}\n")
            
            # 이진 데이터와 헤더를 함께 전송
            header = f"CHUNK_DATA:{req_client_id}:{client_id}:{chunk_index}:<EoH>".encode()
            end = "<END>".encode()
            send_chunk_data=header+chunk_data + end
            client.send(send_chunk_data)
            
            clock=increment_client_clock(client_id, "CHUNK_DATA")
            print(f"{round(clock,1)}[청크 전송] 클라이언트 {client_id}가 청크 ID {chunk_index} 전송 완료")
            log_file.write(f"{round(clock,1)}[청크 전송] 클라이언트 {client_id}가 청크 ID {chunk_index} 전송 완료\n")
            
            data = client.recv(4096)  # 일단 첫 번째 데이터를 받음
            response=data
            if not response:
                print("data가 아닌 무언가가 들어옴<END>\n")
                log_file.write("data가 아닌 무언가가 들어옴<END>\n")
            else:
                
                while b"<END>" not in response:  # <END>가 없을 동안 반복
                    data = client.recv(4096)
                    if not data:
                        print("data가 아닌 무언가가 들어옴<END>")
                        log_file.write("data가 아닌 무언가가 들어옴<END>\n")
                        break
                    response += data  # 새로 받은 데이터를 buffer에 추가

            try:
                # 수신된 데이터를 텍스트로 변환해 헤더와 데이터 분리
                if response.startswith(b"SEND_CHUNK"):
                    header_end_index = response.index(b"<EoH>")
                    header = response[:header_end_index].decode()
                    chunk_data = response[header_end_index + 5:]  # 헤더 다음의 이진 데이터 부분
                    chunk_data = chunk_data.rstrip(b"<END>")  # 마지막의 <END>' 제거
                    message_type, sender_client_id, chunk_index,clock,_ = header.split(":")#################데이터 받는 형식이상 ,_ 추가함
                    chunk_index = int(chunk_index)

                    received_chunks[sender_client_id][chunk_index] = chunk_data
                    clock=round(sync_client_clock(client_id,float(clock)),1)
                    print(f"{clock}[청크 수신] 클라이언트{client_id}가 {sender_client_id}로부터 청크 ID {chunk_index} 수신 및 저장")
                    log_file.write(f"{clock}[청크 수신] 클라이언트{client_id}가 {sender_client_id}로부터 청크 ID {chunk_index} 수신 및 저장\n\n")


            except UnicodeDecodeError:
                print("[클라이언트] 이진 데이터 수신 처리 오류")
                log_file.write("[클라이언트] 이진 데이터 수신 처리 오류\n")
    
        order_index += 1

    print(f"{round(clients_system_clock[client_id],1)}[완료] 클라이언트 {client_id}는 모든 파일의 청크를 보유하고 있으므로 연결을 종료합니다.")
    log_file.write(f"{round(clients_system_clock[client_id],1)}[완료] 클라이언트 {client_id}는 모든 파일의 청크를 보유하고 있으므로 연결을 종료합니다.\n")
    
    # 파일이 완성되었는지 확인하고 합치기
    for file_key, chunks_list in received_chunks.items():
        if all(chunks_list):
            path = os.path.dirname(os.path.abspath(__file__))
            output_file_path = path + f"/{client_id}_{file_key}_complete.file"
            
            #output_file_path = os.path.join("C:/Users/n3225/OneDrive/Desktop/test", f"{client_id}_{file_key}_complete.file")
            with open(output_file_path, 'wb') as output_file:
                for chunk in chunks_list:
                    output_file.write(chunk)
            clock=clients_system_clock[client_id]
            print(f"{clock}[파일 생성 완료] {output_file_path}에 파일이 저장되었습니다.")
            log_file.write(f"{clock}[파일 생성 완료] {output_file_path}에 파일이 저장되었습니다.\n")


        #MD5 hash값 계산하기
        path = os.path.dirname(os.path.abspath(__file__))
        
        # 파일 경로 목록
        file_paths = [
            path+f"/A.file",
            path+f"/B_A_complete.file",
            path+f"/C_A_complete.file",
            path+f"/D_A_complete.file",
            
            path+f"/B.file",
            path+f"/A_B_complete.file",
            path+f"/C_B_complete.file",
            path+f"/D_B_complete.file",
            
            path+f"/C.file",
            path+f"/A_C_complete.file",
            path+f"/B_C_complete.file",
            path+f"/D_C_complete.file",
            
            path + f"/D.file",  
            path + f"/A_D_complete.file",    
            path + f"/B_D_complete.file",  
            path + f"/C_D_complete.file"
        ]
        
        # 각 파일의 MD5 해시 계산
    hash_results = {}
    for file_path in file_paths:
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                md5_hash = hashlib.md5(file_data).hexdigest()
                hash_results[file_path] = md5_hash
        except FileNotFoundError:
            hash_results[file_path] = "File not found"
        except Exception as e:
            hash_results[file_path] = f"Error: {str(e)}"

    # hash_results의 데이터 출력
    for file_path, md5_hash in hash_results.items():
        print(f"{file_path}: {md5_hash}")

        

    client.close()

if __name__ == "__main__":
    start_client()
