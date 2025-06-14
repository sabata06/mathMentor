from rest_framework import serializers
from .models import Student, Assignment, Schedule, Lesson, Notification

class StudentSerializer(serializers.ModelSerializer):
    assignment_completion_percentage = serializers.ReadOnlyField()
    total_lessons_count = serializers.ReadOnlyField()
    total_earned = serializers.ReadOnlyField()
    pending_payments = serializers.ReadOnlyField()
    
    class Meta:
        model = Student
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_surname = serializers.CharField(source='student.surname', read_only=True)
    
    class Meta:
        model = Assignment
        fields = '__all__'

class ScheduleSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_surname = serializers.CharField(source='student.surname', read_only=True)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    lesson_type_display = serializers.CharField(source='get_lesson_type_display', read_only=True)
    
    class Meta:
        model = Schedule
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_surname = serializers.CharField(source='student.surname', read_only=True)
    parent_contact = serializers.CharField(source='student.parent_contact', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    lesson_type_display = serializers.CharField(source='get_lesson_type_display', read_only=True)
    is_today = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    
    class Meta:
        model = Lesson
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_surname = serializers.CharField(source='student.surname', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'

# Dashboard için özel serializer'lar
class DashboardStatsSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_lessons_today = serializers.IntegerField()
    total_pending_payments = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_completed_assignments = serializers.IntegerField()
    total_overdue_assignments = serializers.IntegerField()
    monthly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)

class WeeklyScheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    day_name = serializers.CharField()
    lessons = LessonSerializer(many=True)