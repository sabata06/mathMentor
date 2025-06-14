from django.core.management.base import BaseCommand
from mathmentor.models import Student
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Daha fazla örnek öğrenci oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Kaç öğrenci oluşturulacak (varsayılan: 10)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(
            self.style.SUCCESS(f'{count} yeni öğrenci oluşturuluyor...')
        )

        # Örnek öğrenci isimleri
        first_names = [
            'Ahmet', 'Mehmet', 'Ali', 'Ayşe', 'Fatma', 'Zeynep', 'Emre', 'Burak',
            'Selin', 'Deniz', 'Cem', 'Elif', 'Oğuz', 'Beren', 'Kaan', 'Dila',
            'Arda', 'Naz', 'Emir', 'Sude', 'Yiğit', 'Ece', 'Berk', 'İrem',
            'Mert', 'Defne', 'Eren', 'Aslı', 'Kerem', 'Pınar'
        ]
        
        last_names = [
            'Yılmaz', 'Kaya', 'Demir', 'Çelik', 'Şahin', 'Yıldız', 'Yıldırım', 'Öztürk',
            'Aydin', 'Özkan', 'Kaplan', 'Çetin', 'Kara', 'Koç', 'Kurt', 'Özdemir',
            'Aslan', 'Polat', 'Şimşek', 'Erdoğan', 'Çakır', 'Aksoy', 'Türk', 'Güneş',
            'Arslan', 'Kılıç', 'Uçar', 'Şen', 'Bayram', 'Tekin'
        ]
        
        parent_names = [
            'Ahmet Bey', 'Mehmet Bey', 'Ali Bey', 'Ayşe Hanım', 'Fatma Hanım', 
            'Zeynep Hanım', 'Emre Bey', 'Burak Bey', 'Selin Hanım', 'Deniz Hanım',
            'Cem Bey', 'Elif Hanım', 'Oğuz Bey', 'Beren Hanım', 'Kaan Bey'
        ]

        # Ders ücretleri (150-300 TL arası)
        lesson_fees = [150, 175, 200, 225, 250, 275, 300]

        students_created = 0

        for i in range(count):
            # Rastgele isim kombinasyonu
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            # Aynı isimde öğrenci var mı kontrol et
            full_name = f"{first_name} {last_name}"
            if Student.objects.filter(name=first_name, surname=last_name).exists():
                # Farklı soyisim dene
                last_name = random.choice(last_names)
                if Student.objects.filter(name=first_name, surname=last_name).exists():
                    continue  # Bu kombinasyonu atla
            
            # Telefon numarası oluştur
            phone = f"05{random.randint(10, 99)}{random.randint(100, 999)}{random.randint(10, 99)}{random.randint(10, 99)}"
            
            # Öğrenci oluştur
            student = Student.objects.create(
                name=first_name,
                surname=last_name,
                parent_name=random.choice(parent_names),
                parent_contact=phone,
                lesson_fee=Decimal(str(random.choice(lesson_fees))),
                debt_status=Decimal('0.00'),
                notes=f"{first_name} için özel notlar ve gözlemler"
            )
            
            students_created += 1
            self.stdout.write(f'  ✓ {student.name} {student.surname} oluşturuldu')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Başarıyla {students_created} yeni öğrenci oluşturuldu!'
            )
        ) 