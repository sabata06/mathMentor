from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.db.models import Q

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username


class Student(models.Model):
    name = models.CharField(max_length=100)  # Öğrenci adı
    surname = models.CharField(max_length=100)  # Öğrenci soyadı
    parent_name = models.CharField(max_length=100)  # Veli adı
    parent_contact = models.CharField(max_length=15)  # Veli telefon numarası
    debt_status = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Borç durumu
    lesson_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)  # Ders ücreti
    last_topic = models.CharField(max_length=255, blank=True, null=True)  # Son işlenen konu
    book_progress = models.CharField(max_length=255, blank=True, null=True)  # Kitap ilerleme durumu
    last_lesson_date = models.DateField(blank=True, null=True)  # Son ders tarihi
    notes = models.TextField(blank=True, null=True)  # Öğrenci notları
    created_at = models.DateTimeField(auto_now_add=True)  # Kayıt tarihi

    @property
    def assignment_completion_percentage(self):
        total_assignments = self.assignments.count()
        completed_assignments = self.assignments.filter(is_completed=True).count()
        if total_assignments == 0:
            return 0
        return (completed_assignments / total_assignments) * 100

    @property
    def total_lessons_count(self):
        return self.lessons.filter(status='completed').count()

    @property
    def total_earned(self):
        return self.lessons.filter(status='completed', payment_status='paid').aggregate(
            total=models.Sum('lesson_fee'))['total'] or 0

    @property
    def pending_payments(self):
        return self.lessons.filter(status='completed', payment_status='pending').aggregate(
            total=models.Sum('lesson_fee'))['total'] or 0

    def __str__(self):
        return f"{self.name} {self.surname}"


class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Pazartesi'),
        ('tuesday', 'Salı'),
        ('wednesday', 'Çarşamba'),
        ('thursday', 'Perşembe'),
        ('friday', 'Cuma'),
        ('saturday', 'Cumartesi'),
        ('sunday', 'Pazar'),
    ]
    
    LESSON_TYPE_CHOICES = [
        ('online', 'Online'),
        ('physical', 'Yüz Yüze'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, default='physical')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.student.name} - {self.get_day_of_week_display()} {self.start_time}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Yeni schedule oluşturulduğunda periyodik dersler oluştur
        if is_new and self.is_active:
            self.create_recurring_lessons()
    
    def create_recurring_lessons(self, months_ahead=3):
        """
        Schedule'a göre periyodik dersler oluşturur
        months_ahead: kaç ay ileriye dersler oluşturulacak
        """
        day_mapping = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6,
        }
        
        target_weekday = day_mapping[self.day_of_week]
        
        # Bugünden başlayarak ilk ders gününü bul
        today = date.today()
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:  # Bugün geçti, gelecek haftayı al
            days_ahead += 7
        
        first_lesson_date = today + timedelta(days=days_ahead)
        end_date = today + timedelta(days=30 * months_ahead)  # 3 ay sonra
        
        current_date = first_lesson_date
        lessons_created = 0
        
        while current_date <= end_date:
            # Bu tarihte zaten ders var mı kontrol et
            existing_lesson = Lesson.objects.filter(
                student=self.student,
                date=current_date,
                start_time=self.start_time
            ).exists()
            
            if not existing_lesson:
                # Çakışma kontrolü yap
                has_conflict, conflicting_lesson = Lesson.check_schedule_conflict(
                    current_date, self.start_time, self.end_time
                )
                
                if not has_conflict:
                    # Ders ücreti öğrencinin varsayılan ücretinden al
                    lesson_fee = self.student.lesson_fee or 0
                    
                    Lesson.objects.create(
                        student=self.student,
                        schedule=self,
                        date=current_date,
                        start_time=self.start_time,
                        end_time=self.end_time,
                        lesson_type=self.lesson_type,
                        lesson_fee=lesson_fee,
                        status='scheduled',
                        payment_status='pending'
                    )
                    lessons_created += 1
                else:
                    # Çakışma varsa log'a yaz (opsiyonel)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Çakışma nedeniyle ders oluşturulamadı: {current_date} "
                        f"{self.start_time}-{self.end_time} ({self.student.name} {self.student.surname}) "
                        f"- Çakışan ders: {conflicting_lesson.student.name} {conflicting_lesson.student.surname}"
                    )
            
            # Bir sonraki haftaya geç
            current_date += timedelta(days=7)
        
        return lessons_created


