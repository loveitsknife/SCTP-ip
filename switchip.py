import subprocess
import threading


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
class InterfaceSwitcher:
    def __init__(self, socket):
        self.socket = socket
        self.all_interfaces = self.get_bound_addresses()  # Инициализация списка всех интерфейсов
        self.interface_change_requested = False  # Явно определяем атрибут
        self.new_interface = None


    def disable_temporary_interfaces(self, keep_interface, duration=20):
        """
        Временно отключает все интерфейсы, кроме указанного, на заданное время.
        """
        self.temp_disabled_interfaces = [iface for iface in self.all_interfaces if iface != keep_interface]
        # Пример логики отключения - на самом деле может потребоваться индивидуальная реализация
        for iface in self.temp_disabled_interfaces:
            self.socket.remove_address(iface)  # Предполагается, что есть метод для удаления адреса
        # Запускаем таймер для восстановления интерфейсов
        threading.Timer(duration, self.restore_interfaces).start()

    def toggle_interface(self, interface_name, duration=20):
        """Временно отключает и затем включает указанный интерфейс."""

        def enable_interface():
            subprocess.run(['sudo', 'ip', 'link', 'set', interface_name, 'up'], check=True)
            print(f"Интерфейс {interface_name} вновь включен.")

        try:
            # Отключаем интерфейс
            subprocess.run(['sudo', 'ip', 'link', 'set', interface_name, 'down'], check=True)
            print(f"Интерфейс {interface_name} временно отключен.")
            # Задаем таймер для включения интерфейса
            timer = threading.Timer(duration, enable_interface)
            timer.start()
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при выполнении команды: {e}")

    def disable_other_interfaces(self, keep_interface, duration=20):
        """Отключает все интерфейсы, кроме указанного, на заданное время."""
        interfaces = get_network_interfaces()  # Получаем список интерфейсов

        def restore_interfaces():
            for interface in interfaces:
                if interface != keep_interface:
                    subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], check=True)
                    print(f"Интерфейс {interface} вновь включен.")

        try:
            # Отключаем все интерфейсы, кроме выбранного
            for interface in interfaces:
                if interface != keep_interface:
                    subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], check=True)
                    print(f"Интерфейс {interface} временно отключен.")
            # Задаем таймер для восстановления интерфейсов
            timer = threading.Timer(duration, restore_interfaces)
            timer.start()
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при выполнении команды: {e}")
    def restore_interfaces(self):
        """
        Восстанавливает ранее отключенные интерфейсы.
        """
        for iface in self.temp_disabled_interfaces:
            self.socket.add_address(iface)
        self.temp_disabled_interfaces = []

    def get_bound_addresses(self):
        """
        Возвращает список всех IP-адресов, ассоциированных с сокетом.
        """
        try:
            addresses = self.socket.sock.getladdrs()
            return [addr[0] for addr in addresses]
        except Exception as e:
            print(f"Ошибка при получении списка адресов: {e}")
            return []

    def request_interface_change(self):
        """
        Запрашивает у пользователя выбор нового интерфейса для использования
        и инициирует процесс смены интерфейса.
        """
        addresses = self.get_bound_addresses()
        print("Доступные адреса для отправки данных:")
        for index, address in enumerate(addresses, start=1):
            print(f"{index}. {address}")

        choice = int(input("Выберите номер нового основного адреса для отправки данных: ")) - 1
        if 0 <= choice < len(addresses):
            self.new_interface = addresses[choice]
            self.interface_change_requested = True
            print(f"Интерфейс будет изменен на {self.new_interface} при следующей отправке сообщения.")
        else:
            print("Некорректный выбор. Пожалуйста, выберите номер из списка.")

    def check_for_interface_change(self):
        """
        Проверяет, была ли запрошена смена интерфейса.
        """
        return self.interface_change_requested


    def send_packet(self, packet):
        """
        Отправляет пакет через текущий активный интерфейс.
        """
        try:
            self.socket.send_packet(packet)
        except Exception as e:
            print(f"Ошибка при отправке пакета: {e}")

    def apply_interface_change(self):
        """
        Применяет запрошенное изменение интерфейса, временно отключая все остальные.
        """
        if self.interface_change_requested:
            # Временно отключаем все интерфейсы, кроме выбранного
            self.disable_temporary_interfaces(self.new_interface, duration=20)
            self.interface_change_requested = False  # Сбрасываем флаг запроса изменения



