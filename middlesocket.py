import socket
import sctp
from threading import Thread

class MiddleSocket:
    def __init__(self, socket_type, address, port):
        self.socket_type = socket_type
        self.address = address
        self.port = port
        # Создаем SCTP сокет
        self.sock = sctp.sctpsocket_tcp(socket.AF_INET)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Привязываем сокет к начальному адресу и порту, если адрес указан
        if self.address:
            self.sock.bind((self.address, self.port))

    def add_address(self, new_ip):
        try:
            # Добавляем новый адрес к сокету с помощью bindx
            self.sock.bindx([(new_ip, self.port)], sctp.BINDX_ADD)
            print(f"Address {new_ip} added to the socket.")
        except Exception as e:
            print(f"Error adding address {new_ip}: {e}")

    def remove_address(self, ip):
        try:
            # Удаляем адрес из сокета
            self.sock.bindx([(ip, self.port)], sctp.BINDX_REM)
            print(f"Address {ip} removed from the socket.")
        except Exception as e:
            print(f"Error removing address {ip}: {e}")

    # Другие методы для отправки и приема данных

class InputSocket(MiddleSocket):
    def __init__(self, address, port):
        super().__init__(sctp.SOCK_STREAM, address, port)
        self.sock.listen(5)  # Прослушивание входящих соединений

    def accept(self):
        try:
            conn, addr = self.sock.accept()
            return conn, addr
        except Exception as e:
            print(f"Ошибка при принятии соединения: {e}")
            return None, None

    def send_packet(self, packet):
        try:
            self.sock.send(packet)
        except Exception as e:
            print(f"Ошибка при отправке пакета: {e}")



class OutputSocket(MiddleSocket):
    def __init__(self, port):
        super().__init__(sctp.SOCK_STREAM, '', port)
        self.sock = sctp.sctpsocket_tcp(socket.AF_INET)
        self.associated_addresses = []

    def add_address(self, new_ip):
        print(f"Добавление адреса {new_ip} к сокету.")
        self.associated_addresses.append(new_ip)
        # Привязка сокета к дополнительному адресу
        self.sock.bindx([(new_ip, self.port)])

    def establish_connection(self, remote_address, remote_port):
        # Привязка сокета к всем ранее добавленным адресам (если не выполнена)
        if self.associated_addresses:
            self.sock.bindx([(ip, self.port) for ip in self.associated_addresses])
        # Установление соединения
        try:
            self.sock.connect((remote_address, remote_port))
            print("Соединение установлено.")
        except Exception as e:
            print(f"Ошибка при установлении соединения: {e}")


    def remove_address(self, ip):
        """Удаляет адрес из списка ассоциированных адресов сокета."""
        print(f"Удаление адреса {ip} из сокета.")
        try:
            self.associated_addresses.remove(ip)
        except ValueError:
            print(f"Адрес {ip} не найден среди ассоциированных адресов.")

    def __enter__(self):
        return self  # Возвращает экземпляр для использования в контексте

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()  # Закрывает соединение при выходе из контекста

    """def establish_connection(self, remote_address, remote_port):
        try:
            self.sock.connect((remote_address, remote_port))
        except Exception as e:
            print(f"Ошибка при установлении соединения: {e}")"""

    def send_packet(self, packet):
        try:
            self.sock.send(packet)
        except Exception as e:
            print(f"Ошибка при отправке пакета: {e}")

    def receive_response(self, buffer_size=1024):
        try:
            response = self.sock.recv(buffer_size)
            return response.decode()  # Преобразование ответа в строку
        except Exception as e:
            print(f"Ошибка при получении ответа: {e}")
            return None

    def close_connection(self):
        self.sock.close()





