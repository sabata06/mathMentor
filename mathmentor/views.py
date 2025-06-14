from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta, date
from .models import Student, Assignment, Schedule, Lesson, Notification
from .serializers import (
    StudentSerializer, AssignmentSerializer, ScheduleSerializer, 
    LessonSerializer, NotificationSerializer, DashboardStatsSerializer,
    WeeklyScheduleSerializer
)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Öğrenci istatistikleri"""
        student = self.get_object()
        
        # Ders istatistikleri
        total_lessons = student.lessons.count()
        completed_lessons = student.lessons.filter(status='completed').count()
        cancelled_lessons = student.lessons.filter(status='cancelled').count()
        
        # Ödeme istatistikleri
        total_earned = student.lessons.filter(
            status='completed', payment_status='paid'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        pending_payments = student.lessons.filter(
            status='completed', payment_status='pending'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        # Ödev istatistikleri
        total_assignments = student.assignments.count()
        completed_assignments = student.assignments.filter(is_completed=True).count()
        overdue_assignments = student.assignments.filter(
            is_completed=False, due_date__lt=timezone.now().date()
        ).count()
        
        stats = {
            'lesson_stats': {
                'total': total_lessons,
                'completed': completed_lessons,
                'cancelled': cancelled_lessons,
                'attendance_rate': (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            },
            'payment_stats': {
                'total_earned': total_earned,
                'pending_payments': pending_payments,
            },
            'assignment_stats': {
                'total': total_assignments,
                'completed': completed_assignments,
                'overdue': overdue_assignments,
                'completion_rate': (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
            }
        }
        
        return Response(stats)

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        queryset = self.queryset
        student_id = self.request.query_params.get('student_id')
        is_completed = self.request.query_params.get('is_completed')
        is_overdue = self.request.query_params.get('is_overdue')
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed.lower() == 'true')
        if is_overdue == 'true':
            queryset = queryset.filter(
                is_completed=False, due_date__lt=timezone.now().date()
            )
            
        return queryset

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Ödevi tamamlandı olarak işaretle"""
        assignment = self.get_object()
        assignment.is_completed = True
        assignment.completion_date = timezone.now().date()
        assignment.save()
        return Response({'status': 'completed'})

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

    def create(self, request, *args, **kwargs):
        """Yeni haftalık program oluşturma - çakışma kontrolü ile"""
        data = request.data
        
        # Schedule bilgilerini al
        student_id = data.get('student')
        day_of_week = data.get('day_of_week')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        try:
            # Saat formatlarını parse et
            if isinstance(start_time, str):
                parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
            else:
                parsed_start_time = start_time
                
            if isinstance(end_time, str):
                parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
            else:
                parsed_end_time = end_time
            
            # Aynı gün ve saatte başka öğrenci programı var mı kontrol et
            existing_schedule = Schedule.objects.filter(
                day_of_week=day_of_week,
                is_active=True
            ).exclude(
                # Zaman çakışması kontrolü
                Q(end_time__lte=parsed_start_time) | Q(start_time__gte=parsed_end_time)
            ).first()
            
            if existing_schedule:
                student = Student.objects.get(id=existing_schedule.student_id)
                return Response({
                    'error': f'Bu gün ve saatte çakışma var! {student.name} {student.surname} öğrencisinin {existing_schedule.start_time}-{existing_schedule.end_time} saatleri arasında haftalık programı bulunmaktadır.',
                    'conflicting_schedule': {
                        'id': existing_schedule.id,
                        'student_name': f'{student.name} {student.surname}',
                        'day_of_week': existing_schedule.day_of_week,
                        'start_time': existing_schedule.start_time.strftime('%H:%M'),
                        'end_time': existing_schedule.end_time.strftime('%H:%M')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Çakışma yoksa normal create işlemini yap
            return super().create(request, *args, **kwargs)
            
        except ValueError as e:
            return Response({
                'error': 'Geçersiz saat formatı',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Program oluşturulurken bir hata oluştu',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Haftalık program güncelleme - çakışma kontrolü ile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        
        # Schedule bilgilerini al
        day_of_week = data.get('day_of_week', instance.day_of_week)
        start_time = data.get('start_time', instance.start_time)
        end_time = data.get('end_time', instance.end_time)
        
        try:
            # Saat formatlarını parse et
            if isinstance(start_time, str):
                parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
            else:
                parsed_start_time = start_time
                
            if isinstance(end_time, str):
                parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
            else:
                parsed_end_time = end_time
            
            # Aynı gün ve saatte başka öğrenci programı var mı kontrol et (mevcut hariç)
            existing_schedule = Schedule.objects.filter(
                day_of_week=day_of_week,
                is_active=True
            ).exclude(
                id=instance.id
            ).exclude(
                # Zaman çakışması kontrolü
                Q(end_time__lte=parsed_start_time) | Q(start_time__gte=parsed_end_time)
            ).first()
            
            if existing_schedule:
                student = Student.objects.get(id=existing_schedule.student_id)
                return Response({
                    'error': f'Bu gün ve saatte çakışma var! {student.name} {student.surname} öğrencisinin {existing_schedule.start_time}-{existing_schedule.end_time} saatleri arasında haftalık programı bulunmaktadır.',
                    'conflicting_schedule': {
                        'id': existing_schedule.id,
                        'student_name': f'{student.name} {student.surname}',
                        'day_of_week': existing_schedule.day_of_week,
                        'start_time': existing_schedule.start_time.strftime('%H:%M'),
                        'end_time': existing_schedule.end_time.strftime('%H:%M')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Çakışma yoksa normal update işlemini yap
            return super().update(request, *args, **kwargs)
            
        except ValueError as e:
            return Response({
                'error': 'Geçersiz saat formatı',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Program güncellenirken bir hata oluştu',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        """Partial update - çakışma kontrolü ile"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.queryset.filter(is_active=True)
        student_id = self.request.query_params.get('student_id')
        day_of_week = self.request.query_params.get('day_of_week')
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)
            
        return queryset.order_by('day_of_week', 'start_time')

    @action(detail=False, methods=['get'])
    def weekly_schedule(self, request):
        """Haftalık ders programı - bugünden başlayarak 7 gün"""
        from datetime import timedelta
        today = timezone.now().date()
        
        weekly_data = []
        day_names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        
        for i in range(7):
            current_date = today + timedelta(days=i)
            day_name = day_names[current_date.weekday()]
            
            # O gün için planlanmış dersler
            lessons = Lesson.objects.filter(
                date=current_date
            ).select_related('student').order_by('start_time')
            
            weekly_data.append({
                'date': current_date.isoformat(),
                'day_name': day_name,
                'lessons': LessonSerializer(lessons, many=True).data
            })
        
        return Response(weekly_data)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def create(self, request, *args, **kwargs):
        """Yeni ders oluşturma - çakışma kontrolü ile"""
        data = request.data
        
        # Tarih ve saat bilgilerini al
        lesson_date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        try:
            # Tarih ve saat formatlarını parse et
            if isinstance(lesson_date, str):
                parsed_date = datetime.strptime(lesson_date, '%Y-%m-%d').date()
            else:
                parsed_date = lesson_date
                
            if isinstance(start_time, str):
                parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
            else:
                parsed_start_time = start_time
                
            if isinstance(end_time, str):
                parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
            else:
                parsed_end_time = end_time
            
            # Çakışma kontrolü
            has_conflict, conflicting_lesson = Lesson.check_schedule_conflict(
                parsed_date, parsed_start_time, parsed_end_time
            )
            
            if has_conflict:
                return Response({
                    'error': f'Bu tarih ve saatte çakışma var! {conflicting_lesson.student.name} {conflicting_lesson.student.surname} öğrencisinin {conflicting_lesson.start_time}-{conflicting_lesson.end_time} saatleri arasında dersi bulunmaktadır.',
                    'conflicting_lesson': {
                        'id': conflicting_lesson.id,
                        'student_name': f'{conflicting_lesson.student.name} {conflicting_lesson.student.surname}',
                        'date': conflicting_lesson.date.isoformat(),
                        'start_time': conflicting_lesson.start_time.strftime('%H:%M'),
                        'end_time': conflicting_lesson.end_time.strftime('%H:%M'),
                        'status': conflicting_lesson.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Çakışma yoksa normal create işlemini yap
            return super().create(request, *args, **kwargs)
            
        except ValueError as e:
            return Response({
                'error': 'Geçersiz tarih/saat formatı',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Ders oluşturulurken bir hata oluştu',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Ders güncelleme - çakışma kontrolü ile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        
        # Tarih ve saat bilgilerini al
        lesson_date = data.get('date', instance.date)
        start_time = data.get('start_time', instance.start_time)
        end_time = data.get('end_time', instance.end_time)
        
        try:
            # Tarih ve saat formatlarını parse et
            if isinstance(lesson_date, str):
                parsed_date = datetime.strptime(lesson_date, '%Y-%m-%d').date()
            else:
                parsed_date = lesson_date
                
            if isinstance(start_time, str):
                parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
            else:
                parsed_start_time = start_time
                
            if isinstance(end_time, str):
                parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
            else:
                parsed_end_time = end_time
            
            # Çakışma kontrolü (mevcut dersi hariç tut)
            has_conflict, conflicting_lesson = Lesson.check_schedule_conflict(
                parsed_date, parsed_start_time, parsed_end_time, instance.id
            )
            
            if has_conflict:
                return Response({
                    'error': f'Bu tarih ve saatte çakışma var! {conflicting_lesson.student.name} {conflicting_lesson.student.surname} öğrencisinin {conflicting_lesson.start_time}-{conflicting_lesson.end_time} saatleri arasında dersi bulunmaktadır.',
                    'conflicting_lesson': {
                        'id': conflicting_lesson.id,
                        'student_name': f'{conflicting_lesson.student.name} {conflicting_lesson.student.surname}',
                        'date': conflicting_lesson.date.isoformat(),
                        'start_time': conflicting_lesson.start_time.strftime('%H:%M'),
                        'end_time': conflicting_lesson.end_time.strftime('%H:%M'),
                        'status': conflicting_lesson.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Çakışma yoksa normal update işlemini yap
            return super().update(request, *args, **kwargs)
            
        except ValueError as e:
            return Response({
                'error': 'Geçersiz tarih/saat formatı',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Ders güncellenirken bir hata oluştu',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        """Partial update - çakışma kontrolü ile"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.queryset.select_related('student', 'schedule')
        
        # Filtreleme parametreleri
        student_id = self.request.query_params.get('student_id')
        status = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        today_only = self.request.query_params.get('today_only')
        upcoming_only = self.request.query_params.get('upcoming_only')
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if today_only == 'true':
            queryset = queryset.filter(date=timezone.now().date())
        if upcoming_only == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                Q(date__gt=now.date()) | 
                Q(date=now.date(), start_time__gt=now.time())
            )
            
        return queryset

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Dersi tamamlandı olarak işaretle"""
        lesson = self.get_object()
        topic_covered = request.data.get('topic_covered', '')
        notes = request.data.get('notes', '')
        
        lesson.status = 'completed'
        lesson.topic_covered = topic_covered
        lesson.notes = notes
        lesson.save()
        
        # Öğrencinin son ders tarihini güncelle
        lesson.student.last_lesson_date = lesson.date
        lesson.student.last_topic = topic_covered
        lesson.student.save()
        
        return Response({'status': 'completed'})

    @action(detail=True, methods=['post'])
    def mark_cancelled(self, request, pk=None):
        """Dersi iptal et"""
        lesson = self.get_object()
        cancel_reason = request.data.get('cancel_reason', '')
        
        lesson.status = 'cancelled'
        lesson.cancel_reason = cancel_reason
        lesson.save()
        
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Ders ücretini ödendi olarak işaretle"""
        lesson = self.get_object()
        lesson.payment_status = 'paid'
        lesson.save()
        
        return Response({'status': 'paid'})

    @action(detail=True, methods=['post'])
    def quick_complete(self, request, pk=None):
        """Hızlı ders tamamlama - kapsamlı işlem"""
        lesson = self.get_object()
        data = request.data
        
        # Ders bilgilerini güncelle
        lesson.status = 'completed'
        lesson.topic_covered = data.get('topic_covered', '')
        lesson.notes = data.get('notes', '')
        lesson.book_progress = data.get('book_progress', '')
        
        # Ödeme durumunu güncelle
        payment_received = data.get('payment_received', False)
        if payment_received:
            lesson.payment_status = 'paid'
        else:
            lesson.payment_status = 'pending'
            # Öğrencinin borcunu güncelle
            student = lesson.student
            student.debt_status = (student.debt_status or 0) + lesson.lesson_fee
            student.save()
        
        lesson.save()
        
        # Öğrencinin son ders bilgilerini güncelle
        student = lesson.student
        student.last_lesson_date = lesson.date
        student.last_topic = lesson.topic_covered
        if lesson.book_progress:
            student.book_progress = lesson.book_progress
        student.save()
        
        # Önceki ödev durumunu kontrol et
        previous_assignment_completed = data.get('previous_assignment_completed')
        if previous_assignment_completed is not None:
            # En son verilen ödevi bul
            latest_assignment = Assignment.objects.filter(
                student=student,
                is_completed=False
            ).order_by('-created_at').first()
            
            if latest_assignment:
                latest_assignment.is_completed = previous_assignment_completed
                if previous_assignment_completed:
                    latest_assignment.completion_date = timezone.now().date()
                latest_assignment.save()
        
        # Yeni ödev oluştur
        new_assignment_description = data.get('new_assignment')
        if new_assignment_description:
            Assignment.objects.create(
                student=student,
                description=new_assignment_description,
                due_date=data.get('assignment_due_date', timezone.now().date() + timedelta(days=7)),
                is_completed=False
            )
        
        # Güncellenmiş ders bilgisini döndür
        serializer = LessonSerializer(lesson)
        return Response({
            'lesson': serializer.data,
            'message': 'Ders başarıyla tamamlandı',
            'payment_status': lesson.payment_status,
            'debt_updated': not payment_received
        })

    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Bekleyen ödemeler listesi"""
        pending_lessons = Lesson.objects.filter(
            status='completed',
            payment_status__in=['pending', 'overdue']
        ).select_related('student').order_by('-date')
        
        serializer = LessonSerializer(pending_lessons, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_schedule(self, request, pk=None):
        """Ders tarih ve saatini güncelle"""
        lesson = self.get_object()
        data = request.data
        
        new_date = data.get('date')
        new_start_time = data.get('start_time')
        new_end_time = data.get('end_time')
        update_reason = data.get('update_reason', '')
        
        # Eski bilgileri kaydet
        old_date = lesson.date
        old_start_time = lesson.start_time
        old_end_time = lesson.end_time
        
        try:
            # Yeni tarih ve saatleri parse et
            if new_date:
                if isinstance(new_date, str):
                    lesson.date = datetime.strptime(new_date, '%Y-%m-%d').date()
                else:
                    lesson.date = new_date
            
            if new_start_time:
                if isinstance(new_start_time, str):
                    lesson.start_time = datetime.strptime(new_start_time, '%H:%M').time()
                else:
                    lesson.start_time = new_start_time
            
            if new_end_time:
                if isinstance(new_end_time, str):
                    lesson.end_time = datetime.strptime(new_end_time, '%H:%M').time()
                else:
                    lesson.end_time = new_end_time
            
            # Kapsamlı çakışma kontrolü (tüm öğrenciler için)
            has_conflict, conflicting_lesson = Lesson.check_schedule_conflict(
                lesson.date, lesson.start_time, lesson.end_time, lesson.id
            )
            
            if has_conflict:
                return Response({
                    'error': f'Bu tarih ve saatte çakışma var! {conflicting_lesson.student.name} {conflicting_lesson.student.surname} öğrencisinin {conflicting_lesson.start_time}-{conflicting_lesson.end_time} saatleri arasında dersi bulunmaktadır.',
                    'conflicting_lesson': {
                        'id': conflicting_lesson.id,
                        'student_name': f'{conflicting_lesson.student.name} {conflicting_lesson.student.surname}',
                        'date': conflicting_lesson.date.isoformat(),
                        'start_time': conflicting_lesson.start_time.strftime('%H:%M'),
                        'end_time': conflicting_lesson.end_time.strftime('%H:%M'),
                        'status': conflicting_lesson.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Güncelleme notunu ekle
            if update_reason:
                update_note = f"Ders zamanı güncellendi: {old_date} {old_start_time}-{old_end_time} → {lesson.date} {lesson.start_time}-{lesson.end_time}. Sebep: {update_reason}"
            else:
                update_note = f"Ders zamanı güncellendi: {old_date} {old_start_time}-{old_end_time} → {lesson.date} {lesson.start_time}-{lesson.end_time}"
            
            if lesson.notes:
                lesson.notes += f"\n\n{update_note}"
            else:
                lesson.notes = update_note
            
            lesson.save()
            
            # Bildirim oluştur
            Notification.objects.create(
                title="Ders Saati Değişti",
                message=f"{lesson.student.name} {lesson.student.surname} öğrencisinin {lesson.date} tarihli dersi güncellendi.",
                notification_type="lesson_reminder",
                student=lesson.student,
                lesson=lesson,
                send_at=timezone.now(),
                is_sent=True
            )
            
            serializer = LessonSerializer(lesson)
            return Response({
                'lesson': serializer.data,
                'message': 'Ders zamanı başarıyla güncellendi',
                'changes': {
                    'old_date': old_date.isoformat(),
                    'new_date': lesson.date.isoformat(),
                    'old_start_time': old_start_time.strftime('%H:%M'),
                    'new_start_time': lesson.start_time.strftime('%H:%M'),
                    'old_end_time': old_end_time.strftime('%H:%M'),
                    'new_end_time': lesson.end_time.strftime('%H:%M')
                }
            })
            
        except ValueError as e:
            return Response({
                'error': 'Geçersiz tarih/saat formatı',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Ders güncellenirken bir hata oluştu',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def cancel_with_reason(self, request, pk=None):
        """Dersi sebep belirterek iptal et"""
        lesson = self.get_object()
        data = request.data
        
        cancel_reason = data.get('cancel_reason', '')
        
        if not cancel_reason.strip():
            return Response({
                'error': 'İptal sebebi belirtilmelidir'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        lesson.status = 'cancelled'
        lesson.cancel_reason = cancel_reason
        lesson.payment_status = 'pending'  # İptal edilenler için ödeme durumu
        
        # İptal notunu ekle
        cancel_note = f"Ders iptal edildi. Sebep: {cancel_reason}"
        if lesson.notes:
            lesson.notes += f"\n\n{cancel_note}"
        else:
            lesson.notes = cancel_note
        
        lesson.save()
        
        # Bildirim oluştur
        Notification.objects.create(
            title="Ders İptal Edildi",
            message=f"{lesson.student.name} {lesson.student.surname} öğrencisinin {lesson.date} tarihli dersi iptal edildi.",
            notification_type="lesson_reminder",
            student=lesson.student,
            lesson=lesson,
            send_at=timezone.now(),
            is_sent=True
        )
        
        serializer = LessonSerializer(lesson)
        return Response({
            'lesson': serializer.data,
            'message': 'Ders başarıyla iptal edildi'
        })

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = self.queryset
        student_id = self.request.query_params.get('student_id')
        notification_type = self.request.query_params.get('type')
        unread_only = self.request.query_params.get('unread_only')
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        if unread_only == 'true':
            queryset = queryset.filter(is_read=False)
            
        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Bildirimi okundu olarak işaretle"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Tüm bildirimleri okundu yap"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all_read'})

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Dashboard istatistikleri"""
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        # Temel istatistikler
        total_students = Student.objects.count()
        total_lessons_today = Lesson.objects.filter(date=today).count()
        
        # Ödeme istatistikleri
        total_pending_payments = Lesson.objects.filter(
            status='completed', payment_status='pending'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        monthly_earnings = Lesson.objects.filter(
            status='completed', 
            payment_status='paid',
            date__gte=this_month
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        # Ödev istatistikleri
        total_completed_assignments = Assignment.objects.filter(is_completed=True).count()
        total_overdue_assignments = Assignment.objects.filter(
            is_completed=False, due_date__lt=today
        ).count()
        
        stats = {
            'total_students': total_students,
            'total_lessons_today': total_lessons_today,
            'total_pending_payments': total_pending_payments,
            'total_completed_assignments': total_completed_assignments,
            'total_overdue_assignments': total_overdue_assignments,
            'monthly_earnings': monthly_earnings,
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def detailed_stats(self, request):
        """Detaylı istatistikler sayfası için kapsamlı veriler"""
        today = timezone.now().date()
        this_month = today.replace(day=1)
        this_year = today.replace(month=1, day=1)
        last_month_start = (this_month - timedelta(days=1)).replace(day=1)
        last_year = today.replace(year=today.year-1, month=1, day=1)
        
        # Genel İstatistikler
        total_students = Student.objects.count()
        active_students = Student.objects.filter(
            lessons__date__gte=this_month
        ).distinct().count()
        
        # Ders İstatistikleri
        total_lessons = Lesson.objects.count()
        completed_lessons = Lesson.objects.filter(status='completed').count()
        cancelled_lessons = Lesson.objects.filter(status='cancelled').count()
        missed_lessons = Lesson.objects.filter(status='missed').count()
        
        # Bu ay ders istatistikleri
        monthly_lessons = Lesson.objects.filter(date__gte=this_month).count()
        monthly_completed = Lesson.objects.filter(
            date__gte=this_month, status='completed'
        ).count()
        
        # Geçen ay ile karşılaştırma
        last_month_lessons = Lesson.objects.filter(
            date__gte=last_month_start, date__lt=this_month
        ).count()
        lessons_growth = ((monthly_lessons - last_month_lessons) / last_month_lessons * 100) if last_month_lessons > 0 else 0
        
        # Ödeme İstatistikleri
        total_earned = Lesson.objects.filter(
            status='completed', payment_status='paid'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        monthly_earnings = Lesson.objects.filter(
            status='completed', payment_status='paid', date__gte=this_month
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        last_month_earnings = Lesson.objects.filter(
            status='completed', payment_status='paid',
            date__gte=last_month_start, date__lt=this_month
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        earnings_growth = ((monthly_earnings - last_month_earnings) / last_month_earnings * 100) if last_month_earnings > 0 else 0
        
        total_pending = Lesson.objects.filter(
            status='completed', payment_status='pending'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        overdue_payments = Lesson.objects.filter(
            status='completed', payment_status='overdue'
        ).aggregate(total=Sum('lesson_fee'))['total'] or 0
        
        # Ödev İstatistikleri
        total_assignments = Assignment.objects.count()
        completed_assignments = Assignment.objects.filter(is_completed=True).count()
        overdue_assignments = Assignment.objects.filter(
            is_completed=False, due_date__lt=today
        ).count()
        assignment_completion_rate = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        # Ders türü dağılımı
        online_lessons = Lesson.objects.filter(lesson_type='online').count()
        physical_lessons = Lesson.objects.filter(lesson_type='physical').count()
        
        # Son 12 ay aylık kazanç trendi
        monthly_earnings_trend = []
        for i in range(12):
            month_start = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            earnings = Lesson.objects.filter(
                status='completed', payment_status='paid',
                date__gte=month_start, date__lte=month_end
            ).aggregate(total=Sum('lesson_fee'))['total'] or 0
            
            lessons_count = Lesson.objects.filter(
                status='completed',
                date__gte=month_start, date__lte=month_end
            ).count()
            
            monthly_earnings_trend.insert(0, {
                'month': month_start.strftime('%m/%Y'),
                'earnings': float(earnings),
                'lessons': lessons_count
            })
        
        # Öğrenci başına performans
        student_performance = []
        for student in Student.objects.all()[:10]:  # En aktif 10 öğrenci
            student_lessons = student.lessons.filter(status='completed').count()
            student_earnings = student.lessons.filter(
                status='completed', payment_status='paid'
            ).aggregate(total=Sum('lesson_fee'))['total'] or 0
            student_pending = student.lessons.filter(
                status='completed', payment_status='pending'
            ).aggregate(total=Sum('lesson_fee'))['total'] or 0
            
            completion_rate = 0
            if student.assignments.count() > 0:
                completion_rate = (student.assignments.filter(is_completed=True).count() / 
                                 student.assignments.count() * 100)
            
            student_performance.append({
                'name': f"{student.name} {student.surname}",
                'lessons': student_lessons,
                'earnings': float(student_earnings),
                'pending': float(student_pending),
                'assignment_completion': round(completion_rate, 1)
            })
        
        # Haftalık ders dağılımı
        weekly_distribution = []
        days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        for i, day in enumerate(days):
            count = Lesson.objects.filter(date__week_day=i+2).count()  # Django week_day: 1=Sunday
            weekly_distribution.append({
                'day': day,
                'count': count
            })
        
        # En popüler ders saatleri
        popular_hours = []
        for hour in range(8, 21):  # 08:00 - 20:00 arası
            count = Lesson.objects.filter(start_time__hour=hour).count()
            if count > 0:
                popular_hours.append({
                    'hour': f"{hour:02d}:00",
                    'count': count
                })
        
        detailed_stats = {
            # Genel İstatistikler
            'general': {
                'total_students': total_students,
                'active_students': active_students,
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'completion_rate': round((completed_lessons / total_lessons * 100) if total_lessons > 0 else 0, 1),
                'cancelled_lessons': cancelled_lessons,
                'missed_lessons': missed_lessons,
                'lessons_growth': round(lessons_growth, 1)
            },
            
            # Ödeme İstatistikleri
            'payments': {
                'total_earned': float(total_earned),
                'monthly_earnings': float(monthly_earnings),
                'earnings_growth': round(earnings_growth, 1),
                'total_pending': float(total_pending),
                'overdue_payments': float(overdue_payments),
                'payment_rate': round(((total_earned / (total_earned + total_pending)) * 100) if (total_earned + total_pending) > 0 else 0, 1)
            },
            
            # Ödev İstatistikleri
            'assignments': {
                'total_assignments': total_assignments,
                'completed_assignments': completed_assignments,
                'overdue_assignments': overdue_assignments,
                'completion_rate': round(assignment_completion_rate, 1)
            },
            
            # Ders Türü Dağılımı
            'lesson_types': {
                'online': online_lessons,
                'physical': physical_lessons,
                'online_percentage': round((online_lessons / (online_lessons + physical_lessons) * 100) if (online_lessons + physical_lessons) > 0 else 0, 1)
            },
            
            # Trendler ve Analizler
            'trends': {
                'monthly_earnings': monthly_earnings_trend,
                'student_performance': student_performance,
                'weekly_distribution': weekly_distribution,
                'popular_hours': popular_hours
            }
        }
        
        return Response(detailed_stats)

    @action(detail=False, methods=['get'])
    def upcoming_lessons(self, request):
        """Yaklaşan dersler"""
        now = timezone.now()
        upcoming = Lesson.objects.filter(
            Q(date__gt=now.date()) | 
            Q(date=now.date(), start_time__gt=now.time()),
            status='scheduled'
        ).select_related('student').order_by('date', 'start_time')[:10]
        
        serializer = LessonSerializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today_schedule(self, request):
        """Bugünün ders programı"""
        today = timezone.now().date()
        today_lessons = Lesson.objects.filter(
            date=today
        ).select_related('student').order_by('start_time')
        
        serializer = LessonSerializer(today_lessons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def earnings_report(self, request):
        """Kazanç raporu - haftalık, aylık, yıllık"""
        from datetime import timedelta
        from django.db.models import Sum, Count, Q
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        # Haftalık kazanç
        weekly_earnings = Lesson.objects.filter(
            date__gte=week_start,
            date__lte=today,
            status='completed',
            payment_status='paid'
        ).aggregate(
            total=Sum('lesson_fee'),
            count=Count('id')
        )
        
        # Aylık kazanç
        monthly_earnings = Lesson.objects.filter(
            date__gte=month_start,
            date__lte=today,
            status='completed',
            payment_status='paid'
        ).aggregate(
            total=Sum('lesson_fee'),
            count=Count('id')
        )
        
        # Yıllık kazanç
        yearly_earnings = Lesson.objects.filter(
            date__gte=year_start,
            date__lte=today,
            status='completed',
            payment_status='paid'
        ).aggregate(
            total=Sum('lesson_fee'),
            count=Count('id')
        )
        
        # Bekleyen ödemeler
        pending_payments = Lesson.objects.filter(
            status='completed',
            payment_status='pending'
        ).aggregate(
            total=Sum('lesson_fee'),
            count=Count('id')
        )
        
        # Vadesi geçen ödemeler
        overdue_payments = Lesson.objects.filter(
            status='completed',
            payment_status='overdue'
        ).aggregate(
            total=Sum('lesson_fee'),
            count=Count('id')
        )
        
        return Response({
            'weekly': {
                'earnings': weekly_earnings['total'] or 0,
                'lessons_count': weekly_earnings['count'] or 0,
                'period': f"{week_start} - {today}"
            },
            'monthly': {
                'earnings': monthly_earnings['total'] or 0,
                'lessons_count': monthly_earnings['count'] or 0,
                'period': f"{month_start} - {today}"
            },
            'yearly': {
                'earnings': yearly_earnings['total'] or 0,
                'lessons_count': yearly_earnings['count'] or 0,
                'period': f"{year_start} - {today}"
            },
            'pending_payments': {
                'amount': pending_payments['total'] or 0,
                'lessons_count': pending_payments['count'] or 0
            },
            'overdue_payments': {
                'amount': overdue_payments['total'] or 0,
                'lessons_count': overdue_payments['count'] or 0
            }
        })
