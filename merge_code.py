import os

def merge_python_files(output_file='code.txt'):
    # Список папок, которые стоит игнорировать (опционально)
    ignore_dirs = {'.venv', 'venv', '__pycache__', '.git', '.idea', '.vscode'}
    
    # Имя самого скрипта, чтобы он не записывал сам себя
    current_script = os.path.basename(__file__)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Проходим по всем папкам и файлам
        for root, dirs, files in os.walk('.'):
            # Убираем игнорируемые папки из обхода
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if file.endswith('.py') and file != current_script:
                    file_path = os.path.join(root, file)
                    
                    # Пишем заголовок (путь к файлу)
                    outfile.write(f"{'='*60}\n")
                    outfile.write(f"FILE: {file_path}\n")
                    outfile.write(f"{'='*60}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"Ошибка при чтении файла: {e}")
                    
                    # Добавляем отступы между файлами
                    outfile.write("\n\n")

    print(f"Готово! Весь код собран в файл: {output_file}")

if __name__ == "__main__":
    merge_python_files()