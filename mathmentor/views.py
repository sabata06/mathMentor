from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Student
from .serializers import StudentSerializer
from .models import Assignment
from .serializers import AssignmentSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]  # API'ye erişim için JWT doğrulaması gerekli

# Create your views here.
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        # Query parametre ile filtreleme yap
        student_id = self.request.query_params.get('student_id')
        if student_id:
            return self.queryset.filter(student_id=student_id)
        return self.queryset
