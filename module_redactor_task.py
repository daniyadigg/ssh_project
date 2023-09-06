import sqlite3

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
        print("Изображение и файл успешно вставлены как BLOB в таблицу")


    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)

conn = sqlite3.connect('ip_and_task.db')
cur = conn.cursor()

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