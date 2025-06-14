from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, time
from mathmentor.models import Student, Lesson


class Command(BaseCommand):
    help = 'Çakışma kontrolü sistemini test et'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Çakışma kontrolü sistem testi başlatılıyor...'))
        
        # Test öğrencileri al (varsa)
        students = Student.objects.all()[:2]
        if len(students) < 2:
            self.stdout.write(self.style.ERROR('Test için en az 2 öğrenci gerekli!'))
            return
        
        student1, student2 = students[0], students[1]
        test_date = date.today()
        
        # Test 1: İlk ders oluştur
        self.stdout.write(f'\nTest 1: {student1.name} için ders oluşturuluyor...')
        try:
            lesson1 = Lesson.objects.create(
                student=student1,
                date=test_date,
                start_time=time(14, 0),  # 14:00
                end_time=time(15, 30),   # 15:30
                lesson_fee=200,
                status='scheduled'
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Ders başarıyla oluşturuldu: {lesson1}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Hata: {e}'))
            return
        
        # Test 2: Aynı saatte başka öğrenci için ders oluşturmaya çalış (çakışma olmalı)
        self.stdout.write(f'\nTest 2: {student2.name} için çakışan ders oluşturmaya çalışılıyor...')
        try:
            lesson2 = Lesson.objects.create(
                student=student2,
                date=test_date,
                start_time=time(14, 30),  # 14:30 (çakışıyor)
                end_time=time(16, 0),     # 16:00
                lesson_fee=200,
                status='scheduled'
            )
            self.stdout.write(self.style.ERROR(f'✗ PROBLEM: Çakışma algılanmadı! Ders oluşturuldu: {lesson2}'))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f'✓ Çakışma başarıyla algılandı: {e}'))
        
        # Test 3: Çakışmayan saatte ders oluştur
        self.stdout.write(f'\nTest 3: {student2.name} için çakışmayan ders oluşturuluyor...')
        try:
            lesson3 = Lesson.objects.create(
                student=student2,
                date=test_date,
                start_time=time(16, 0),   # 16:00 (çakışmıyor)
                end_time=time(17, 30),    # 17:30
                lesson_fee=200,
                status='scheduled'
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Ders başarıyla oluşturuldu: {lesson3}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Beklenmeyen hata: {e}'))
        
        # Test 4: Mevcut dersi güncelleme (çakışmasız)
        self.stdout.write(f'\nTest 4: Mevcut ders güncelleniyor (çakışmasız)...')
        try:
            lesson1.start_time = time(13, 0)
            lesson1.end_time = time(14, 0)
            lesson1.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Ders başarıyla güncellendi: {lesson1}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Hata: {e}'))
        
        # Test 5: Mevcut dersi güncelleme (çakışmalı)
        self.stdout.write(f'\nTest 5: Mevcut ders güncelleniyor (çakışmalı)...')
        try:
            lesson1.start_time = time(16, 30)  # lesson3 ile çakışacak
            lesson1.end_time = time(18, 0)
            lesson1.save()
            self.stdout.write(self.style.ERROR(f'✗ PROBLEM: Çakışma algılanmadı! Ders güncellendi: {lesson1}'))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f'✓ Çakışma başarıyla algılandı: {e}'))
        
        # Test sonuçları
        self.stdout.write(f'\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('TEST TAMAMLANDI'))
        
        # Oluşturulan test derslerini temizle
        test_lessons = Lesson.objects.filter(
            date=test_date,
            student__in=[student1, student2]
        )
        
        if test_lessons.exists():
            self.stdout.write(f'\nTest dersleri temizleniyor... ({test_lessons.count()} ders)')
            test_lessons.delete()
            self.stdout.write(self.style.SUCCESS('✓ Test dersleri temizlendi'))
        
        self.stdout.write(self.style.SUCCESS('\nÇakışma kontrolü sistem testi tamamlandı!')) 