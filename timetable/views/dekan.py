from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Count, Q

from accounts.decorators import dekan_required
from timetable.models import Report
from timetable.forms import ReportReviewForm
from timetable.utils import (
    get_week_by_number,
    get_week_count,
    get_current_week_number,
    get_week_schedule,
    get_month_summary,
)

User       = get_user_model()
decorators = [login_required, dekan_required]


# ─────────────────────────────────────────────
# Dashboard (FIXED)
# ─────────────────────────────────────────────
@method_decorator(decorators, name='dispatch')
class DekanDashboardView(View):
    template_name = 'timetable/dekan/dashboard.html'

    def get(self, request):
        from calendar import monthrange
        from timetable.models import ActualTimetable

        today = date.today()
        year = today.year
        month = today.month

        reports = Report.objects.filter(dekan=request.user)

        stats = {
            'total': reports.count(),
            'pending': reports.filter(status='submitted').count(),
            'approved': reports.filter(status='approved').count(),
            'rejected': reports.filter(status='rejected').count(),
        }

        pending_reports = (
            reports.filter(status='submitted')
            .select_related('teacher')
            .order_by('-submitted_at')[:5]
        )

        teachers = (
            User.objects.filter(role='teacher')
            .annotate(
                total_reports=Count('reports'),
                pending_reports=Count(
                    'reports',
                    filter=Q(reports__status='submitted')
                ),
            )
        )

        # ✅ CREATE days FIRST
        total_days = monthrange(year, month)[1]
        days = list(range(1, total_days + 1))

        # ✅ BUILD MATRIX
        matrix = []

        for teacher in teachers:
            row = {
                'name': teacher.get_full_name() or teacher.username,
                'days': []
            }

            for d in days:
                current_date = date(year, month, d)

                entries = ActualTimetable.objects.filter(
                    teacher=teacher,
                    date=current_date
                )

                if entries.exists() and entries.filter(status='confirmed').count() == entries.count():
                    row['days'].append('confirmed')
                else:
                    row['days'].append('not')

            matrix.append(row)

        return render(request, self.template_name, {
            'stats': stats,
            'pending_reports': pending_reports,
            'teachers': teachers,

            # ✅ grid
            'matrix': matrix,
            'days': days,

            # context
            'year': year,
            'month': month,
            'week': get_current_week_number(year, month),
        })

# ─────────────────────────────────────────────
# Report detail — read-only timetable view
# ─────────────────────────────────────────────

@method_decorator(decorators, name='dispatch')
class ReportDetailView(View):
    template_name = 'timetable/dekan/report_detail.html'

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk, dekan=request.user)

        entries = (
            report.entries
                .order_by('date', 'slot_number')
        )

        # Group entries by date for the grid view
        days = {}
        for entry in entries:
            days.setdefault(entry.date, []).append(entry)

        review_form = ReportReviewForm()

        return render(request, self.template_name, {
            'report':      report,
            'days':        days,
            'review_form': review_form,
        })

# ─────────────────────────────────────────────
# Teachers list
# ─────────────────────────────────────────────

@method_decorator(decorators, name='dispatch')
class TeacherListView(View):
    template_name = 'timetable/dekan/teacher_list.html'

    def get(self, request):
        teachers = (
            User.objects
                .filter(role='teacher', is_active=True)
                .annotate(
                    total_reports   = Count('reports'),
                    pending_reports = Count(
                        'reports',
                        filter=Q(reports__status='submitted',
                                reports__dekan=request.user)
                    ),
                )
                .order_by('last_name', 'first_name')
        )

        today = date.today()

        return render(request, self.template_name, {
            'teachers': teachers,
            'year':     today.year,
            'month':    today.month,
            'week':     get_current_week_number(today.year, today.month),
        })


# ─────────────────────────────────────────────
# Read-only schedule for a specific teacher
# ─────────────────────────────────────────────

@method_decorator(decorators, name='dispatch')
class TeacherScheduleView(View):
    template_name = 'timetable/dekan/teacher_schedule.html'

    def get(self, request, teacher_id, year, month, week):
        teacher     = get_object_or_404(User, pk=teacher_id, role='teacher')
        total_weeks = get_week_count(year, month)
        week        = max(1, min(week, total_weeks))
        week_dates  = get_week_by_number(year, month, week)

        if not week_dates:
            messages.error(request, 'Invalid week.')
            return redirect('dekan:teachers')

        schedule      = get_week_schedule(teacher, week_dates)
        month_summary = get_month_summary(teacher, year, month)

        return render(request, self.template_name, {
            'teacher':       teacher,
            'schedule':      schedule,
            'month_summary': month_summary,
            'week_number':   week,
            'total_weeks':   total_weeks,
            'year':          year,
            'month':         month,
            'month_name':    date(year, month, 1).strftime('%B'),
            'prev_week':     week - 1 if week > 1 else None,
            'next_week':     week + 1 if week < total_weeks else None,
        })

import openpyxl
from django.http import HttpResponse
from timetable.models import ActualTimetable

def export_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly Report"

    ws.append(["Teacher", "Day", "Status"])

    entries = ActualTimetable.objects.all()

    for e in entries:
        ws.append([
            str(e.teacher),
            e.date.strftime("%Y-%m-%d"),
            e.status
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=report.xlsx'

    wb.save(response)
    return response 