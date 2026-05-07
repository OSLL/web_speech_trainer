# animated_avatar

Локальный пайплайн для генерации видеоаватара из текста.

## Структура

```text
animated_avatar/
├── assets/
│   └── face.jpg
├── output/
├── piper_tts/
│   ├── .venv/
│   ├── output.wav
│   ├── requirements.txt
│   ├── run_piper.sh
│   ├── text.txt
│   ├── ru_RU-ruslan-medium.onnx
│   └── ru_RU-ruslan-medium.onnx.json
├── wav2lip/
│   ├── Wav2Lip/
│   ├── requirements.txt
│   └── run_wav2lip.sh
├── .gitignore
├── README.md
├── run.sh
└── setup.sh
```

## Первый запуск

Выдать права:

```bash
chmod +x run.sh setup.sh piper_tts/run_piper.sh wav2lip/run_wav2lip.sh
```

Подготовить окружение:

```bash
./setup.sh
```

## Генерация видео

```bash
./run.sh "Привет, это тест генерации видео"
```

Итоговый файл:

```bash
output/result.mp4
```

## Что нужно положить вручную

```text
assets/face.jpg
piper_tts/ru_RU-ruslan-medium.onnx
piper_tts/ru_RU-ruslan-medium.onnx.json
wav2lip/Wav2Lip/checkpoints/wav2lip_gan.pth
```