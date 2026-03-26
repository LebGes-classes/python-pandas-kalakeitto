import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

class MedicalDevice:
    """
    Класс, представляющий медицинское диагностическое устройство.
    Содержит все атрибуты оборудования и базовые методы доступа.
    """
    def __init__(
        self, device_id: str, clinic_id: str, clinic_name: str, city: str,
        department: str, model: str, serial_number: str, install_date: Optional[datetime],
        status: str, warranty_until: Optional[datetime], last_calibration_date: Optional[datetime],
        last_service_date: Optional[datetime], issues_reported_12mo: int,
        failure_count_12mo: int, uptime_pct: float, issues_text: str
    ):
        self.device_id = str(device_id)
        self.clinic_id = str(clinic_id)
        self.clinic_name = str(clinic_name)
        self.city = str(city)
        self.department = str(department)
        self.model = str(model)
        self.serial_number = str(serial_number)
        self.install_date = install_date
        self.status = status
        self.warranty_until = warranty_until
        self.last_calibration_date = last_calibration_date
        self.last_service_date = last_service_date
        self.issues_reported_12mo = int(issues_reported_12mo) if pd.notna(issues_reported_12mo) else 0
        self.failure_count_12mo = int(failure_count_12mo) if pd.notna(failure_count_12mo) else 0
        self.uptime_pct = float(uptime_pct) if pd.notna(uptime_pct) else 0.0
        self.issues_text = str(issues_text) if pd.notna(issues_text) else ""

    @property
    def total_problems(self) -> int:
        """Возвращает общее количество проблем и отказов за 12 месяцев."""
        return self.issues_reported_12mo + self.failure_count_12mo


