from django.core.management.base import BaseCommand
from jobs.models import EmploymentSupportCenter

class Command(BaseCommand):
    help = '건설근로자공제회 무료 취업지원센터 데이터 초기 적재'

    def handle(self, *args, **kwargs):
        centers_data = [
            {"region": "서울", "name": "서울센터", "location": "서울 중구", "phone": "02-2696-1829"},
            {"region": "서울", "name": "서울남부센터", "location": "서울 금천구", "phone": "1666-1122"},
            {"region": "서울", "name": "(사)국제직업능력개발교류협회", "location": "서울 서초구", "phone": "02-6949-0061"},
            {"region": "경기/인천", "name": "인천센터", "location": "인천 남동구", "phone": "032-654-1829"},
            {"region": "경기/인천", "name": "(사)미래고용노사네트워크", "location": "경기 고양시", "phone": "031-966-0556"},
            {"region": "경기/인천", "name": "경기수원지역자활센터", "location": "경기 수원시", "phone": "031-251-7006"},
            {"region": "강원", "name": "강원춘천센터 (희망리본)", "location": "강원 춘천시", "phone": "033-818-9559"},
            {"region": "대전/충청", "name": "가까운 센터 안내", "location": "대전/충청 지역", "phone": "1666-1829"},
            {"region": "광주/전남", "name": "(재)대원산업기술교육원", "location": "광주 광산구", "phone": "062-973-1829"},
            {"region": "광주/전남", "name": "(사)한국건설기능인협회", "location": "광주 남구", "phone": "062-464-1829"},
            {"region": "광주/전남", "name": "(사)한국건설기능인협회", "location": "전남 나주", "phone": "061-333-1829"},
            {"region": "전북", "name": "일드림사회적협동조합", "location": "전북 전주시", "phone": "063-902-1829"},
            {"region": "대구/경북", "name": "(사)사람들과다가치", "location": "대구 서구", "phone": "053-716-8218"},
            {"region": "대구/경북", "name": "(재)이찬", "location": "경북 포항시", "phone": "054-272-2820"},
            {"region": "부산/경남", "name": "(사)한국인재뱅크", "location": "부산 수영구", "phone": "051-751-4777"},
            {"region": "부산/경남", "name": "(사)고령사회고용진흥원", "location": "경남 창원시", "phone": "055-713-7179"},
        ]

        EmploymentSupportCenter.objects.all().delete()
        
        centers = []
        for item in centers_data:
            center = EmploymentSupportCenter(
                region=item['region'],
                name=item['name'],
                location=item['location'],
                phone_number=item['phone']
            )
            centers.append(center)
            
        EmploymentSupportCenter.objects.bulk_create(centers)
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(centers)} support centers.'))
