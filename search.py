import os

def search_files(directory, search_string):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if search_string in content:
                            print(f"Found in: {file_path}")
                except Exception as e:
                    print(f"Skipped {file_path}: {e}")

if __name__ == '__main__':
    search_files(r'C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\PROYECTS\HYDRA\HYDRA_frontend', 'Cargar los documentos')
