import os

def binary_to_text(binary_file_path, text_file_path):
    try:
        with open(binary_file_path, 'rb') as binary_file:
            binary_data = binary_file.read()
        
        with open(text_file_path, 'w', encoding='utf-8') as text_file:
            text_file.write(binary_data.decode('utf-8', errors='ignore'))
        
        print(f"The binary file '{binary_file_path}' has been successfully converted to '{text_file_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Process all files in the folder
folder_path = r"C:\\Users\\ksh07\\Desktop\\file"  # Replace with your folder path
output_folder = r"C:\\Users\\ksh07\\Desktop\\output"  # Replace with your output folder path

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for filename in os.listdir(folder_path):
    if filename.endswith('.file'):  # Adjust if needed for your file extension
        binary_file_path = os.path.join(folder_path, filename)
        text_file_path = os.path.join(output_folder, filename.replace('.file', '.txt'))
        binary_to_text(binary_file_path, text_file_path)
