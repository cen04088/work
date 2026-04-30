import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import requests

from core.models import PublicDataSyncState
from health.models import HealthClinic
from jobs.models import EmploymentSupportCenter
from pension.models import PensionSite


SUPPORT_CENTERS = [
    {
        "센터명": "서울센터",
        "운영기관": "건설근로자공제회",
        "운영시간": "09:00-18:00",
        "주소": "서울특별시 중구 남대문로 109, 8층(국제빌딩)",
        "전화번호": "1666-1829",
    },
]
SUPPORT_CENTER_API_URL = "https://api.odcloud.kr/api/15083034/v1/uddi:9260f361-85f4-4202-a08d-dc9b3b40ae8b"
SUPPORT_CENTER_SOURCE_DATE = "2025-07-22"


class Command(BaseCommand):
    help = "Load bundled public CSV data into an empty deployment database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace public data even when rows already exist.",
        )
        parser.add_argument(
            "--daily-noon",
            action="store_true",
            help="Run only once per day after 12:00 in Asia/Seoul.",
        )

    def handle(self, *args, **options):
        if options["daily_noon"] and not self.should_run_daily_noon():
            self.stdout.write("Daily public data sync skipped.")
            return

        state, _ = PublicDataSyncState.objects.get_or_create(key="public_data_daily")
        try:
            self.load_support_centers()
            self.load_clinics(force=options["force"] or options["daily_noon"])
            self.load_pension_sites(force=options["force"] or options["daily_noon"])
            state.last_synced_at = timezone.now()
            state.last_status = "success"
            state.last_message = "Public data sync completed."
            state.save(update_fields=["last_synced_at", "last_status", "last_message"])
        except Exception as exc:
            state.last_synced_at = timezone.now()
            state.last_status = "failed"
            state.last_message = str(exc)
            state.save(update_fields=["last_synced_at", "last_status", "last_message"])
            raise

    def should_run_daily_noon(self):
        now = timezone.localtime()
        if now.hour < 12:
            return False
        state = PublicDataSyncState.objects.filter(key="public_data_daily").first()
        if not state or not state.last_synced_at:
            return True
        return timezone.localtime(state.last_synced_at).date() < now.date()

    def load_support_centers(self):
        rows = self.fetch_support_centers() or SUPPORT_CENTERS
        EmploymentSupportCenter.objects.all().delete()

        for row in rows:
            name = self.clean(row.get("센터명"))
            address = self.clean(row.get("주소"))
            if not name:
                continue
            EmploymentSupportCenter.objects.update_or_create(
                name=name,
                defaults={
                    "region": self.region_from_address(address),
                    "location": address,
                    "phone_number": self.clean(row.get("전화번호")),
                    "operator": self.clean(row.get("운영기관")),
                    "operating_hours": self.clean(row.get("운영시간")),
                    "source_updated_at": SUPPORT_CENTER_SOURCE_DATE,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Support centers ready: {EmploymentSupportCenter.objects.count()}"))

    def fetch_support_centers(self):
        api_key = settings.PUBLIC_DATA_API_KEY
        if not api_key:
            return []
        try:
            response = requests.get(
                SUPPORT_CENTER_API_URL,
                params={
                    "page": 1,
                    "perPage": 100,
                    "returnType": "json",
                    "serviceKey": api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Support center API fallback used: {exc}"))
            return []

    def clean(self, value):
        return str(value or "").strip()

    def region_from_address(self, address):
        if not address:
            return "전국"
        first = address.split()[0]
        mapping = {
            "서울시": "서울",
            "서울특별시": "서울",
            "수원시": "경기",
            "경기도": "경기",
            "인천": "인천",
            "인천광역시": "인천",
            "부산": "부산",
            "부산광역시": "부산",
            "대구": "대구",
            "대구광역시": "대구",
            "광주": "광주",
            "광주광역시": "광주",
            "대전": "대전",
            "대전광역시": "대전",
            "강원특별자치도": "강원",
            "강원도": "강원",
            "전북특별자치도": "전북",
            "전라북도": "전북",
            "전라남도": "전남",
            "경상북도": "경북",
            "경상남도": "경남",
        }
        return mapping.get(first, first)

    def load_clinics(self, force=False):
        if HealthClinic.objects.exists() and not force:
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
            if force:
                HealthClinic.objects.all().delete()
            HealthClinic.objects.bulk_create([row for row in rows if row.name], batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Health clinics loaded: {len(rows)}"))

    def load_pension_sites(self, force=False):
        if PensionSite.objects.exists() and not force:
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
            if force:
                PensionSite.objects.all().delete()
            PensionSite.objects.bulk_create([row for row in rows if row.project_name], batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Pension sites loaded: {len(rows)}"))
