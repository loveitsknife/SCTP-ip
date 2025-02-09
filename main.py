# SCTP-ip
SCTP защита за счет маскирование ip
import socket
import sctp
import threading
import subprocess
from middlesocket import InputSocket, OutputSocket  # Импорт классов из новой библиотеки
from switch import InterfaceSwitcher
import time


connections = {}
connections_lock = threading.Lock()

def get_network_interfaces():
    result = subprocess.run(['ip', '-br', 'addr'], capture_output=True, text=True)
    interfaces = []
    if result.returncode == 0:
        lines = result.stdout.splitlines()
        for line in lines:
            parts = line.split()
            if parts:
                interfaces.append(parts[0])  # Добавляем имя интерфейса
    return interfaces

# Функции для работы с sub-интерфейсами
def interface_exists(interface_label):
    try:
        output = subprocess.check_output(f"ip addr show label {interface_label}", shell=True)
        return interface_label in output.decode()
    except subprocess.CalledProcessError:
        return False

def create_sub_interface(interface, new_ip, label):
    interface_label = f"{interface}:{label}"
    if not interface_exists(interface_label):
        command = f"sudo ip addr add {new_ip} dev {interface} label {interface_label}"
        subprocess.run(command, shell=True, check=True)
        print(f"Sub-интерфейс {interface_label} создан.")
    else:
        print(f"Sub-интерфейс {interface_label} уже существует.")
def establish_and_send_data(remote_ip, remote_port, data):
    print(f"Начало процесса отправки данных на {remote_ip}:{remote_port}")
    try:
        # Создание клиентского сокета
        print("Создание клиентского сокета...")
        with OutputSocket(port=0) as sock:  # Порт 0 для динамического выбора
            print("Добавление дополнительных адресов...")
            sock.add_address('192.168.1.101')
            sock.add_address('192.168.1.102')

            # Установление соединения
            print(f"Установление соединения с {remote_ip}:{remote_port}...")
            sock.establish_connection(remote_ip, remote_port)

            # Отправка данных
            print(f"Отправка данных на {remote_ip}:{remote_port}...")
            sock.send_packet(data.encode())

            # Ожидание подтверждения
            print("Ожидание ответа от сервера...")
            response = sock.receive_response()
            if response:
                print(f"Получен ответ от {remote_ip}: {response}")
            else:
                print("Ответ от сервера не получен или произошла ошибка.")

    except Exception as e:
        print(f"Ошибка при соединении или отправке данных на {remote_ip}:{remote_port}: {e}")
    finally:
        print(f"Завершение процесса отправки данных на {remote_ip}:{remote_port}")


# Пример клиентской функции отправки сообщения
def send_data_and_wait_for_response(sock, data):
    try:
        sock.send(data)
        response = sock.recv(1024)  # Ожидание ответа
        print("Ответ от сервера:", response.decode())
    except Exception as e:
        print("Ошибка при отправке данных:", e)

# Пример серверной функции обработки входящего соединения
def handle_incoming_connection(conn, addr):
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break  # Закрытие соединения, если данных нет
            print(f"Получены данные от {addr}: {data.decode()}")
        except Exception as e:
            print(f"Ошибка при обработке данных от {addr}: {e}")
            break
    print(f"Соединение с {addr} закрыто")
    conn.close()



def listen_for_connections(host, port):
    sock = InputSocket(host, port)
    print(f"Слушаю на {host}:{port}")

    while True:
        conn, addr = sock.accept()
        if conn is not None:
            client_thread = threading.Thread(target=handle_incoming_connection, args=(conn, addr))
            client_thread.start()
        else:
            print("Ошибка при принятии соединения.")


def add_ip_to_sctp_connection(sctp_socket, new_ip):
    # Привязка дополнительного IP-адреса к сокету
    try:
        sctp_socket.sctp_bindx([(new_ip, sctp_socket.getsockname()[1])], sctp.BINDX_ADD)
        print(f"Дополнительный IP {new_ip} добавлен к соединению.")
    except Exception as e:
        print(f"Ошибка при добавлении IP {new_ip} к соединению: {e}")

def send_continuous_messages(remote_ip, remote_port, switch):
    try:
        # Установление соединения перед началом отправки сообщений
        # Теперь используем текущий сокет в switch без вызова отсутствующего метода
        switch.socket.establish_connection(remote_ip, remote_port)
        print(f"Соединение установлено с использованием текущего интерфейса.")

        while True:
            # Отправка сообщения
            switch.send_packet(b"Hi! It's SCTP!")
            print(f"Сообщение 'Hi! It's SCTP!' отправлено на {remote_ip}:{remote_port}")
            time.sleep(10)

            # Проверка и применение изменения IP, если оно было инициировано
            if switch.check_for_interface_change():
                print("Происходит смена интерфейса...")
                switch.apply_interface_change(remote_ip, remote_port)
                # После смены интерфейса, сокет в switch автоматически обновляется,
                # поэтому нам не нужно пересоздавать соединение здесь
    except Exception as e:
        print(f"Ошибка при отправке данных: {e}")
    finally:
        if switch.socket is not None:
            switch.socket.close_connection()



def send_messages(host, port, switch):
    while True:
        command = input("Введите команду (send, continuous, exit): ").strip()
        if command.lower() == 'send':
            recipient_ip = input("Введите IP-адрес получателя: ").strip()
            message = input("Введите сообщение: ").strip()
            # Используем функцию establish_and_send_data для отправки сообщения
            establish_and_send_data(recipient_ip, port, message)


        elif command.lower() == 'continuous':
            recipient_ip = input("Введите IP-адрес получателя для непрерывной отправки: ").strip()
            continuous_thread = threading.Thread(target=send_continuous_messages, args=(recipient_ip, port, switch))
            continuous_thread.start()


        elif command.lower() == 'switch':
            interfaces = get_network_interfaces()  # Предполагаем, что эта функция возвращает список имен интерфейсов
            print("Доступные интерфейсы для управления:")
            for index, interface in enumerate(interfaces, start=1):
                print(f"{index}. {interface}")
            choice = int(input("Выберите номер интерфейса для временного использования: ")) - 1
            if 0 <= choice < len(interfaces):
                keep_interface = interfaces[choice]
                switch.disable_other_interfaces(keep_interface, 20)  # Используем новый метод
                print(f"Все интерфейсы, кроме {keep_interface}, временно отключены на 20 секунд.")
            else:
                print("Некорректный выбор. Пожалуйста, выберите номер из списка.")

        elif command.lower() == 'exit':
            break



def main():
    host = '192.168.1.2'  # Замените на свой локальный IP-адрес
    port = 5000

    create_sub_interface('eth0', '192.168.1.101/24', '1')
    create_sub_interface('eth0', '192.168.1.102/24', '2')

    output_socket = OutputSocket(port=0)  # Создание сокета для отправки сообщений
    switch = InterfaceSwitcher(output_socket)  # Создание экземпляра InterfaceSwitcher

    # Запускаем сервер и клиент
    server_thread = threading.Thread(target=listen_for_connections, args=(host, port))
    server_thread.start()

    send_thread = threading.Thread(target=send_messages, args=(host, port, switch))  # Передаем switch в send_messages
    send_thread.start()

    server_thread.join()
    send_thread.join()


if __name__ == "__main__":
    main()

