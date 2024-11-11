import hashlib

# 파일 경로 목록
file_paths = [
    r"C:/Users/n3225/OneDrive/Desktop/test/A_com/A_B_complete.file",
    r"C:/Users/n3225/OneDrive/Desktop/test/A_com/A_C_complete.file",
    r"C:/Users/n3225/OneDrive/Desktop/test/A_com/A_D_complete.file"
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
    print(f"{file_path}: {md5_hash}\n")
