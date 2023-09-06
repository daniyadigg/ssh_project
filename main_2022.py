import time
import datetime
import paramiko
import logging
import os
import sqlite3
import socket
import threading


# функция сканирования сети для последующего добавления станций в БД
def scan():
    ip_list = []
    def getMyIp():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Создаем сокет (UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Настраиваем сокет на BROADCAST вещание
        s.connect(('<broadcast>', 0))
        return s.getsockname()[0]

    def scan_Ip(ip):
        for i in range(start_octet3, end_octet3 + 1):
            for j in range(start_octet2, end_octet2 + 1):
                for k in range(start_octet1, start_octet1 + 1):
                    addr = str(k) + '.' + str(j) + '.' + str(i) + '.' + str(ip)
                    comm = 'ping -c 1 ' + addr
                    response = os.popen(comm)
        data = response.readlines()
        for line in data:
            if 'ttl' in line:
                ip_list.append(addr)
                break

    net = getMyIp()
    print('Ваш IP :', net)
    net_split = net.split('.')
    a = '.'
    net = net_split[0] + a
    start_octet1, end_octet1 = int(input('Начало первого октета: ')), int(input('Конец первого октета: '))
    start_octet2, end_octet2 = int(input('Начало второго октета: ')), int(input('Конец второго октета: '))
    start_octet3, end_octet3 = int(input('Начало третьего октета: ')), int(input('Конец третьего октета: '))
    start_point = int(input("Начало четвертого октета: "))
    end_point = int(input("Конец четвертого октета: "))


    print("Сканирование в процессе...")
    threads = []
    for ip in range(start_point, end_point):
        if ip == int(net_split[3]):
            continue
        potoc = threading.Thread(target=scan_Ip, args=[ip])
        potoc.start()
        threads.append(potoc)
    for thread in threads:
        thread.join()
    print('Найдено', len(ip_list), 'станций, они будут добавлены в БД')
    for ip in ip_list:
        cur.execute("INSERT INTO  devices VALUES (?,?,?,?)", [ip, 'user', '12345678', 'comp'])
        conn.commit()



conn = sqlite3.connect('ip_and_task.db')
cur = conn.cursor()

st = 0 # переменная для вывода работы задания при формирования отчета в БД

logging.basicConfig(filename='ssh.log', level=logging.INFO)



# функция передачи всем рабочим станциям заданий в автоматическом режиме
def mode_auto():

    for device in ping_device:
        h = device[0]
        u = device[1]
        p = device[2]
        print('Подключение к станции:', h, u, p)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        try:
            ssh.connect(hostname=h, username=u, password=p)
            print('Подключение корректно')
        except paramiko.ssh_exception.AuthenticationException:
            print('Некорректные данные для подключения; измените данные в строке станции: ', h, u, p, '\n')
            continue
        except paramiko.ssh_exception.NoValidConnectionsError:
            print('На машине',h, u, p, 'не запущен SSH сервис', '\n')
            continue


        sftp_client = ssh.open_sftp()
        stdin, stdout, stderr = ssh.exec_command('mkdir /tmp/ssh-project/')
        for task in array_task:
            name = task[0]
            type = task[1] # тип команда/скрипт
            comand = task[2] # управляющая команда или путь до файла скрипта
            if isinstance(comand, bytes):
                task_path = os.path.join("/home/makarov/project/ssh-project/scripts/", name + ".sh")
                with open(task_path, 'wb') as file:
                    file.write(comand)
                comand = task_path

            if device[3] not in task[3]:
                st = 0
                continue
            if type.lower() == 'скрипт':
                print('Задание:', name, type, comand)
                sftp_client.put(f'{comand}', f'/tmp/ssh-project/{name}')
                stdin, stdout, stderr = ssh.exec_command(f'chmod +x /tmp/ssh-project/{name} && /tmp/ssh-project/{name}')
                logging.info(f'Скрипт выполнен: {datetime.datetime.now()} {h} {comand}')
                st = stdout.readlines()
                flag = 'выполнен'

            elif type.lower() == 'команда':
                print('Задание:', name, type, comand)
                stdin, stdout, stderr = ssh.exec_command(comand)
                logging.info(f'Команда выполнена: {datetime.datetime.now()} {h} {comand}')
                st = stdout.readlines()
                flag = 'Выполнен'
            elif type.lower() != 'скрипт' and type.lower() != 'команда':
                print('Задание', name, type, comand, 'не отправлено, введите корректно тип задания')
                flag = 'Не отправлено'
                st = stdout.readlines()
            print('Результат выполнения:', '\n', *st)
            time.sleep(2)
            cur.execute("INSERT INTO log VALUES (?,?,?,?,?)", [datetime.datetime.now(), h, name, flag, str(st)])
            conn.commit()

        stdin.close()
        time.sleep(2)
        sftp_client.close()
        ssh.close()
    print('Выполнение скрипта в автоматическом режиме закончено, файл логирования: ssh.log')
    



# функция передачи заданий в ручном режиме
def mode_hand():
    for device in ping_device:
        h = device[0]
        u = device[1]
        p = device[2]
        select_device = input(f'Отправить задания на станцию {h} {u} {p}? Введите Д или Н: ')
        if select_device.lower() != 'н' and select_device.lower() != 'д':
            print('Некорректный ввод')
            continue
        if select_device.lower() == 'н':
            continue
        if select_device.lower() == 'д':
            print('Подключение к станции:', h, u, p)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()
            try:
                ssh.connect(hostname=h, username=u, password=p)
                print('Подключение корректно')
            except paramiko.ssh_exception.AuthenticationException:
                print('Некорректные данные для подключения; измените данные в строке станции: ', h, u, p, '\n')
                continue
            except paramiko.ssh_exception.NoValidConnectionsError:
                print('На машине', h, u, p, 'не запущен SSH сервис', '\n')
                continue

            sftp_client = ssh.open_sftp()
            stdin, stdout, stderr = ssh.exec_command('mkdir /tmp/ssh-project/')
            time.sleep(1)
            for task in array_task:
                if device[3] not in task[3]:
                    st = 0
                    continue
                name = task[0]
                type = task[1]  # тип команда/скрипт
                comand = task[2]  # управляющая команда или путь до файла скрипта
                select_task = input(f'Отправить задачу {task}? Введите Д или Н: ')

                if select_task.lower() == 'д' and type.lower() == 'скрипт':
                    print('Задание:', name, type, comand)
                    sftp_client.put(f'{comand}', f'/tmp/ssh-project/{name}')
                    stdin, stdout, stderr = ssh.exec_command(f'chmod +x /tmp/ssh-project/{name} && /tmp/ssh-project/{name}')
                    logging.info(f'Скрипт выполнен: {datetime.datetime.now()} {h} {comand}')
                    st = stdout.readlines()
                    flag = 'выполнен'
                elif select_task.lower() == 'д' and type.lower() == 'команда':
                    print('Задание:', name, type, comand)
                    stdin, stdout, stderr = ssh.exec_command(comand)
                    logging.info(f'Команда выполнена: {datetime.datetime.now()} {h} {comand}')
                    st = stdout.readlines()
                    flag = 'выполнен'
                elif select_task.lower() == 'н':
                    continue
                else:
                    st = stdout.readlines()
                    flag = 'Ошибка'
                    print('Некорректный ввод')
                print('Результат выполнения:', '\n', *st)
                time.sleep(1)
                cur.execute("INSERT INTO log VALUES (?,?,?,?,?)", [datetime.datetime.now(), h, name, flag, str(st)])
                conn.commit()
        stdin.close()
        time.sleep(2)
        sftp_client.close()
        ssh.close()
    print('Конец списка задач и станций')



# функция передачи заданий в полуручном режиме
def semi_manual_mode():
    device_list = []
    task_list = []
    for device in ping_device:
        h = device[0]
        u = device[1]
        p = device[2]
        select_device = input(f'Добавить станцию {h} {u} {p} в список? Введите Д или Н: ')
        if select_device.lower() == 'н':
            continue
        elif select_device.lower() == 'д':
            device_list.append(device)
            print(f'Станция {h} {u} {p} добавлена в список')
        else:
            print('Некорректный ввод, машина не добавлена')
    print('Задания будут отправлены на станции: ', *device_list, sep='\n')
    for task in array_task:
        if len(device_list) == 0:
            print('В список машин ничего не добавлено')
            break
        name = task[0]
        type = task[1]  # тип команда/скрипт
        comand = task[2].rstrip()  # управляющая команда или путь до файла скрипта
        select_task = input(f'Добавить задание {task} в список? Введите Д или Н: ')
        if select_task.lower() == 'д':
            task_list.append(task)
        elif select_task.lower() == 'н':
            continue
        else:
            print('Некорректный ввод')
    print('Список заданий: ', *task_list, sep='\n')

    for device in device_list:
        h = device[0]
        u = device[1]
        p = device[2]
        print('Подключение к станции:', h, u, p)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        try:
            ssh.connect(hostname=h, username=u, password=p)
            print('Подключение корректно')
        except paramiko.ssh_exception.AuthenticationException:
            print('Некорректные данные для подключения; измените данные в строке станции: ', h, u, p, '\n')
            continue
        except paramiko.ssh_exception.NoValidConnectionsError:
            print('На машине', h, u, p, 'не запущен SSH сервис', '\n')
            continue

        sftp_client = ssh.open_sftp()
        stdin, stdout, stderr = ssh.exec_command('mkdir /tmp/ssh-project/')
        for task in task_list:
            if device[3] not in task[3]:
                st = 0
                continue
            name = task[0]
            type = task[1]  # тип команда/скрипт
            comand = task[2]  # управляющая команда или путь до файла скрипта

            if type.lower() == 'скрипт':
                print('Задание:', name, type, comand)
                sftp_client.put(f'{comand}', f'/tmp/ssh-project/{name}')
                stdin, stdout, stderr = ssh.exec_command(f'chmod +x /tmp/ssh-project/{name} && /tmp/ssh-project/{name}')
                logging.info(f'Скрипт выполнен: {datetime.datetime.now()} {h} {comand}')
                flag = 'выполнен'
                st = stdout.readlines()
            elif type.lower() == 'команда':
                print('Задание:', name, type, comand)
                stdin, stdout, stderr = ssh.exec_command(comand)
                logging.info(f'Команда выполнена: {datetime.datetime.now()} {h} {comand}')
                flag = 'выполнен'
                st = stdout.readlines()
            elif type.lower() != 'скрипт' and type.lower() != 'команда':
                print('Задание', name, type, comand, 'не отправлено, введите корректно тип задания')
                continue
            print('Результат выполнения:', '\n', *st)
            time.sleep(1)
            cur.execute("INSERT INTO log VALUES (?,?,?,?,?)", [datetime.datetime.now(), h, name, flag, str(st)])
        conn.commit()
        stdin.close()
        time.sleep(2)
        sftp_client.close()
        ssh.close()
    print('Выполнение скрипта в полуавтоматическом режиме закончено, файл логирования: ssh.log')



# функция меню выбора режима исполнения скрипта
def menu_mode():
    menu_str = '''
============================================
[1] Отправка заданий в автоматическом режиме
[2] Отправка заданий в ручном режиме        
[3] Отправка заданий в полуручном режиме   
[0] Выход                                   
============================================
➘
'''
    true_print = True

    while True:
        if true_print:
            print(menu_str)

        cho = input('>>> ')
        if cho == '0':
            break
        elif cho == '1':
            print('Переход в автоматический режим')
            mode_auto()
        elif cho == '2':
            print('Вы перешли в ручной режим')
            mode_hand()
        elif cho == '3':
            print('Вы перешли в полуручной режим')
            semi_manual_mode()
        else:
            print('Выберите пункт из меню')
            continue

def redactor_device():
    menu_str = '''
[1] Добавить
[2] Удалить
[3] Редактировать станцию
[4] Просканировать сеть и добавить станции в БД
[5] Вывести список станций, имеющихся в БД
[0] Назад
'''
    true_print = True
    while True:
        if true_print:
            print(menu_str)
        cho = input('>>> ')
        if cho == '1':
            try:
                cur.execute("INSERT INTO  devices VALUES (?,?,?,?)", input('Введите станцию: ').split())
                conn.commit()
            except sqlite3.ProgrammingError:
                print('Нужно ввести ip имя пароль тип через пробел')
        elif cho == '2':
            a = input('Удалить станции(ip): ').split()
            cur.execute("DELETE FROM devices WHERE hostname = ?", a)
            conn.commit()
        elif cho == '5':
            for device in cur.execute("SELECT * FROM devices;"):
                print(*device)
        elif cho == '0':
            break
        elif cho == '4':
            scan()
        elif cho == '3':
            ip = input('Введите ip адрес станции: ')
            user = input('Введите новое имя пользователя: ')
            password = input('Введите новый пароль: ')
            type = input('Введите новый тип: ')
            if user != '':
                cur.execute('''UPDATE devices SET username=? WHERE hostname=?''', (user, ip))
            if password != '':
                cur.execute('''UPDATE devices SET password=? WHERE hostname=?''', (password, ip))
            if type != '':
                cur.execute('''UPDATE devices SET type=? WHERE hostname=?''', (type, ip))
            conn.commit()
# функция преобразования данных в двоичный формат
def convert_to_binary_data(filename):
    with open(filename, 'rb') as file:
        blob_data = file.read()
    return blob_data

def insert_blob(name, type, task, for_type_device):
    try:
        sqlite_insert_blob_query = """INSERT INTO task
                                  (name, type, task, for_type_device) VALUES (?, ?, ?, ?)"""

        emp_task = convert_to_binary_data(task)
        # Преобразование данных в формат кортежа
        data_tuple = (name, type, emp_task, for_type_device)
        cur.execute(sqlite_insert_blob_query, data_tuple)
        conn.commit()
        print("Изображение и файл успешно вставлены как BLOB в таблиу")


    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)

