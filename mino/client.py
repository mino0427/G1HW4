import socket
import threading
import os

CHUNK_SIZE = 128 * 1024  # 128KB

# 서버에 연결하고 파일의 chunk를 관리하는 클라이언트 함수
def start_client(host="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    print(f"[서버 연결] {host}:{port}에 연결됨.")

    # 서버로부터 플래그 수신
    flag_msg = client.recv(4096).decode().strip()
    client_id = int(flag_msg.split(":")[1])  # FLAG:1, FLAG:2 등에서 숫자만 추출
    print(f"[클라이언트 ID 설정] ID: {client_id}")

    if 1 <= client_id <= 4:  # ID 범위가 1에서 4 사이일 경우에만 적용
        file_letter = chr(client_id + 64)  # 1 -> A, 2 -> B, 3 -> C, 4 -> D
        path = os.path.dirname(os.path.abspath(__file__))
        expression_file = path + f"/{file_letter}.file"
        print(f"[파일 선택] {expression_file}")

        chunks = []  # chunk를 저장할 리스트

        try:
            with open(expression_file, 'rb') as file:
                while True:
                    chunk = file.read(CHUNK_SIZE)  # 128KB씩 읽기
                    if not chunk:
                        break
                    chunks.append(chunk)
                print(f"[청크 로드 완료] {len(chunks)}개의 청크가 로드됨.")

                 # 각 청크의 내용을 출력
                for idx, chunk in enumerate(chunks):
                    print(f"[청크 {idx+1}] 크기: {len(chunk)} bytes")
                    print(f"{chunk}\n")  # 청크의 내용을 출력
        except FileNotFoundError:
            print(f"[오류] 파일 {expression_file}을(를) 찾을 수 없습니다.")
    else:
        print(f"[오류] 잘못된 클라이언트 ID: {client_id}")

    # 연결 종료
    # client.close()
    # print("[연결 종료] 서버와의 연결이 종료됨.")

if __name__ == "__main__":
    start_client()
