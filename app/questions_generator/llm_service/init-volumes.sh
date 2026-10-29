#!/usr/bin/env bash
set -e

MODEL_DIR="/models/rut5"
MODEL_REPO="cointegrated/rut5-base-multitask"
MODEL_VERSION="54bbd6542540528b9e99bbbe8feff7150d805588"
VERSION_FILE="$MODEL_DIR/.version"

mkdir -p "$MODEL_DIR"

check_version() {
    if [ -f "$VERSION_FILE" ]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
        if [ "$CURRENT_VERSION" = "$MODEL_VERSION" ]; then
            return 0  # версия совпадает
        else
            echo "Версия не совпадает: ожидается $MODEL_VERSION, найдено $CURRENT_VERSION"
            return 1
        fi
    fi
    return 1  # файл версии отсутствует
}

if [ -d "$MODEL_DIR" ] && [ -n "$(ls -A "$MODEL_DIR" 2>/dev/null)" ] && check_version; then
    echo "Модель уже есть и версия правильная ($MODEL_VERSION)"
else
    echo "Загружаем модель $MODEL_REPO версии $MODEL_VERSION..."
    rm -rf "$MODEL_DIR"/*

    hf download \
        "$MODEL_REPO" \
        --local-dir "$MODEL_DIR" \
        --revision "$MODEL_VERSION"

    echo "$MODEL_VERSION" > "$VERSION_FILE"
    echo "Модель загружена и зафиксирована версия $MODEL_VERSION"
fi
