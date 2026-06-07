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

```bash
docker-compose --profile interview_profile up --build
```

## Что нужно положить вручную!!!

```text
assets/face.jpg
piper_tts/ru_RU-irina-medium.onnx
piper_tts/ru_RU-ruslan-medium.onnx
wav2lip/Wav2Lip/checkpoints/wav2lip_gan.pth
```
