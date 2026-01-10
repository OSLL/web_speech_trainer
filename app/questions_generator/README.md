## Запуск (контейнер вечно крутится)
`docker-compose up` - ВАЖНО: Первый раз ОЧЕНЬ ДОЛГО билдится (30-40 минут)

## Использование (интерактивное)
`docker compose exec app python run.py /app/static/vkr_examples/VKR1.docx --no-overflow-logs` - папка `vkr_examples` локальная

## Пример сгенерированных вопросов по тексту ВКР

[✔ OK] Как цель и задачи, сформулированные во введении, отражены в итоговых выводах заключения?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✔ OK] Какие термины и подходы из обзора предметной области легли в основу формальной постановки задачи?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✖ FAIL] В каких требованиях к решению, указанных в постановке задачи, находят отражение цели работы?
  - relevance: False
  - clarity:   True
  - difficulty:False

[✔ OK] Как практическая значимость работы следует из задач и результатов исследования?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✔ OK] Какие ограничения метода решения указаны в тексте и как они влияют на достижение цели?
  - relevance: True
  - clarity:   True
  - difficulty:False

--- rut5-base-multitask вопросы ---

[✖ FAIL] Что такое ЛЭТИ?
  - relevance: False
  - clarity:   False
  - difficulty:False

[✖ FAIL] Что является целью работы в веб-приложении?
  - relevance: True
  - clarity:   False
  - difficulty:False

[✖ FAIL] Что было проведено в конце работы?
  - relevance: False
  - clarity:   False
  - difficulty:False

[✔ OK] Что могут изменять объекты, располагаемые на карте?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✔ OK] Что представляет собой создание набора программных средств для отображения объектов на карте?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✖ FAIL] Сформировать требования к набору программных средств?
  - relevance: True
  - clarity:   False
  - difficulty:False

[✖ FAIL] Что является объектом исследования?
  - relevance: True
  - clarity:   False
  - difficulty:False

[✖ FAIL] Что существует уже давно?
  - relevance: True
  - clarity:   False
  - difficulty:False

[✔ OK] Что можно дать в контексте набора программных средств?
  - relevance: True
  - clarity:   True
  - difficulty:False

[✖ FAIL] ГИС является интегрированной информационной системой?
  - relevance: True
  - clarity:   False
  - difficulty:False
