## Запуск и настройка окружения
* Перейдите в директорию **pdf_parser**
* Установите необходимые зависимости 
* Запустите скрипт **perfomance_assessment.py**

```
pip install -r requirements.txt
python perfomance_assessment.py --pdf [filename].pdf --txt [filename].txt --opt Header1 Header2 ...
```

_Пример запуска_
```
python perfomance_assessment.py --pdf final.pdf --txt speach.txt --opt Заключение Апробация
```

_Результат:_
```
...
Пропускаем слайд с заголовком: Апробация
Пропускаем слайд с заголовком: Заключение
Оценка выступлению: 73.15384615384616 %

```

_Версия python 3.6.9_


## Результаты
* Будет создана директория с именем **[filename]** для пдф
* Текст каждого слайда предоставлен отдельным файлом
внутри данной папки
* Для текста выступления будет созана папка соответсвующая названию файла.
В ней будет лежать "очищенный" текст, название файла - **clear.txt**

_Директория **final**_:
```
1_slide.txt
...
16_slide.txt
```

_Директория **speach**_:
```
clear.txt
```
_До оброботки фрагмента текста:_
```
цель моей работы разработать набор автоматически проверяемых лабораторных работ на базе симулятора nao для этого требуется решить следующие задачи нужно провести обзор аналогов
создать лабораторные работы разработать систему проверки лабораторных работ обеспечить возможность подключения разработанной системы к существующим площадкам онлайн обучения и исследовать время проверки решения и количество потребляемых ресурсов

актуальность обусловлена следующими факторами во-первых это рост спроса на специалистов в области робототехники по данным компании Статиста уже в две тысячи двадцатом году рынок робототехники будет оцениваться в сто миллиардов долларов при годовом темпе роста в двадцать шесть процентов
во-вторых обучение программированию робота сопряжено с трудностями для программирования робота нужен либо робот либо симулятор робота во втором случае потребуется установить все необходимые пакеты
также знать как работать с операционной системы для которой предназначен симулятор что не является обязательным для тех кто хочет попробовать программирование робота и в-третьих эта популярность онлайн обучения в данный момент массовые открытые онлайн курсы привлекают множество людей разных возрастов со всего мира
чтобы понять как именно стоит организовывать лабораторные работы по программированию роботов был проведён обзор ресурсов обучающих программированию роботов
с точки зрения способа обучения а не получаемых знаний 

в результате обзора была разработана архитектура следующего вида задания должны представлять собой выполнение текста исходного кода управляющей программы для виртуального робота модуль проверки лабораторных работ должен генерировать случайные условия лабораторной работы принимать решения на проверку автоматически их проверять генерировать обратную связь по решению а также использовать различные симуляторы робота модуль для проверки лабораторных работ состоит из трёх компонентов
это проверочный модуль модуль генерации случайного условия лабораторной работы и симулятор робота
проверочный модуль с помощью модуля генерации случайного условия получает условие лабораторной работы и отдаёт его пользователям потом принимает решение на проверку с помощью симулятора робота запускает
это решение генерирует обратную связь и отправляет обратную связь пользователю в данной работе было принято решение сосредоточиться на создании лабораторных работ и их автоматической проверке
```
_После обработки:_
```
цель работа разработать набор автоматически проверять лабораторный работа база симулятор это требоваться решить следующий задача нужно провести обзор аналог
создать лабораторный работа разработать система проверка лабораторный работа обеспечить возможность подключение разработать система существующий площадка онлайн обучение исследовать время проверка решение количество потреблять ресурс

актуальность обусловить следующий фактор вопервое это рост спрос специалист область робототехника данные компания статистый тысяча двадцатый год рынок робототехника оцениваться сто миллиард доллар годовой темп рост двадцать шесть процент
вовторое обучение программирование робот сопрячь трудность программирование робот нужный либо робот либо симулятор робот второй случай потребоваться установить всё необходимый пакет
также знать работать операционный система который предназначить симулятор являться обязательный хотеть попробовать программирование робот втретий популярность онлайн обучение данный момент массовый открытый онлайн курс привлекать множество человек разный возраст весь мир
понять именно стоить организовывать лабораторный работа программирование робот проведна обзор ресурс обучать программирование робот
точка зрение способ обучение получать знание

результат обзор разработать архитектура следующий вид задание должный представлять выполнение текст исходный код управлять программа виртуальный робот модуль проверка лабораторный работа должный генерировать случайный условие лабораторный работа принимать решение проверка автоматически проверять генерировать обратный связь решение также использовать различный симулятор робот модуль проверка лабораторный работа состоять трх компонент
это проверочный модуль модуль генерация случайный условие лабораторный работа симулятор робот
проверочный модуль помощь модуль генерация случайный условие получать условие лабораторный работа отдата пользователь принимать решение проверка помощь симулятор робот запускать
это решение генерировать обратный связь отправлять обратный связь пользователь дать работа принять решение сосредоточиться создание лабораторный работа автоматический проверка
```
