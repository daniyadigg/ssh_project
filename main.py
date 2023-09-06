import time
import datetime
import paramiko
import logging
import os
import sqlite3
import socket
import threading

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QFontDatabase

import des
import device_db
import task_db
import ui_menu_mode
import ui_menu_task
import ui_menu_device

import sys


conn = sqlite3.connect('ip_and_task.db')
cur = conn.cursor()

st = 0  # переменная для вывода работы задания при формирования отчета в БД

logging.basicConfig(filename='ssh.log', level=logging.INFO)


array_task = [task for task in cur.execute("SELECT * FROM task;")]  # формирование списка всех возможных задач в БД

# класс главного меню
class ExampleApp(QtWidgets.QMainWindow, des.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton_4.clicked.connect(self.exit)
        self.pushButton_3.clicked.connect(self.menu_mode)
        self.pushButton_2.clicked.connect(self.menu_task)
        self.pushButton.clicked.connect(self.menu_device)


        self.textEdit_2.setReadOnly(True)
        self.textEdit.setReadOnly(True)

        # запуск функции, которая заполняет окно станций, имеющих пинг
        self.ping_device()

        # запуск функции, которая заполняет окно состояния машин
        self.state_device()



    # функция выхода
    def exit(self):
        self.close()
    # меню отправки скрипта
    def menu_mode(self):
        self.menu_mode = MenuMode()
        self.menu_mode.show()
     # меню заданий
    def menu_task(self):
        self.menu_task = MenuTask()
        self.menu_task.show()
    # меню станций
    def menu_device(self):
        self.menu_device = MenuDevice()
        self.menu_device.show()

    # функция заполнения окна станциями, которые имеют пинг
    def ping_device(self):
        self.textEdit_2.clear()
        # блок определения станций, имеющих пинг
        global ping_device
        ping_device = []
        for device in cur.execute("SELECT * FROM devices;"):
            host = device[0]
            ping = os.system('ping -c 1 ' + host)
            if ping == 0:
                ping_device.append(device)
        self.textEdit_2.insertPlainText('Машины, имеющие соединения:\n')
        # завершаем выполнение функции, если нет машин, имеющих подключение
        if len(ping_device) == 0:
            self.textEdit_2.insertPlainText('Нет машин, имеющих соединения.')
            return
        # вывод машин, которые имеют соединение (ping)
        for i in ping_device:
            self.textEdit_2.insertHtml(f'{i[0]} {i[1]} {i[2]} {i[3]} <span style="color: green;">&#10004;</span>\n')

    #если что удалить, функция отслеживания состояния машин
    def state_device(self):
        # устанавливаем соединение
        for device in ping_device:
            h = device[0]
            u = device[1]
            p = device[2]
            self.textEdit.insertHtml(f'Станция: {h} {u} {p} <span style="color: green;">&#10004;</span>\n')
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()
            # обработка исключений корректного подключения
            try:
                ssh.connect(hostname=h, username=u, password=p)
                self.textEdit.insertPlainText('подключена')
            except paramiko.ssh_exception.AuthenticationException:
                self.textEdit.insertPlainText(f'Некорректные данные для подключения; измените данные в строке станции: {h} {u} {p}')
                continue
            except paramiko.ssh_exception.NoValidConnectionsError:
                self.textEdit.insertPlainText(f'На машине {h} {u} {p} не запущен SSH сервис')
                continue

            # получение информации о загруженности диска
            command = 'df -h'
            stdin, stdout, stderr = ssh.exec_command(command)
            output_disk = stdout.read().decode()
            self.textEdit.append("<span style='color:orangered;'>Загруженность диска:</span>")
            self.textEdit.append(output_disk)

            # получение информации о загрузке ЦП
            command = "top -bn1 | grep 'Cpu(s)'"
            stdin, stdout, stderr = ssh.exec_command(command)
            output_cp = stdout.read().decode()
            self.textEdit.append("<span style='color:orangered;'>Информация о загрузке ЦП:</span>")
            self.textEdit.append(output_cp)

            # получение информации о запущенных процессах
            command = "ps aux"
            stdin, stdout, stderr = ssh.exec_command(command)
            output_process = stdout.read().decode()
            self.textEdit.append("<span style='color:orangered;'>Информация о запущенных процессах:</span>")
            self.textEdit.append(output_process)

            # получение информации о открытых соединениях и портах
            command = "netstat -ano"
            stdin, stdout, stderr = ssh.exec_command(command)
            output_connection = stdout.read().decode()
            self.textEdit.append("<span style='color:orangered;'>Информация о соединениях и портах:</span>")
            self.textEdit.append(output_connection)

            # логирование собранной информации в БД
            cur.execute("INSERT INTO stat VALUES (?,?,?,?,?)", [h, output_disk, output_cp, output_process, output_connection])
            conn.commit()




# класс меню после нажатия кнопки "Переход к меню исполнения скрипта"
class MenuMode(QtWidgets.QMainWindow, ui_menu_mode.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.TextEdit.setReadOnly(True)
        self.pushButton_4.clicked.connect(self.exit)
        self.pushButton.clicked.connect(self.auto_mode)

    def exit(self):
        self.close()

    def auto_mode(self):
        self.TextEdit.clear()
        # блок определения станций, имеющих пинг
        ping_device = []
        for device in cur.execute("SELECT * FROM devices;"):
            host = device[0]
            ping = os.system('ping -c 1 ' + host)
            if ping == 0:
                ping_device.append(device)
        self.TextEdit.appendPlainText('Машины, имеющие соединения: ')
        # завершаем выполнение функции, если нет машин, имеющих подключение
        if len(ping_device) == 0:
            self.TextEdit.appendPlainText('Нет машин, имеющих соединения. Завершение работы...')
            QtWidgets.QMessageBox.information(self, "Внимание!", "Нет машин, имеющих соединения.")
            return
        # вывод машин, которые имеют соединение (ping)
        for i in ping_device:
            self.TextEdit.appendPlainText(' '.join(i))
        for device in ping_device:
            h = device[0]
            u = device[1]
            p = device[2]
            self.TextEdit.appendPlainText(f'Подключение к станции: {h} {u} {p}')
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()
            # обработка исключений корректного подключения
            try:
                ssh.connect(hostname=h, username=u, password=p)
                self.TextEdit.appendPlainText('Подключение прошло успешно')
            except paramiko.ssh_exception.AuthenticationException:
                self.TextEdit.appendPlainText(f'Некорректные данные для подключения; измените данные в строке станции: {h} {u} {p}')
                continue
            except paramiko.ssh_exception.NoValidConnectionsError:
                self.TextEdit.appendPlainText(f'На машине {h} {u} {p} не запущен SSH сервис')
                continue

            sftp_client = ssh.open_sftp()
            stdin, stdout, stderr = ssh.exec_command('mkdir /tmp/ssh-project/')
            for task in array_task:
                name = task[0]
                type = task[1]  # тип команда/скрипт
                comand = task[2]  # управляющая команда или путь до файла скрипта
                if isinstance(comand, bytes):
                    task_path = os.path.join("/home/user/PycharmProjects/ssh-project-main/scripts", name + ".sh")
                    with open(task_path, 'wb') as file:
                        file.write(comand)
                    comand = task_path
                if device[3] not in task[3]:
                    st = 0
                    continue
                if type.lower() == 'скрипт':
                    self.TextEdit.appendPlainText(f'Задание {name} {type} {comand}')
                    sftp_client.put(f'{comand}', f'/tmp/ssh-project/{name}')
                    stdin, stdout, stderr = ssh.exec_command(
                        f'chmod +x /tmp/ssh-project/{name} && /tmp/ssh-project/{name}')
                    logging.info(f'Скрипт выполнен: {datetime.datetime.now()} {h} {comand}')
                    st = stdout.readlines()
                    flag = 'выполнен'

                elif type.lower() == 'команда':
                    self.TextEdit.appendPlainText(f'Задание: {name} {type} {comand}')
                    stdin, stdout, stderr = ssh.exec_command(comand)
                    logging.info(f'Команда выполнена: {datetime.datetime.now()} {h} {comand}')
                    st = stdout.readlines()
                    flag = 'Выполнен'
                elif type.lower() != 'скрипт' and type.lower() != 'команда':
                    self.TextEdit.appendPlainText(f'Задание {name} {type} {comand} не отправлено, введите корректно тип задания')
                    flag = 'Не отправлено'
                    st = stdout.readlines()
                self.TextEdit.appendPlainText('Результат выполнения:')
                self.TextEdit.appendPlainText('\n' + '\n'.join(st))
                time.sleep(2)
                cur.execute("INSERT INTO log VALUES (?,?,?,?,?)", [datetime.datetime.now(), h, name, flag, str(st)])
                conn.commit()
        self.TextEdit.appendPlainText('Завершено.')
# класс меню после нажатия кнопки "Редактор списка заданий"
class MenuTask(QtWidgets.QMainWindow, ui_menu_task.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton_10.clicked.connect(self.exit)
        self.pushButton_5.clicked.connect(self.data_task)
    # функция выхода
    def exit(self):
        self.close()
    # функция отображения класса редактирования таблицы заданий
    def data_task(self):
        self.task_db = DataTask()
        self.task_db.show()

# класс меню после нажатия кнопки "Редактор рабочих станций станций"
class MenuDevice(QtWidgets.QMainWindow, ui_menu_device.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton_13.clicked.connect(self.exit)
        self.pushButton_15.clicked.connect(self.device_db)

        self.pushButton_14.clicked.connect(self.scan_device)

    # функция выхода
    def exit(self):
        self.close()

    # функция отображения класса вывода БД
    def device_db(self):
        self.device_db = DataDevice()
        self.device_db.show()

    # функция сканирования сети
    def scan_device(self):
        # функция получения IP нашей машины
        def getMyIp():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаем сокет (UDP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Настраиваем сокет на BROADCAST вещание
            s.connect(('<broadcast>', 0))
            return s.getsockname()[0]
        # сканирование сети
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
            return ip_list
        ip_list = []
        net = getMyIp()
        my_ip_message = f'Ваш IP: {net}'
        QtWidgets.QMessageBox.information(self, "Ваш IP", my_ip_message)
        net_split = net.split('.')
        a = '.'
        net = net_split[0] + a

        # Изменения: Ввод октетов через диалоговое окно
        start_octet1, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Начало первого октета:")
        if not ok:
            return
        end_octet1, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Конец первого октета:")
        if not ok:
            return
        start_octet2, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Начало второго октета:")
        if not ok:
            return
        end_octet2, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Конец второго октета:")
        if not ok:
            return
        start_octet3, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Начало третьего октета:")
        if not ok:
            return
        end_octet3, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Конец третьего октета:")
        if not ok:
            return
        start_point, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Начало четвертого октета:")
        if not ok:
            return
        end_point, ok = QtWidgets.QInputDialog.getInt(self, "Ввод октетов", "Конец четвертого октета:")
        if not ok:
            return

        message = 'Сканирование запущено. Не закрывайте окно Редактора станций. Нажмите OK.'
        QtWidgets.QMessageBox.information(self, 'Подождите', message )
        threads = []
        for ip in range(start_point, end_point):
            if ip == int(net_split[3]):
                continue
            potoc = threading.Thread(target=scan_Ip, args=[ip])
            potoc.start()
            threads.append(potoc)
        for thread in threads:
            thread.join()
        message = f'Найдено {len(ip_list)} станций, они будут добавлены в БД'
        QtWidgets.QMessageBox.information(self, "Количество станций", message)

        for ip in ip_list:
            cur.execute("INSERT INTO  devices VALUES (?,?,?,?)", [ip, 'user', '12345678', 'comp'])
            conn.commit()

# класс вывода окна после нажатия кнопки "Вывести список станций, имеющихся в БД"
class DataDevice(QtWidgets.QMainWindow, device_db.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.populate_table_devices()


        self.tableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.showContext)

        self.context_menu = QtWidgets.QMenu(self)
        self.add_row_action = self.context_menu.addAction("Добавить")
        self.add_row_action.setIcon(QtGui.QIcon('check.png'))
        self.delete_rows_action = self.context_menu.addAction("Удалить")
        self.delete_rows_action.setIcon(QtGui.QIcon('delete.png'))
        self.exit = self.context_menu.addAction('Выход')
        self.exit.setIcon(QtGui.QIcon('exit2.png'))

        self.add_row_action.triggered.connect(self.add_row)
        self.delete_rows_action.triggered.connect(self.delete_rows)
        self.exit.triggered.connect(self.close)

    # функция заполнения таблицы рабочих станций
    def populate_table_devices(self):
        connection = sqlite3.connect('ip_and_task.db')
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM devices')
        data = cursor.fetchall()

        self.tableWidget.setRowCount(len(data))
        self.tableWidget.setColumnCount(len(data[0]))


        for i, row in enumerate(data):
            for j, item in enumerate(row):
                cell = QtWidgets.QTableWidgetItem(str(item))
                self.tableWidget.setItem(i, j, cell)

    # функция контекстного меню по нажатию правой кнопки мыши
    def showContext(self, position):
        self.context_menu.exec_(self.tableWidget.viewport().mapToGlobal(position))

    # функция добавления строки в таблицу станций
    def add_row(self):
        current_row_count = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(current_row_count + 1)

        hostname_item = QtWidgets.QTableWidgetItem()
        username_item = QtWidgets.QTableWidgetItem()
        password_item = QtWidgets.QTableWidgetItem()
        device_type_item = QtWidgets.QTableWidgetItem()

        # Устанавливаем значения в элементы ячеек
        self.tableWidget.setItem(current_row_count, 0, hostname_item)
        self.tableWidget.setItem(current_row_count, 1, username_item)
        self.tableWidget.setItem(current_row_count, 2, password_item)
        self.tableWidget.setItem(current_row_count, 3, device_type_item)

        # Открываем диалоговое окно для ввода значений
        hostname_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Введите адрес хоста:")
        if ok:
            username_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Введите имя пользователя:")
            if ok:
                password_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Введите пароль:")
                if ok:
                    device_type_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных",
                                                                              "Введите тип устройства:")
                    if ok:
                            # Выполняем операции с полученными значениями
                        connection = sqlite3.connect('ip_and_task.db')
                        cursor = connection.cursor()
                        cursor.execute(
                            "INSERT INTO devices (hostname, username, password, type) VALUES (?, ?, ?, ?)",
                            (hostname_text, username_text, password_text, device_type_text))
                        connection.commit()
                        connection.close()
                        self.populate_table_devices()

    # функция удаления строки из таблицы станций
    def delete_rows(self):
            selected_rows = set(index.row() for index in self.tableWidget.selectedIndexes())
            connection = sqlite3.connect('ip_and_task.db')
            cursor = connection.cursor()
            for row in sorted(selected_rows, reverse=True):
                row_item = self.tableWidget.item(row, 0)
                if row_item is not None:
                    hostname = row_item.text()
                    cursor.execute('DELETE FROM devices WHERE hostname=?', (hostname,))
                    self.tableWidget.removeRow(row)
            connection.commit()
            connection.close()




# класс, после нажатия кнопки  "Вывести список заданий, имеющихся в БД"
class DataTask(QtWidgets.QMainWindow, task_db.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.populate_table_task()


        self.tableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.showContext)

        self.context_menu = QtWidgets.QMenu(self)
        self.add_row_action = self.context_menu.addAction("Добавить")
        self.add_row_action.setIcon(QtGui.QIcon('check.png'))
        self.delete_rows_action = self.context_menu.addAction("Удалить")
        self.delete_rows_action.setIcon(QtGui.QIcon('delete.png'))
        self.exit = self.context_menu.addAction('Выход')
        self.exit.setIcon(QtGui.QIcon('exit2.png'))

        self.exit.triggered.connect(self.close)
        self.add_row_action.triggered.connect(self.add_row)
        self.delete_rows_action.triggered.connect(self.delete_rows)
        self.show_info_message()




    # функция заполнения таблицы заданий
    def populate_table_task(self):
        connection = sqlite3.connect('ip_and_task.db')
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM task')
        data = cursor.fetchall()

        self.tableWidget.setRowCount(len(data))
        self.tableWidget.setColumnCount(len(data[0]))

        for i, row in enumerate(data):
            for j, item in enumerate(row):
                cell = QtWidgets.QTableWidgetItem(str(item))
                self.tableWidget.setItem(i, j, cell)

    # функция контекстного меню по нажатию правой кнопки мыши
    def showContext(self, position):
        self.context_menu.exec_(self.tableWidget.viewport().mapToGlobal(position))

    # функция добавления строки в таблицу заданий
    def add_row(self):
        current_row_count = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(current_row_count + 1)

        name_item = QtWidgets.QTableWidgetItem()
        type_item = QtWidgets.QTableWidgetItem()
        task_item = QtWidgets.QTableWidgetItem()
        for_type_device_item = QtWidgets.QTableWidgetItem()

        # Устанавливаем значения в элементы ячеек
        self.tableWidget.setItem(current_row_count, 0, name_item)
        self.tableWidget.setItem(current_row_count, 1, type_item)
        self.tableWidget.setItem(current_row_count, 2, task_item)
        self.tableWidget.setItem(current_row_count, 3, for_type_device_item)

        # Открываем диалоговое окно для ввода значений
        name_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Введите название задания:")
        if ok:
            type_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Введите тип задания: ")
            if ok:
                task_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных", "Укажите путь или задание:")
                if ok:
                    for_type_device_text, ok = QtWidgets.QInputDialog.getText(self, "Ввод данных",
                                                                              "Укажите типы устройств для задания:")
                    if ok:
                        # Выполняем операции с полученными значениями
                        connection = sqlite3.connect('ip_and_task.db')
                        cursor = connection.cursor()
                        cursor.execute(
                            "INSERT INTO task (name, type, task, for_type_device) VALUES (?, ?, ?, ?)",
                            (name_text, name_text, task_text, for_type_device_text))
                        connection.commit()
                        connection.close()
                        self.populate_table_task()

    # функция удаления строки из таблицы заданий
    def delete_rows(self):
            selected_rows = set(index.row() for index in self.tableWidget.selectedIndexes())
            connection = sqlite3.connect('ip_and_task.db')
            cursor = connection.cursor()
            for row in sorted(selected_rows, reverse=True):
                row_item = self.tableWidget.item(row, 0)
                if row_item is not None:
                    name = row_item.text()
                    cursor.execute('DELETE FROM task WHERE name=?', (name,))
                    self.tableWidget.removeRow(row)
            connection.commit()
            connection.close()

    # функция отображения окна с сообщением
    def show_info_message(self):
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Внимание!")
        msg_box.setText("Имя каждого задания должно быть уникальным")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()



# функция показа окна главного меню
def main_menu():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ExampleApp()  # Создаём объект класса ExampleApp
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение


# точка входа в приложение
if __name__ == '__main__':
    #menu_redactor()
    main_menu()
conn.close()