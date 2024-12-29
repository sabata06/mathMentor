from rest_framework import serializers
from .models import Student
from .models import Assignment

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'surname',
            'parent_name',
            'parent_contact',
            'debt_status',
            'last_topic',
            'book_progress',
            'last_lesson_date',
            'created_at',
            'assignment_completion_percentage', 
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'student', 'book', 'topic', 'page', 'is_completed', 'date_added']