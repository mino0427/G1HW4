# client.py

import socket
import os
import threading
import time

lock = threading.Lock()

def split_file_into_chunks(expression_file, chunk_size=128 * 1024):
    """파일을 청크 단위로 나누어 리스트에 저장"""
    chunks = []
    try:
        with open(expression_file, 'rb') as file:
            print("[진행 중] 파일을 청크 단위로 분할 중...")
            chunk_id = 0
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                print(f"[진행 중] 청크 ID {chunk_id} 생성 완료")
                chunk_id += 1
            print("[완료] 파일 분할이 완료되었습니다.")
    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {expression_file}")
    except Exception as e:
        print(f"[오류] 파일 분할 중 예외 발생: {e}")

    return chunks

def receive_data(client, client_id, chunks, client_chunks, received_chunks):
    while True:
        try:
            response = client.recv(4096)
            if not response:
                break  # 연결이 종료됨

            # 수신된 메시지 처리
            process_response(response, client, client_id, chunks, client_chunks, received_chunks)
        except Exception as e:
            print(f"[오류] 수신 스레드에서 예외 발생: {e}")
            break

def process_response(response, client, client_id, chunks, client_chunks, received_chunks):
    try:
        if response.startswith(b"SEND_CHUNK"):
            # 헤더와 청크 데이터 추출
            header_end_index = response.index(b"\n")
            header = response[:header_end_index].decode()
            chunk_data = response[header_end_index + 1:]  # 헤더 이후의 데이터

            _, sender_client_id, chunk_index = header.split(":")
            chunk_index = int(chunk_index)

            with lock:
                received_chunks[sender_client_id][chunk_index] = chunk_data
                client_chunks[sender_client_id][chunk_index] = 1
            print(f"[청크 수신] 클라이언트 {sender_client_id}로부터 청크 ID {chunk_index} 수신 완료")

        elif response.startswith(b"REQUEST_CHUNK"):
            # 요청자 ID와 청크 인덱스 추출
            decoded_response = response.decode()
            _, requester_client_id, chunk_index = decoded_response.strip().split(":")
            chunk_index = int(chunk_index)
            chunk_data = chunks[chunk_index]

            # 청크 데이터를 서버로 전송 (requester_client_id를 포함)
            header = f"CHUNK_DATA:{client_id}:{chunk_index}:{requester_client_id}\n".encode()
            client.send(header + chunk_data)
            print(f"[청크 전송] 클라이언트 {requester_client_id}에게 청크 ID {chunk_index} 전송 완료")
        else:
            print("[클라이언트] 알 수 없는 메시지 수신")
    except Exception as e:
        print(f"[오류] 응답 처리 중 예외 발생: {e}")


def all_chunks_received(client_chunks):
    with lock:
        return all(
            all(status == 1 for status in client_chunks[file_key])
            for file_key in client_chunks
        )

def start_client(host="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    print(f"[서버 연결] {host}:{port}에 연결됨.")

    # 서버로부터 FLAG 수신
    flag_msg = client.recv(4096).decode().strip()
    client_id = flag_msg.split(":")[1]  # FLAG:A 등에서 ID 추출
    print(f"[클라이언트 ID] ID 설정: {client_id}")

    # 클라이언트 ID에 따라 파일 선택
    expression_file = os.path.join("C:\\Users\\ksh07\\Desktop\\file", f"{client_id}.file")
    print(f"[파일 선택] {expression_file}\n")

    # 파일을 청크 단위로 분할
    chunks = split_file_into_chunks(expression_file)
    total_chunks = len(chunks)
    if chunks:
        print(f"[청크 생성 완료] 총 {total_chunks}개의 청크 생성")
    else:
        print("[오류] 청크가 생성되지 않았습니다.")

    # 클라이언트 청크 상태 초기화
    client_chunks = {
        file_key: [1 if client_id == file_key else 0 for _ in range(total_chunks)]
        for file_key in ['A', 'B', 'C', 'D']
    }

    # 수신한 청크 저장소 초기화
    received_chunks = {
        file_key: [None] * total_chunks for file_key in ['A', 'B', 'C', 'D'] if file_key != client_id
    }

    # 수신 스레드 시작
    receiver_thread = threading.Thread(target=receive_data, args=(client, client_id, chunks, client_chunks, received_chunks))
    receiver_thread.start()

    # 요청 순서 설정
    request_order = [
        {'A': 'B', 'B': 'C', 'C': 'D', 'D': 'A'},
        {'A': 'C', 'B': 'D', 'C': 'A', 'D': 'B'},
        {'A': 'D', 'B': 'A', 'C': 'B', 'D': 'C'}
    ]

    order_index = 0

    while not all_chunks_received(client_chunks):
        # 요청할 대상 클라이언트 결정
        current_order = request_order[order_index % len(request_order)]
        target_client_id = current_order[client_id]

        # 누락된 청크 찾기
        with lock:
            missing_chunks = [i for i, status in enumerate(client_chunks[target_client_id]) if status == 0]
        if missing_chunks:
            chunk_index = missing_chunks[0]
            request_msg = f"REQUEST_CHUNK:{client_id}:{chunk_index}\n"
            client.send(request_msg.encode())
            print(f"[청크 요청] 클라이언트 {target_client_id}에게 청크 ID {chunk_index} 요청")
        else:
            print(f"[정보] 클라이언트 {target_client_id}로부터 누락된 청크가 없습니다.")

        # 다음 요청까지 대기
        time.sleep(0.1)
        order_index += 1

    print(f"[완료] 클라이언트 {client_id}는 모든 청크를 보유했습니다. 연결을 종료합니다.")

    # 수신한 파일 저장
    for file_key, chunks_list in received_chunks.items():
        if all(chunk is not None for chunk in chunks_list):
            output_file_path = os.path.join("C:\\Users\\ksh07\\Desktop\\file", f"{client_id}_{file_key}_complete.file")
            with open(output_file_path, 'wb') as output_file:
                for chunk in chunks_list:
                    output_file.write(chunk)
            print(f"[파일 저장 완료] 파일이 {output_file_path}에 저장되었습니다.")

    client.close()

if __name__ == "__main__":
    start_client()
