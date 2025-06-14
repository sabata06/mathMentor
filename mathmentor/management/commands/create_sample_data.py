from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta, date, time
import random
from mathmentor.models import Student, Lesson, Assignment
from decimal import Decimal

class Command(BaseCommand):
    help = 'Geçmiş aylara ait gerçekçi test verisi oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=3,
            help='Kaç ay geriye gidilerek veri oluşturulacak (varsayılan: 3)'
        )
        parser.add_argument(
            '--lessons-per-student',
            type=int,
            default=20,
            help='Her öğrenci için kaç ders oluşturulacak (varsayılan: 20)'
        )

    def handle(self, *args, **options):
        months_back = options['months']
        lessons_per_student = options['lessons_per_student']
        
        self.stdout.write(
            self.style.SUCCESS(f'Geçmiş {months_back} ay için her öğrenciye {lessons_per_student} ders oluşturuluyor...')
        )

        # Mevcut öğrencileri al
        students = Student.objects.all()
        if not students.exists():
            self.stdout.write(
                self.style.ERROR('Hiç öğrenci bulunamadı! Önce öğrenci ekleyin.')
            )
            return

        # Ders konuları
        topics = [
            "Doğal Sayılar ve İşlemler",
            "Kesirler ve Ondalık Sayılar", 
            "Geometri - Açılar",
            "Cebirsel İfadeler",
            "Denklemler",
            "Üçgenler ve Özellikleri",
            "Çember ve Daire",
            "Veri Analizi",
            "Olasılık",
            "Fonksiyonlar",
            "Trigonometri",
            "Logaritma",
            "Türev",
            "İntegral",
            "Limit ve Süreklilik",
            "Analitik Geometri",
            "Kombinatorik",
            "Sayı Teorisi",
            "Matrisler",
            "Determinant"
        ]

        # Kitap ilerlemeleri
        book_progresses = [
            "Sayfa 45-52, Bölüm 3",
            "Sayfa 78-85, Konu: Kesirler",
            "Sayfa 120-128, Geometri Bölümü",
            "Sayfa 34-41, Temel İşlemler",
            "Sayfa 156-163, İleri Konular",
            "Sayfa 89-96, Problem Çözme",
            "Sayfa 201-208, Uygulama Soruları",
            "Sayfa 67-74, Teori ve Örnekler",
            "Sayfa 145-152, Karma Sorular",
            "Sayfa 23-30, Giriş Konuları"
        ]

        # Ders notları
        lesson_notes = [
            "Öğrenci konuyu çok iyi anladı, aktif katılım gösterdi",
            "Başlangıçta zorlandı ama sonra kavradı, tekrar yapması gerekiyor",
            "Mükemmel performans, ödevlerini düzenli yapıyor",
            "Dikkat dağınıklığı var, motivasyon artırılmalı",
            "Çok çalışkan, sorularını aktif olarak soruyor",
            "Matematik konularında güçlü, problem çözme yetisi gelişmiş",
            "Temel konularda eksikleri var, tekrar yapılmalı",
            "Sınav kaygısı yaşıyor, özgüven artırılmalı",
            "Pratik yapma konusunda istekli, ev ödevlerini yapıyor",
            "Konsantrasyon sorunu var, kısa molalar verilmeli"
        ]

        # Ödev açıklamaları
        assignment_descriptions = [
            "Sayfa 45-50 arası tüm sorular",
            "Kesirler konusu tekrar edilecek, sayfa 78-82",
            "Geometri problemleri, sayfa 120-125",
            "Denklem kurma soruları, sayfa 156-160",
            "Karma problemler, sayfa 89-94",
            "Test soruları çözülecek, sayfa 201-205",
            "Teori tekrarı ve örnekler, sayfa 67-72",
            "Uygulama soruları, sayfa 145-150",
            "Giriş konuları pekiştirilecek, sayfa 23-28",
            "Problem çözme teknikleri, sayfa 34-39"
        ]

        total_lessons_created = 0
        total_assignments_created = 0

        for student in students:
            self.stdout.write(f'  → {student.name} {student.surname} için dersler oluşturuluyor...')
            
            # Son 3 ay için rastgele tarihler oluştur
            end_date = date.today()
            start_date = end_date - timedelta(days=30 * months_back)
            
            lessons_created = 0
            assignments_created = 0
            
            for i in range(lessons_per_student):
                # Rastgele tarih oluştur
                random_days = random.randint(0, (end_date - start_date).days)
                lesson_date = start_date + timedelta(days=random_days)
                
                # Hafta sonu derslerini azalt
                if lesson_date.weekday() >= 5:  # Cumartesi veya Pazar
                    if random.random() > 0.3:  # %70 ihtimalle atla
                        continue
                
                # Rastgele saat oluştur (14:00 - 20:00 arası)
                hour = random.randint(14, 19)
                minute = random.choice([0, 30])
                start_time = time(hour, minute)
                end_time = time(hour + 1, minute)
                
                # Ders durumu (çoğunlukla tamamlanmış olsun)
                status_weights = [
                    ('completed', 0.85),  # %85 tamamlanmış
                    ('cancelled', 0.10),  # %10 iptal
                    ('missed', 0.05)      # %5 katılmadı
                ]
                status = random.choices(
                    [s[0] for s in status_weights],
                    weights=[s[1] for s in status_weights]
                )[0]
                
                # Ödeme durumu (tamamlanan dersler için)
                if status == 'completed':
                    payment_weights = [
                        ('paid', 0.70),     # %70 ödendi
                        ('pending', 0.25),  # %25 bekliyor
                        ('overdue', 0.05)   # %5 vadesi geçti
                    ]
                    payment_status = random.choices(
                        [p[0] for p in payment_weights],
                        weights=[p[1] for p in payment_weights]
                    )[0]
                else:
                    payment_status = 'pending'
                
                # Ders ücreti
                lesson_fee = student.lesson_fee or Decimal('150.00')
                
                # Rastgele konu ve notlar
                topic = random.choice(topics) if status == 'completed' else ""
                notes = random.choice(lesson_notes) if status == 'completed' else ""
                book_progress = random.choice(book_progresses) if status == 'completed' else ""
                
                # Dersi oluştur
                lesson = Lesson.objects.create(
                    student=student,
                    date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    lesson_type=random.choice(['physical', 'online']),
                    status=status,
                    payment_status=payment_status,
                    lesson_fee=lesson_fee,
                    topic_covered=topic,
                    book_progress=book_progress,
                    notes=notes,
                    cancel_reason="Öğrenci hasta" if status == 'cancelled' else ""
                )
                
                lessons_created += 1
                total_lessons_created += 1
                
                # Tamamlanan dersler için ödev oluştur (%60 ihtimalle)
                if status == 'completed' and random.random() < 0.6:
                    # Ödev teslim tarihi (ders tarihinden 3-7 gün sonra)
                    due_days = random.randint(3, 7)
                    due_date = lesson_date + timedelta(days=due_days)
                    
                    # Ödev tamamlanma durumu
                    is_completed = random.choice([True, False])
                    completion_date = None
                    
                    if is_completed:
                        # Teslim tarihi öncesi veya sonrası rastgele
                        completion_days = random.randint(-2, 3)  # 2 gün erken ile 3 gün geç arası
                        completion_date = due_date + timedelta(days=completion_days)
                        
                        # Geçmiş tarih kontrolü
                        if completion_date > date.today():
                            completion_date = date.today() - timedelta(days=random.randint(1, 5))
                    
                    assignment = Assignment.objects.create(
                        student=student,
                        lesson=lesson,
                        book="Matematik Ders Kitabı",
                        topic=topic,
                        page=f"Sayfa {random.randint(20, 200)}-{random.randint(201, 250)}",
                        description=random.choice(assignment_descriptions),
                        is_completed=is_completed,
                        due_date=due_date,
                        completion_date=completion_date
                    )
                    
                    assignments_created += 1
                    total_assignments_created += 1
            
            # Öğrencinin borç durumunu güncelle
            pending_amount = student.lessons.filter(
                status='completed',
                payment_status__in=['pending', 'overdue']
            ).aggregate(total=models.Sum('lesson_fee'))['total'] or Decimal('0.00')
            
            student.debt_status = pending_amount
            
            # Son ders bilgilerini güncelle
            last_lesson = student.lessons.filter(status='completed').order_by('-date').first()
            if last_lesson:
                student.last_lesson_date = last_lesson.date
                student.last_topic = last_lesson.topic_covered
                student.book_progress = last_lesson.book_progress
            
            student.save()
            
            self.stdout.write(
                f'    ✓ {lessons_created} ders, {assignments_created} ödev oluşturuldu'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Başarıyla tamamlandı!\n'
                f'📚 Toplam {total_lessons_created} ders oluşturuldu\n'
                f'📝 Toplam {total_assignments_created} ödev oluşturuldu\n'
                f'👥 {students.count()} öğrenci için veri eklendi'
            )
        )
        
        # İstatistik özeti
        completed_lessons = Lesson.objects.filter(status='completed').count()
        paid_lessons = Lesson.objects.filter(status='completed', payment_status='paid').count()
        pending_payments = Lesson.objects.filter(status='completed', payment_status='pending').count()
        completed_assignments = Assignment.objects.filter(is_completed=True).count()
        
        self.stdout.write(
            self.style.WARNING(
                f'\n📊 İSTATİSTİK ÖZETİ:\n'
                f'✅ Tamamlanan Dersler: {completed_lessons}\n'
                f'💰 Ödenen Dersler: {paid_lessons}\n'
                f'⏳ Bekleyen Ödemeler: {pending_payments}\n'
                f'📋 Tamamlanan Ödevler: {completed_assignments}\n'
                f'📋 Toplam Ödevler: {total_assignments_created}'
            )
        ) 