class Lesson(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Planlandı'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
        ('missed', 'Katılmadı'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('paid', 'Ödendi'),
        ('overdue', 'Vadesi Geçti'),
    ]
    
    LESSON_TYPE_CHOICES = [
        ('online', 'Online'),
        ('physical', 'Yüz Yüze'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='lessons')
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, default='physical')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='scheduled')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    lesson_fee = models.DecimalField(max_digits=8, decimal_places=2)
    topic_covered = models.CharField(max_length=255, blank=True, null=True)
    book_progress = models.CharField(max_length=255, blank=True, null=True)  # Kitap ilerleme durumu
    notes = models.TextField(blank=True, null=True)
    cancel_reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.student.name} - {self.date} {self.start_time}"

    @property
    def is_today(self):
        return self.date == timezone.now().date()

    @property
    def is_upcoming(self):
        now = timezone.now()
        lesson_datetime = datetime.combine(self.date, self.start_time)
        lesson_datetime = timezone.make_aware(lesson_datetime)
        return lesson_datetime > now

    @staticmethod
    def check_schedule_conflict(date, start_time, end_time, exclude_lesson_id=None):
        """
        Belirtilen tarih ve saat aralığında çakışma olup olmadığını kontrol eder
        Returns: (has_conflict, conflicting_lesson)
        """
        from datetime import datetime, time
        
        # Başlangıç ve bitiş zamanlarını datetime objelerine çevir
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, '%H:%M').time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, '%H:%M').time()
        
        # Aynı tarihte çakışan dersler
        conflicting_lessons = Lesson.objects.filter(
            date=date,
            status__in=['scheduled', 'completed']  # İptal edilmiş dersler hariç
        )
        
        # Güncellenecek dersi hariç tut
        if exclude_lesson_id:
            conflicting_lessons = conflicting_lessons.exclude(id=exclude_lesson_id)
        
        for lesson in conflicting_lessons:
            lesson_start = lesson.start_time
            lesson_end = lesson.end_time
            
            # Zaman çakışması kontrolü
            # Yeni ders başlangıcı mevcut ders aralığında mı?
            if lesson_start <= start_time < lesson_end:
                return True, lesson
            # Yeni ders bitişi mevcut ders aralığında mı?
            if lesson_start < end_time <= lesson_end:
                return True, lesson
            # Yeni ders mevcut dersi tamamen kapsıyor mu?
            if start_time <= lesson_start and end_time >= lesson_end:
                return True, lesson
            # Mevcut ders yeni dersi tamamen kapsıyor mu?
            if lesson_start <= start_time and lesson_end >= end_time:
                return True, lesson
        
        return False, None

    def save(self, *args, **kwargs):
        # Yeni ders oluşturulurken veya mevcut ders güncellenirken çakışma kontrolü
        if not self._state.adding or self.pk:  # Güncelleme işlemi
            exclude_id = self.pk
        else:  # Yeni ders
            exclude_id = None
            
        has_conflict, conflicting_lesson = self.check_schedule_conflict(
            self.date, 
            self.start_time, 
            self.end_time, 
            exclude_id
        )
        
        if has_conflict:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Bu tarih ve saatte çakışma var! "
                f"{conflicting_lesson.student.name} {conflicting_lesson.student.surname} "
                f"öğrencisinin {conflicting_lesson.start_time}-{conflicting_lesson.end_time} "
                f"saatleri arasında dersi bulunmaktadır."
            )
        
        super().save(*args, **kwargs)


class Assignment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignments')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    book = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    page = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_added']

    def __str__(self):
        return f"{self.student.name} {self.student.surname} - {self.topic}"

    @property
    def is_overdue(self):
        if self.due_date and not self.is_completed:
            return self.due_date < timezone.now().date()
        return False


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('lesson_reminder', 'Ders Hatırlatması'),
        ('payment_reminder', 'Ödeme Hatırlatması'),
        ('assignment_reminder', 'Ödev Hatırlatması'),
        ('general', 'Genel'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    send_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.student.name if self.student else 'Genel'}"