def redactor_task():
    menu_str = '''
[1] Добавить
[2] Удалить
[3] Редактировать задание
[4] Вывести список заданий, имеющихся в БД
[5] Сохранить задание в виде BLOB-данных
[0] Назад
'''
    true_print = True
    while True:
        if true_print:
            print(menu_str)
        cho = input('>>> ')
        if cho == '1':
            try:
                cur.execute("INSERT INTO  task VALUES (?,?,?,?)", input('Введите задание: ').split())
                conn.commit()
            except sqlite3.ProgrammingError:
                print('Некорректный ввод задания')
        elif cho == '2':
            cur.execute("DELETE FROM task WHERE name = ?", input('Удалить задание(имя): ').split())
            conn.commit()
        elif cho == '4':
            for device in cur.execute("SELECT * FROM task;"):
                print(*device)
        elif cho == '3':
            name = input('Введите уникальное имя задания, которое хотите редактировать: ')
            type = input('Введите новый тип: ')
            task = input('Введите новое задание: ')
            for_type_device = input('Введите типы станций для задания: ')
            if type != '':
                cur.execute('''UPDATE task SET type=? WHERE name=?''', (type, name))
            if task != '':
                cur.execute('''UPDATE task SET task=? WHERE name=?''', (task, name))
            if for_type_device != '':
                cur.execute('''UPDATE task SET for_type_device=? WHERE name=?''', (for_type_device, name))
            conn.commit()
        elif cho == '0':
            break
        elif cho == '5':
            name = input('Введите имя: ')
            type = input('Введите тип: ')
            file = input('Введите название файла: ')
            for_type = input('Введите для каких типов: ')
            insert_blob(name, type, file, for_type)


def menu_redactor():
    menu_str = '''
[1] Редактор рабочих станций 
[2] Редактор списка заданий
[0] Переход к меню исполнения скрипта
'''
    true_print = True
    while True:
        if true_print:
            print(menu_str)

        cho = input('>>> ')
        if cho == '1':
            redactor_device()
        elif cho == '2':
            redactor_task()
        elif cho == '0':
            break
        else:
            print('Выберите пункт из меню')
            continue



menu_redactor()
#блок определения станций, имеющих пинг
ping_device = []
for device in cur.execute("SELECT * FROM devices;"):
    host = device[0]
    ping = os.system('ping -c 1 ' + host)
    if ping == 0:
        ping_device.append(device)
print('Машины, имеющие соединения:')
for i in ping_device:
    print(*i)

array_task = [task for task in cur.execute("SELECT * FROM task;")] # формирование списка всех возможных задач в БД
menu_mode()
conn.close()



