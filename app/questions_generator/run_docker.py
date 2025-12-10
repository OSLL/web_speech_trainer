import os
import sys
import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser(
        description="Запуск генератора вопросов по ВКР внутри Docker"
    )
    parser.add_argument(
        "vkr_path",
        help="Путь к .docx файлу с текстом ВКР (на хосте)",
    )
    args = parser.parse_args()

    host_path = os.path.abspath(args.vkr_path)

    if not os.path.exists(host_path):
        print(f"[ERROR] Файл не найден: {host_path}")
        sys.exit(1)

    # Путь внутри контейнера — фиксированный, один и тот же для всех ОС
    container_path = "/app/questions_generator/vkr_examples/vkr.docx"

    cmd = [
        "docker", "run", "-it", "--rm",
        "-v", "rut5-model:/app/question_generator/rut5-base",
        "-v", "rut5-nltk:/nltk_data",
        "-v", f"{host_path}:{container_path}:ro",
        "vkr-generator",
        "python", "run.py", container_path,
    ]

    print(">> Запускаю команду:")
    print(" ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] docker run завершился с ошибкой: {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