class DeviceSerializer:
    """
    Класс для сериализации (Объект -> Данные) и десериализации (Данные -> Объект).
    Отвечает за очистку, нормализацию данных и преобразование типов.
    """
    
    STATUS_MAPPING = {
        'ok': 'operational',
        'op': 'operational',
        'работает': 'operational',
        'broken': 'faulty',
        'сломан': 'faulty',
        'неисправно': 'faulty',
        'planned': 'planned_installation'
    }

    @staticmethod
    def _parse_date(date_val: Any) -> Optional[datetime]:
        """Внутренний метод для безопасного парсинга дат."""
        if pd.isna(date_val):
            return None
        if isinstance(date_val, datetime):
            return date_val
        try:
            return pd.to_datetime(date_val).to_pydatetime()
        except Exception:
            return None

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> MedicalDevice:
        """
        Десериализует словарь (строку из таблицы) в объект MedicalDevice.
        Выполняет нормализацию статусов и валидацию дат.
        
        Args:
            data (Dict[str, Any]): Словарь с сырыми данными устройства.
            
        Returns:
            MedicalDevice: Экземпляр медицинского устройства.
        """
        # Парсинг дат
        install_date = cls._parse_date(data.get('install_date'))
        warranty_until = cls._parse_date(data.get('warranty_until'))
        last_calibration_date = cls._parse_date(data.get('last_calibration_date'))
        last_service_date = cls._parse_date(data.get('last_service_date'))

        # Валидация калибровки (не может быть раньше установки)
        if last_calibration_date and install_date and last_calibration_date < install_date:
            last_calibration_date = None

        # Нормализация статуса
        raw_status = str(data.get('status', '')).lower().strip()
        clean_status = cls.STATUS_MAPPING.get(raw_status, raw_status)

        return MedicalDevice(
            device_id=data.get('device_id'),
            clinic_id=data.get('clinic_id'),
            clinic_name=data.get('clinic_name'),
            city=data.get('city'),
            department=data.get('department'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            install_date=install_date,
            status=clean_status,
            warranty_until=warranty_until,
            last_calibration_date=last_calibration_date,
            last_service_date=last_service_date,
            issues_reported_12mo=data.get('issues_reported_12mo', 0),
            failure_count_12mo=data.get('failure_count_12mo', 0),
            uptime_pct=data.get('uptime_pct', 0.0),
            issues_text=data.get('issues_text', '')
        )

    @classmethod
    def serialize(cls, device: MedicalDevice) -> Dict[str, Any]:
        """
        Сериализует объект MedicalDevice обратно в словарь.
        
        Args:
            device (MedicalDevice): Экземпляр устройства.
            
        Returns:
            Dict[str, Any]: Словарь, готовый для выгрузки в JSON или Excel.
        """
        return {
            'device_id': device.device_id,
            'clinic_id': device.clinic_id,
            'clinic_name': device.clinic_name,
            'city': device.city,
            'department': device.department,
            'model': device.model,
            'serial_number': device.serial_number,
            'install_date': device.install_date,
            'status': device.status,
            'warranty_until': device.warranty_until,
            'last_calibration_date': device.last_calibration_date,
            'last_service_date': device.last_service_date,
            'issues_reported_12mo': device.issues_reported_12mo,
            'failure_count_12mo': device.failure_count_12mo,
            'uptime_pct': device.uptime_pct,
            'issues_text': device.issues_text
        }


class MedicalDeviceAnalyzer:
    """
    Класс, содержащий бизнес-логику для анализа данных медицинского оборудования.
    """
    
    def __init__(self, devices: List[MedicalDevice]):
        """
        Инициализирует анализатор списком устройств.
        
        Args:
            devices (List[MedicalDevice]): Список объектов MedicalDevice.
        """
        self.devices = devices

    def filter_by_warranty(self) -> Tuple[List[MedicalDevice], List[MedicalDevice]]:
        """
        Разделяет устройства на гарантийные и негарантийные.
        
        Returns:
            Tuple[List[MedicalDevice], List[MedicalDevice]]: 
            (Список устройств на гарантии, Список устройств без гарантии)
        """
        in_warranty = []
        out_of_warranty = []
        now = datetime.now()

        for device in self.devices:
            if device.warranty_until and device.warranty_until >= now:
                in_warranty.append(device)
            else:
                out_of_warranty.append(device)
                
        return in_warranty, out_of_warranty

    def get_top_problematic_clinics(self) -> List[Dict[str, Any]]:
        """
        Находит клиники с наибольшим количеством проблем (инциденты + отказы).
        
        Returns:
            List[Dict[str, Any]]: Отсортированный по убыванию список словарей 
            с данными о клиниках и количестве проблем.
        """
        clinic_stats = {}
        for device in self.devices:
            if device.clinic_id not in clinic_stats:
                clinic_stats[device.clinic_id] = {
                    'clinic_name': device.clinic_name,
                    'total_problems': 0
                }
            clinic_stats[device.clinic_id]['total_problems'] += device.total_problems

        # Сортировка по убыванию количества проблем
        sorted_clinics = sorted(
            clinic_stats.values(), 
            key=lambda x: x['total_problems'], 
            reverse=True
        )
        return sorted_clinics

    def get_calibration_report(self, interval_days: int = 365) -> List[Dict[str, Any]]:
        """
        Формирует отчет по устройствам, которым требуется калибровка.
        
        Args:
            interval_days (int): Регламентный интервал калибровки в днях. По умолчанию 365.
            
        Returns:
            List[Dict[str, Any]]: Список данных об устройствах, требующих калибровки.
        """
        report = []
        now = datetime.now()
        calibration_interval = timedelta(days=interval_days)

        for device in self.devices:
            needs_calibration = False
            next_due = None
            
            if not device.last_calibration_date:
                needs_calibration = True
            else:
                next_due = device.last_calibration_date + calibration_interval
                if next_due <= now:
                    needs_calibration = True

            if needs_calibration:
                report.append({
                    'device_id': device.device_id,
                    'clinic_name': device.clinic_name,
                    'model': device.model,
                    'last_calibration_date': device.last_calibration_date,
                    'next_calibration_due': next_due
                })
        return report

    def get_aggregated_summary(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Сагрегировать данные по клиникам и моделям оборудования.
        Аналог сводной таблицы (Pivot Table).
        
        Returns:
            Dict: Вложенный словарь вида {clinic_name: {model: {'count': X, 'avg_uptime': Y}}}
        """
        summary = {}
        
        for device in self.devices:
            clinic = device.clinic_name
            model = device.model
            
            if clinic not in summary:
                summary[clinic] = {}
            if model not in summary[clinic]:
                summary[clinic][model] = {'count': 0, 'total_uptime': 0.0}
                
            summary[clinic][model]['count'] += 1
            summary[clinic][model]['total_uptime'] += device.uptime_pct

        # Вычисляем средний аптайм вместо суммы
        for clinic, models in summary.items():
            for model, stats in models.items():
                stats['avg_uptime'] = stats['total_uptime'] / stats['count']
                del stats['total_uptime'] # Удаляем промежуточное значение

        return summary


def main(file_path: str):
    """
    Основная функция для запуска пайплайна обработки данных.
    """
    # 1. Читаем сырые данные (используем pandas только как ридер)
    raw_df = pd.read_excel(file_path)
    raw_data = raw_df.to_dict(orient='records')
    
    # 2. Десериализация данных (превращаем строки в объекты)
    devices = [DeviceSerializer.deserialize(row) for row in raw_data]
    
    # 3. Инициализация анализатора
    analyzer = MedicalDeviceAnalyzer(devices)
    
    # 4. Выполнение бизнес-задач
    in_warranty, out_of_warranty = analyzer.filter_by_warranty()
    top_clinics = analyzer.get_top_problematic_clinics()
    calibration_report = analyzer.get_calibration_report()
    summary = analyzer.get_aggregated_summary()
    
    # --- Вывод результатов ---
    print(f"Всего устройств: {len(devices)}")
    print(f"На гарантии: {len(in_warranty)}, Без гарантии: {len(out_of_warranty)}\n")
    
    print("--- ТОП-3 Проблемные клиники ---")
    for clinic in top_clinics[:3]:
        print(f"Клиника: {clinic['clinic_name']} | Проблем: {clinic['total_problems']}")
        
    print("\n--- Отчет по просроченной калибровке (первые 3) ---")
    for report_row in calibration_report[:3]:
        print(report_row)
        
    print("\n--- Сводная таблица (Пример для первой клиники) ---")
    first_clinic = list(summary.keys())[0] if summary else None
    if first_clinic:
        print(f"Клиника: {first_clinic}")
        for model, stats in summary[first_clinic].items():
            print(f"  Модель: {model} | Количество: {stats['count']} | Средний аптайм: {stats['avg_uptime']:.2f}%")

    # Сериализация результата обратно (пример)
    output_data = [DeviceSerializer.serialize(device) for device in in_warranty]
    pd.DataFrame(output_data).to_excel("in_warranty_devices.xlsx", index=False)

if __name__ == "__main__":
    FILE_PATH = 'medical_diagnostic_devices_10000.xlsx'
    main(FILE_PATH)
    pass