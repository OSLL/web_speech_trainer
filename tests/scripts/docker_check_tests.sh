#!/bin/bash

compose="docker compose -f docker-compose.yml -f docker-compose-selenium.yml"
service="selenium-tests"
container_id=$($compose ps -a -q $service)

if [ -z "$container_id" ]; then
    echo "Контейнер сервиса $service не найден."
    exit 1
fi

while [ "$(docker inspect --format='{{.State.Running}}' "$container_id")" == "true" ]; do
    echo "tests in progress"
    sleep 30
done

echo "tests are finished"

EXIT_CODE=$(docker inspect "$container_id" --format='{{.State.ExitCode}}')
echo "tests logs:"
$compose logs $service
echo "web logs:"
$compose logs web
echo "processors logs:"
$compose logs audio_processor recognized_audio_processor presentation_processor recognized_presentation_processor training_processor

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "tests finished with code $EXIT_CODE (OK)"
    exit 0
else
    echo "tests are failed, code $EXIT_CODE"
    exit 1
fi
