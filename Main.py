import pandas as pd

# --- 1. ЗАГРУЗКА ДАННЫХ ---

file_path = 'medical_diagnostic_devices_10000.xlsx'

try:
    df = pd.read_excel(file_path)
except FileNotFoundError:
    print(f"Файл {file_path} не найден. Убедитесь, что он лежит в нужной папке.")

# --- 2. ОЧИСТКА И ПРЕДОБРАБОТКА ДАННЫХ ---

# 2.1. Приведение дат к единому формату (datetime)
# errors='coerce' превратит некорректные даты (например, текст) в NaT (Not a Time)
date_columns = ['install_date', 'warranty_until', 'last_calibration_date', 'last_service_date']
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# 2.2. Нормализация статусов
# Приводим к нижнему регистру, убираем пробелы и используем словарь для маппинга
status_mapping = {
    'ok': 'operational',
    'op': 'operational',
    'broken': 'faulty',
    'planned_installation': 'planned_installation',
    'operational': 'operational',
    'maintenance_scheduled': 'maintenance_scheduled',
    'faulty': 'faulty'
}
# Применяем маппинг. Если статуса нет в словаре, оставляем как было (через fillna)
df['status'] = df['status'].astype(str).str.lower().str.strip().map(status_mapping).fillna(df['status'])

# 2.3. Обработка ошибочных дат калибровки (калибровка раньше установки)
# Если дата калибровки меньше даты установки, заменяем её на пустую (NaT)
mask_invalid_calibration = df['last_calibration_date'] < df['install_date']
df.loc[mask_invalid_calibration, 'last_calibration_date'] = pd.NaT


# --- 3. ВЫПОЛНЕНИЕ ЗАДАЧ АНАЛИЗА ---

today = pd.Timestamp.today()

# Задачa 1: Отфильтровать данные по гарантии
# Создаем два датафрейма: с активной гарантией и с истекшей
active_warranty_df = df[df['warranty_until'] >= today].copy()
expired_warranty_df = df[df['warranty_until'] < today].copy()
devices_without_warranty_info = df[df['warranty_until'].isna()].copy()

print(f"Устройств на гарантии: {len(active_warranty_df)}")
print(f"Устройств с истекшей гарантией: {len(expired_warranty_df)}")

# Задачa 2: Найти клиники с наибольшим количеством проблем
# Группируем по клиникам и суммируем проблемы за 12 месяцев
clinics_with_most_issues = df.groupby(['clinic_id', 'clinic_name'])['issues_reported_12mo'].sum().reset_index()
clinics_with_most_issues = clinics_with_most_issues.sort_values(by='issues_reported_12mo', ascending=False)

print("\nТоп-3 клиники по количеству проблем:")
print(clinics_with_most_issues.head(3))

# Задачa 3: Построить отчёт по срокам калибровки
# Определим устройства, требующие калибровки:
# (Например: калибровки никогда не было, или она была больше 1 года назад)
one_year_ago = today - pd.DateOffset(years=1)

# Создаем флаг "Требуется калибровка"
df['needs_calibration'] = (df['last_calibration_date'].isna()) | (df['last_calibration_date'] < one_year_ago)

# Собираем сам отчет
calibration_report = df[df['status'] == 'operational'][
    ['device_id', 'clinic_name', 'model', 'install_date', 'last_calibration_date', 'needs_calibration']
]

print("\nОтчет по калибровке (первые 5 строк работающих устройств):")
print(calibration_report.head())


# Задачa 4: Сагрегировать данные по клиникам и оборудованию (Сводная таблица)
# Построим сводную таблицу (pivot_table), чтобы показать:
# - Количество устройств каждой модели в клинике
# - Средний процент аптайма (uptime_pct)
# - Суммарное количество отказов за 12 месяцев
pivot_report = pd.pivot_table(
    df,
    index=['clinic_name', 'department'], # Строки: клиника и отделение
    columns=['model'],                   # Столбцы: модели аппаратов
    values=['device_id', 'uptime_pct', 'failure_count_12mo'],
    aggfunc={
        'device_id': 'count',           # Считаем количество аппаратов
        'uptime_pct': 'mean',           # Средний аптайм
        'failure_count_12mo': 'sum'     # Общее число отказов
    },
    fill_value=0 # Заменяем NaN на 0 там, где аппаратов данной модели нет
)

print("\nФрагмент сводной таблицы (агрегация по клиникам и оборудованию):")
print(pivot_report.head())

# Опционально: Сохранение результатов в новый Excel-файл со вкладками
with pd.ExcelWriter('medical_devices_report.xlsx') as writer:
    active_warranty_df.to_excel(writer, sheet_name='Active_Warranty', index=False)
    clinics_with_most_issues.to_excel(writer, sheet_name='Issues_by_Clinic', index=False)
    calibration_report.to_excel(writer, sheet_name='Calibration_Report', index=False)
    pivot_report.to_excel(writer, sheet_name='Pivot_Summary')