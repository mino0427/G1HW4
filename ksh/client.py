import socket
import os


# 서버에 연결하고 수식을 전송하는 클라이언트 함수
def start_client(host="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    print(f"[서버 연결] {host}:{port}에 연결됨.")
    
    # 서버로부터 플래그 수신
    flag_msg = client.recv(4096).decode().strip()
    client_id = flag_msg.split(":")[1]  # FLAG:1, FLAG:2 등에서 숫자만 추출
    print(f"[클라이언트 ID 설정] ID: {client_id}")

    # 클라이언트 접속 순서에 맞는 파일 선택
    path = os.path.dirname(os.path.abspath(__file__))
    expression_file = "C:\\Users\\ksh07\\Desktop\\file" + f"/{client_id}.file"
    print(f"[파일 선택] {expression_file}\n")

    # 128KB 단위로 파일을 읽어 배열에 저장
    chunk_size = 128 * 1024  # 128KB
    chunks = []

    try:
        with open(expression_file, 'rb') as file:
            while chunk := file.read(chunk_size):  # Python 3.8 이상 사용 가능
                chunks.append(chunk)
        print(f"[파일 로드 완료] {len(chunks)}개의 청크가 배열에 저장됨.")
        
         # 배열에 저장된 모든 청크를 번호와 함께 출력
        for i, chunk in enumerate(chunks):
            print(f"\n=== 배열 번호 {i} ===")
            print(chunk)  # 이진 데이터를 그대로 출력
        
    except FileNotFoundError:
        print(f"[오류] {expression_file} 파일을 찾을 수 없음.")
    except Exception as e:
        print(f"[오류] 파일 읽기 중 예외 발생: {e}")
    
    client.close()

if __name__ == "__main__":
    start_client()