import pandas as pd


file_path = 'medical_diagnostic_devices_10000.xlsx'

try:
    df = pd.read_excel(file_path)
except FileNotFoundError:
    print(f"Файл {file_path} не найден. Убедитесь, что он лежит в нужной папке.")


date_columns = ['install_date', 'warranty_until', 'last_calibration_date', 'last_service_date']
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors='coerce')

status_mapping = {
    'ok': 'operational',
    'op': 'operational',
    'broken': 'faulty',
    'planned_installation': 'planned_installation',
    'operational': 'operational',
    'maintenance_scheduled': 'maintenance_scheduled',
    'faulty': 'faulty'
}

df['status'] = df['status'].astype(str).str.lower().str.strip().map(status_mapping).fillna(df['status'])

mask_invalid_calibration = df['last_calibration_date'] < df['install_date']
df.loc[mask_invalid_calibration, 'last_calibration_date'] = pd.NaT

today = pd.Timestamp.today()

active_warranty_df = df[df['warranty_until'] >= today].copy()
expired_warranty_df = df[df['warranty_until'] < today].copy()
devices_without_warranty_info = df[df['warranty_until'].isna()].copy()

print(f"Устройств на гарантии: {len(active_warranty_df)}")
print(f"Устройств с истекшей гарантией: {len(expired_warranty_df)}")


clinics_with_most_issues = df.groupby(['clinic_id', 'clinic_name'])['issues_reported_12mo'].sum().reset_index()
clinics_with_most_issues = clinics_with_most_issues.sort_values(by='issues_reported_12mo', ascending=False)

print("\nТоп-3 клиники по количеству проблем:")
print(clinics_with_most_issues.head(3))


one_year_ago = today - pd.DateOffset(years=1)

df['needs_calibration'] = (df['last_calibration_date'].isna()) | (df['last_calibration_date'] < one_year_ago)

calibration_report = df[df['status'] == 'operational'][
    ['device_id', 'clinic_name', 'model', 'install_date', 'last_calibration_date', 'needs_calibration']
]

print("\nОтчет по калибровке (первые 5 строк работающих устройств):")
print(calibration_report.head())


pivot_report = pd.pivot_table(
    df,
    index=['clinic_name', 'department'], 
    columns=['model'],                   
    values=['device_id', 'uptime_pct', 'failure_count_12mo'],
    aggfunc={
        'device_id': 'count',           
        'uptime_pct': 'mean',           
        'failure_count_12mo': 'sum'     
    },
    fill_value=0 
)

print("\nФрагмент сводной таблицы (агрегация по клиникам и оборудованию):")
print(pivot_report.head())


with pd.ExcelWriter('medical_devices_report.xlsx') as writer:
    active_warranty_df.to_excel(writer, sheet_name='Active_Warranty', index=False)
    clinics_with_most_issues.to_excel(writer, sheet_name='Issues_by_Clinic', index=False)
    calibration_report.to_excel(writer, sheet_name='Calibration_Report', index=False)
    pivot_report.to_excel(writer, sheet_name='Pivot_Summary')