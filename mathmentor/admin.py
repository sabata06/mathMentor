from django.contrib import admin
from .models import Student, Assignment, Schedule, Lesson, Notification
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'surname', 'parent_name', 'parent_contact', 'debt_status', 'lesson_fee', 'last_lesson_date']
    list_filter = ['created_at', 'last_lesson_date']
    search_fields = ['name', 'surname', 'parent_name', 'parent_contact']
    readonly_fields = ['assignment_completion_percentage', 'total_lessons_count', 'total_earned', 'pending_payments']
    
    fieldsets = (
        ('Öğrenci Bilgileri', {
            'fields': ('name', 'surname')
        }),
        ('Veli Bilgileri', {
            'fields': ('parent_name', 'parent_contact')
        }),
        ('Ders Bilgileri', {
            'fields': ('lesson_fee', 'last_topic', 'book_progress', 'last_lesson_date', 'notes')
        }),
        ('Mali Durum', {
            'fields': ('debt_status',)
        }),
        ('İstatistikler', {
            'fields': ('assignment_completion_percentage', 'total_lessons_count', 'total_earned', 'pending_payments'),
            'classes': ('collapse',)
        })
    )

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'topic', 'book', 'page', 'is_completed', 'due_date', 'date_added']
    list_filter = ['is_completed', 'due_date', 'date_added']
    search_fields = ['student__name', 'student__surname', 'topic', 'book']
    autocomplete_fields = ['student']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['student', 'day_of_week', 'start_time', 'end_time', 'lesson_type', 'is_active']
    list_filter = ['day_of_week', 'lesson_type', 'is_active']
    search_fields = ['student__name', 'student__surname']
    autocomplete_fields = ['student']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'start_time', 'end_time', 'lesson_type', 'status', 'payment_status', 'lesson_fee']
    list_filter = ['status', 'payment_status', 'lesson_type', 'date']
    search_fields = ['student__name', 'student__surname', 'topic_covered']
    autocomplete_fields = ['student', 'schedule']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Ders Bilgileri', {
            'fields': ('student', 'schedule', 'date', 'start_time', 'end_time', 'lesson_type')
        }),
        ('Durum', {
            'fields': ('status', 'payment_status', 'lesson_fee')
        }),
        ('İçerik', {
            'fields': ('topic_covered', 'notes')
        }),
        ('İptal Bilgisi', {
            'fields': ('cancel_reason',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'schedule')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'notification_type', 'is_read', 'is_sent', 'send_at', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_sent', 'created_at']
    search_fields = ['title', 'message', 'student__name', 'student__surname']
    autocomplete_fields = ['student', 'lesson']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'lesson')

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('date_joined',)
    list_filter = ('is_staff', 'is_active', 'is_superuser')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )