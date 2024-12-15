from django.contrib.auth.models import AbstractUser
from django.db import models

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
    last_topic = models.CharField(max_length=255, blank=True, null=True)  # Son işlenen konu
    book_progress = models.CharField(max_length=255, blank=True, null=True)  # Kitap ilerleme durumu
    last_lesson_date = models.DateField(blank=True, null=True)  # Son ders tarihi
    created_at = models.DateTimeField(auto_now_add=True)  # Kayıt tarihi

    def __str__(self):
        return f"{self.name} {self.surname}"