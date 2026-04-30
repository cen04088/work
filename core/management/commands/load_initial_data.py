import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from health.models import HealthClinic
from jobs.models import EmploymentSupportCenter
from pension.models import PensionSite


SUPPORT_CENTERS = [
    ("서울", "서울센터", "서울특별시", "1666-1829"),
    ("경기/인천", "경기센터", "수원·성남·안산 등 경기권", "1666-1829"),
    ("경기/인천", "인천센터", "인천광역시", "1666-1829"),
    ("강원", "강원센터", "춘천·원주·강릉 등 강원권", "1666-1829"),
    ("대전/충청", "대전센터", "대전·세종·충청권", "1666-1829"),
    ("광주/전남", "광주센터", "광주·전남권", "1666-1829"),
    ("전북", "전북센터", "전주·군산 등 전북권", "1666-1829"),
    ("대구/경북", "대구센터", "대구·경북권", "1666-1829"),
    ("부산/경남", "부산센터", "부산·울산·경남권", "1666-1829"),
]


class Command(BaseCommand):
    help = "Load bundled public CSV data into an empty deployment database."

    def handle(self, *args, **options):
        self.load_support_centers()
        self.load_clinics()
        self.load_pension_sites()

    def load_support_centers(self):
        for region, name, location, phone in SUPPORT_CENTERS:
            EmploymentSupportCenter.objects.update_or_create(
                name=name,
                defaults={
                    "region": region,
                    "location": location,
                    "phone_number": phone,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Support centers ready: {EmploymentSupportCenter.objects.count()}"))

    def load_clinics(self):
        if HealthClinic.objects.exists():
            self.stdout.write(f"Health clinics already loaded: {HealthClinic.objects.count()}")
            return

        path = Path(settings.BASE_DIR) / "data" / "건설근로자공제회_종합건강검진 수검기관_20250314.csv"
        rows = []
        with path.open("r", encoding="cp949", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(HealthClinic(
                    name=row.get("검진기관명", "").strip(),
                    address=row.get("주 소", "").strip(),
                    region=row.get("지역", "").strip(),
                    phone="",
                ))

        with transaction.atomic():
            HealthClinic.objects.bulk_create([row for row in rows if row.name], batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Health clinics loaded: {len(rows)}"))

    def load_pension_sites(self):
        if PensionSite.objects.exists():
            self.stdout.write(f"Pension sites already loaded: {PensionSite.objects.count()}")
            return

        path = Path(settings.BASE_DIR) / "data" / "건설근로자공제회_퇴직공제 가입사업장 정보_20260331.csv"
        rows = []
        with path.open("r", encoding="cp949", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(PensionSite(
                    project_name=row.get("공사명", "").strip(),
                    company_name=row.get("업체명", "").strip(),
                    total_amount=row.get("총공사금액(억원)", "").strip(),
                    client_org=row.get("수요기관", "").strip(),
                    address=row.get("소재지주소", "").strip(),
                ))

        with transaction.atomic():
            PensionSite.objects.bulk_create([row for row in rows if row.project_name], batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Pension sites loaded: {len(rows)}"))
