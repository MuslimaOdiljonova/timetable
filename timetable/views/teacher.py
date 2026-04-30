from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from accounts.decorators import teacher_required
from timetable.models import DefaultTimetable, ActualTimetable, Report
from timetable.forms import ActualTimetableForm, ReportSubmitForm
from timetable.utils import (
    get_monthly_weeks, get_week_by_number, get_week_count, 
    get_current_week_number, get_week_schedule
)

decorators = [login_required, teacher_required]

from django.shortcuts import render, redirect
from django.views import View
from django.db import connection
from datetime import date, timedelta
import calendar

from django.shortcuts import render
from django.views import View
from django.db import connection
from datetime import date, timedelta
import calendar

class TeacherWizardView(View):
    template_name = 'timetable/teacher/wizard.html'

    def get(self, request, year=None, month=None):
        today = date.today()
        year = year or today.year
        month = month or today.month
        
        # 1. SQL orqali default timetableni fetch qilish
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, day_of_week, slot_number, subject, room, `group`, time_slot 
                FROM timetable_defaulttimetable 
                WHERE teacher_id = %s AND is_active = 1
            """, [request.user.id])
            
            # Fetchall va lug'atga o'tkazish
            columns = [col[0] for col in cursor.description]
            defaults = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 2. Oyning barcha haftalarini va sanalarini hisoblash
        cal = calendar.Calendar(firstweekday=0)
        month_weeks = cal.monthdatescalendar(year, month)
        
        wizard_data = []
        for i, week in enumerate(month_weeks):
            week_days = []
            for day_date in week:
                # Faqat dushanbadan shanbagacha (0-5) darslarni ko'rsatish
                day_num = day_date.weekday()
                day_slots = [s for s in defaults if s['day_of_week'] == day_num]
                
                week_days.append({
                    'date': day_date,
                    'weekday_name': day_date.strftime('%A'),
                    'slots': day_slots,
                    'is_current_month': day_date.month == month
                })
            
            wizard_data.append({
                'number': i + 1,
                'days': week_days
            })

        context = {
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'wizard_data': wizard_data,
        }
        return render(request, self.template_name, context)


@method_decorator(decorators, name='dispatch')
class LessonQuickConfirmView(View):
    """
    Bitta darsni tezkor tasdiqlash (Green Line).
    """
    def post(self, request, default_id, date_str):
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        default = get_object_or_404(DefaultTimetable, pk=default_id, teacher=request.user)

        actual, created = ActualTimetable.objects.update_or_create(
            teacher=request.user,
            date=slot_date,
            slot_number=default.slot_number,
            defaults={
                'default_entry': default,
                'subject': default.subject,
                'time_slot': default.time_slot,
                'group': default.group,
                'room': default.room,
                'status': 'confirmed', # Tezkor tasdiq yashil chiziq beradi
                'filled_at': timezone.now()
            }
        )
        return JsonResponse({'status': 'success', 'new_status': 'confirmed'})

@method_decorator(decorators, name='dispatch')
class LessonEditView(View):
    """
    Darsni tahrirlash (Blue Line).
    Tahrirlangan darslar keyinchalik 'confirmed' statusiga o'zgarmaydi.
    """
    def post(self, request, default_id, date_str):
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        default = get_object_or_404(DefaultTimetable, pk=default_id, teacher=request.user)
        
        actual, _ = ActualTimetable.objects.get_or_create(
            teacher=request.user, date=slot_date, slot_number=default.slot_number,
            defaults={'default_entry': default, 'subject': default.subject}
        )
        
        form = ActualTimetableForm(request.POST, instance=actual)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.status = 'edited' # Tahrirlangan ko'k chiziq beradi
            lesson.filled_at = timezone.now()
            lesson.save()
            return JsonResponse({'status': 'success', 'new_status': 'edited'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@method_decorator(decorators, name='dispatch')
class BulkConfirmWeekView(View):
    """
    Butun haftani tasdiqlash.
    Faqat 'pending' holatidagilarni 'confirmed' qiladi.
    Avvaldan 'edited' (ko'k) bo'lganlarga tegmaydi.
    """
    def post(self, request, year, month, week_num):
        week_dates = get_week_by_number(year, month, week_num)
        
        updated_count = 0
        for day_date in week_dates:
            defaults = DefaultTimetable.objects.filter(
                teacher=request.user, 
                day_of_week=day_date.weekday() + 1, 
                is_active=True
            )
            
            for d in defaults:
                # Agar dars hali yaratilmagan bo'lsa yoki pending bo'lsa
                actual, created = ActualTimetable.objects.get_or_create(
                    teacher=request.user,
                    date=day_date,
                    slot_number=d.slot_number,
                    defaults={
                        'default_entry': d,
                        'subject': d.subject,
                        'status': 'confirmed',
                        'filled_at': timezone.now()
                    }
                )
                
                # Agar dars avvaldan bor bo'lsa va faqat pending bo'lsa tasdiqlaymiz
                if not created and actual.status == 'pending':
                    actual.status = 'confirmed'
                    actual.save()
                    updated_count += 1
                elif created:
                    updated_count += 1

        return JsonResponse({'status': 'success', 'updated': updated_count})

@method_decorator(decorators, name='dispatch')
class FinalizeMonthlyReportView(View):
    """
    Wizard yakunida oylik hisobotni dekanga yuborish.
    """
    def post(self, request, year, month):
        weeks = get_monthly_weeks(year, month)
        first_day = weeks[0][0]
        last_day = weeks[-1][-1]

        # Tekshirish: Hamma darslar tasdiqlanganmi?
        pending_exists = ActualTimetable.objects.filter(
            teacher=request.user,
            date__range=[first_day, last_day],
            status='pending'
        ).exists()

        if pending_exists:
            messages.error(request, "Hisobot yuborishdan oldin barcha darslarni tasdiqlashingiz kerak.")
            return redirect('teacher:wizard', year=year, month=month)

        form = ReportSubmitForm(request.POST)
        if form.is_valid():
            entries = ActualTimetable.objects.filter(
                teacher=request.user,
                date__range=[first_day, last_day],
                status__in=['confirmed', 'edited']
            )
            
            report = Report.objects.create(
                teacher=request.user,
                dekan=form.cleaned_data['dekan'],
                week_start=first_day,
                week_end=last_day,
                status='submitted'
            )
            report.entries.set(entries)
            
            messages.success(request, "Oylik hisobot dekanga muvaffaqiyatli yuborildi.")
            return redirect('teacher:report_list')
        
        return redirect('teacher:wizard', year=year, month=month)