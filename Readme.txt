1조 조원 구성 및 역할

20203043 권수현 - 

20203058 남태인 - 

20203072 안민호 – 

1. 프로그램 구성요소 : server.py, client.py

◆ server.py 구성요소
① 

② 

③ 

④ 

⑤ 

⑥ 

◆ client.py 구성요소
① 

② 

③ 

④ 



2. 소스코드 컴파일 방법 (GCP 사용)

① 구글 클라우드에 접속하여 VM instance를 생성한다.
	지역 : us-central1로 설정
	머신 유형 : e2-micro
	부팅 디스크 : Debian

② 방화벽 규칙을 추가한다
	대상 : 모든 인스턴스 선택
	소스 IP 범위 : 0.0.0.0/0  (모든 IP 주소 허용)
	프로토콜 및 포트 : TCP와 해당 포트를 지정 (port : 9999)

③ 생성된 인스턴스의 SSH를 실행한다.

④ Python과 개발 도구의 패키지들을 설치한다 (Debian 기준)
	sudo apt update
	sudo apt install python3
	sudo apt install python3-pip
	pip install numpy
	pip install numpy scipy
	pip install loguru //Python에서 로그(logging)기능을 제공하는 라이브러리

⑤ 가상환경을 생성하고 활성화한다.
	python3 -m venv myenv(가상환경 이름)
	source myenv/bin/activate //가상환경 활성화

⑥ UPLOAD FILE을 클릭하여 server.py를 업로드한다.
	server.py가 업로드된 디렉터리에서 python3 server.py로 server를 실행한다.

⑦ 로컬에서 powershell 터미널 4개를 열어 python3 client.py로 client 4개를 실행한다. (vscode 터미널에서 실행해도 됨)
	
⑧ server에 4개의 client가 모두 연결되면 프로그램이 실행된다.

☆주의할 점 : client의 host 정의가 자신이 사용하는 외부주소로 되어있는지 확인한다



3. 프로그램 실행환경 및 실행방법 설명
(실행방법 - 2번 참고)
외부 서버 - 구글 클라우드 (파이썬 3.11.2버전, 0.25-2 vCPU (1 shared core)
		메모리 1GB, Boot disk size 20GB, interface type: SCSI
로컬 실행 환경 - 프로세서 12th Gen Intel(R) Core(TM) i5-12500H 2.50 GHz
		      RAM 16GB, 64bit 운영체제, x64기반 프로세서


4. 구현한 최적의 알고리즘 제시 및 설명

⦁ 알고리즘 시나리오
① [Client] request_order[]을 기반으로 서버에 요청 메시지 전송(REQUEST_CHUNK)
	request_order = [
        {'A': 'B', 'B': 'C', 'C': 'D', 'D': 'A'},
        {'A': 'C', 'B': 'D', 'C': 'A', 'D': 'B'},
        {'A': 'D', 'B': 'A', 'C': 'B', 'D': 'C'}
    ]
② [Server] 클라이언트로부터 "REQUEST_CHUNK"를 받고 저장. A, B, C, D 클라이언트의 각각의 4개의 요청이 Q에 차면 요청 위치에 맞게 4개의 클라이언트로 전송
③ [Client] 서버로부터 요청 수신 및 요청에 맞는 데이터 전송 (REQUEST_CHUNK)
④ [Server] 클라이언트로부터 "CHUNK_DATA"를 받고 저장. A, B, C, D,에서 보낸 4개의 CHUNK가 Q에 차면 위치에 맞게 4개의 클라이언트로 전송
⑤ [Client] 서버로부터 요청한 데이터 수신 및 received_chunks에 저장
⑥ [Client] all_chunks_received()로 chunk가 3907개가 다 모였는지 확인하고 합치기.


5. Error or Additional Message Handling
▶ Additional Message Handling
⊙ Server
① 종료 요청 처리 (EXIT)
- 클라이언트가 EXIT 메시지를 보내면 해당 클라이언트의 연결을 종료, 서버의 전체 연결 수가 최대값에 도달하면 서버 전체 종료
- exit_count를 증가, 모든 클라이언트 종료 요청을 받은 경우 os._exit(0) 시행
(gracefully termination)

② 수식 전송 처리 (SEND:순번:수식)
- SEND: 로 시작하는 메시지는 특정 순번의 수식 데이터로 인식
메시지 순번과 수식으로 파싱 후, 수식 대기 큐에 추가
- 순번을 기록해서 누락된 순번 감지, 누락 시 클라이언트에 해당 순번에 대해 
"FAILED:{expected_count}:{expression}" 메시지를 보내 재전송 요청

③ 결과 큐 메시지 처리
- 계산 결과가 result_queue에 쌓이면 클라이언트에게 해당 결과를 전송
- 결과 전송 시 client_socket.send()를 사용해 결과를 클라이언트로 전송

⊙ Client
① 재전송 요청 처리 ("FAILED:{expected_count}:{expression}\n")
- 서버로부터 FAILED 메시지를 수신하면 누락된 순번에 대한 재전송 요청으로 인식, 해당 순번을 failed_queue에 추가하여 재전송 준비
- 메시지 파싱 후 누락된 순번을 추출하고, failed_queue.put(failed_count)로 재전송 큐에 해당 순번 추가

② 수신한 결과 처리
- 서버로부터 정상적인 수식 계산 결과 메시지 수신 시 received_cnt를 증가시키고 로그 파일에 기록
- received_cnt[0] += 1로 수신된 결과 횟수 증가, [순번 결과 수신]: 결과 형식으로 로그와 콘솔에 기록

③ 종료 요청 처리(EXIT)
- 설정된 최대 수신 개수에 도달(MAX_RESULTS=1000)하면, 클라이언트는 EXIT 메시지를 서버로 전송해 연결 종료 요청을 보냄 (gracefully termination을 위해)
- client.send("EXIT\n".encode())로 서버 종료 요청 전송



▶ Error Handling (Exception 처리 포함)

⊙ Server
① 데이터 수신 오류(waiting() - except Exception as e)
- 클라이언트로부터 데이터를 수신하는 중 오류가 발생할 경우 예외 포착
- 발생한 오류를 로그파일에 기록, 해당 클라이언트와 연결 종료

② 결과 전송 오류(management() - except Exception as e)
- 계산된 결과를 클라이언트로 전송하는 과정에서 오류 발생 시 예외 포착
- 해당 오류를 로그 파일에 기록, result_queue.tast_done()을 호출해 해당 작업이 완료 되었음을 큐에 알림

③ 수식 계산 오류
- 계산 함수 내에 발생하는 모든 예외를 포착 (division by zero)
- 오류 메시지 출력 후 오류내용을 클라이언트에 전송

⊙ Client
① 전송 오류(send_expressions() - except Exception as e)
- 수식을 서버로 전송하는 중에 발생하는 모든 예외 포착
- 오류 내용을 로그 파일과 콘솔에 출력

② 수신 오류
- 서버로부터 결과를 수신하는 중 발생하는 모든 예외 포착
- 오류 내용을 로그 파일과 콘솔에 출력


6. Additional Comments (팀플 날짜 기록)
2024/11/9
과제 시작
