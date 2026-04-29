import os
import sys
import pandas as pd
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from jobs.models import JobPosting
from health.models import HealthClinic
from pension.models import PensionSite

def import_jobs():
    print("Importing Jobs...")
    try:
        df = pd.read_csv('data/건설근로자공제회_건설근로자공제회_취업정보_20250722.csv', encoding='cp949')
        for _, row in df.iterrows():
            JobPosting.objects.update_or_create(
                company_name=row.get('센터명', ''),
                defaults={
                    'wnet_id': str(row.get('연번', '')),
                    'job_title': '건설근로자 취업지원 안내',
                    'work_region': row.get('주소', '')[:100],
                    'wage': '센터 문의',
                    'contact_phone': str(row.get('전화번호', '')),
                }
            )
        print(f"Imported {len(df)} jobs.")
    except Exception as e:
        print(f"Error importing jobs: {e}")

def import_clinics():
    print("Importing Clinics...")
    try:
        df = pd.read_csv('data/건설근로자공제회_종합건강검진 수검기관_20250314.csv', encoding='cp949')
        for _, row in df.iterrows():
            HealthClinic.objects.update_or_create(
                name=row.get('검진기관명', ''),
                defaults={
                    'address': row.get('주 소', ''),
                    'region': row.get('지역', ''),
                }
            )
        print(f"Imported {len(df)} clinics.")
    except Exception as e:
        print(f"Error importing clinics: {e}")

def import_pensions():
    print("Importing Pension Sites...")
    try:
        df = pd.read_csv('data/건설근로자공제회_퇴직공제 가입사업장 정보_20260331.csv', encoding='cp949')
        for _, row in df.iterrows():
            PensionSite.objects.update_or_create(
                project_name=row.get('공사명', ''),
                defaults={
                    'company_name': str(row.get('업체명', '')),
                    'total_amount': str(row.get('총공사금액(억원)', '')),
                    'client_org': str(row.get('수요기관', '')),
                    'address': str(row.get('소재지주소', '')),
                }
            )
        print(f"Imported {len(df)} pension sites.")
    except Exception as e:
        print(f"Error importing pension sites: {e}")

if __name__ == "__main__":
    import_jobs()
    import_clinics()
    import_pensions()
