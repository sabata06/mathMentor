from rest_framework import serializers
from .models import Student
from .models import Assignment

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'  # Tüm alanları dahil et


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'student', 'book', 'topic', 'page', 'is_completed', 'date_added']