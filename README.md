# SSH Project

## Описание
Скрипт позволяет в ручном, полуавтоматическом и автоматическом режиме, создавать и передавать на определенные удаленные рабочие станции задания для исполнения с формированием отчета о выполнении.  
Задания могут быть в виде shell-команд, скриптов, бинарных файлов.

## Описание режимов
1. Ручной: пользователю предлагается сформировать список станций, а затем список заданий, которые будут отправлены этим станциям.
2. Полуавтоматический: поочередно каждой станции назначается комплект задач, которые будут отправлены на эту станцию.
3. Автоматический: режим ничего не запрашивает и отправляет все задания всем доступным станциям, записи о которых есть в БД. 

## Системные требования
- Astra Linux 1.6
- Python 3.8

## Зависимости:
- time
- datetime
- paramiko
- logging
- os
- sqlite3
- socket
- threading

## Использование
Скрипт запускается с помощью python3.8 из папки  виртуального окружения проекта(venv).  
Пользовательский интерфейс скрипта реализуется в виде консольного меню.  
Задания описываются в таблице БД, они содержат: уникальное имя, тип(команда/скрипт), управляющая команда или путь до файла скрипта, тип станции для группирования рабочих станций.  
Задания и рабочие станции можно редактировать как через пользовательский интерфейс скрипта, так и с помощью таблицы БД (использовался SQLiteStudio3.3.3).  
Скрипт имеет 3 режима отправки заданий удаленным станциям: ручной, полуавтоматический и автоматический. Результаты выполнения заданий выводятся в терминал, а так же сохраняются в отчете БД и в файле логирования ssh.log. 
Скрипт позволяет обрабатывать корректность ввода пользователя, корректность заданий, подключений к станциям и ошибок вывода программы.  
Присутствует возможность сохранения заданий в виде BLOB-данных с последующей упаковкой в файл перед отправкой на исполнение.  
Так же, перед отправкой заданий производится проверка доступности рабочих станций из списка.

## Краткая инструкция
1. Запустите скрипт в командной строке или среде разработке python.
2. Для редактирования рабочих станций перейдите в „Редактор рабочих станций“, введя строке 1, для редактирования списка заданий введите 2.
3. Для выхода из „Редактора рабочих станций“ или „Редактора списка заданий“ введите 0.
4. Для перехода в меню выбора режима исполнения скрипта нажмите 0.
5. Выберите режим исполнения скрипта.
6. Для выхода после завершения выполнения программы нажмите 0.
