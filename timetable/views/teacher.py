from datetime import date, datetime
import calendar

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from accounts.decorators import teacher_required
from timetable.models import DefaultTimetable, ActualTimetable, Report
from timetable.forms import ActualTimetableForm, ReportSubmitForm
from timetable.utils import get_monthly_weeks
from timetable.models import RedDay
def is_red_day(date_obj):
    return RedDay.objects.filter(date=date_obj).exists()
decorators = [login_required, teacher_required]


# =========================
# WIZARD VIEW (MAIN PAGE)
# =========================
class TeacherWizardView(View):
    template_name = "timetable/teacher/wizard.html"

    def get(self, request, year=None, month=None):

        today = date.today()
        year = year or today.year
        month = month or today.month

        # -------------------------
        # DEFAULT RULES (WEEKLY)
        # -------------------------
        defaults = DefaultTimetable.objects.filter(
            teacher=request.user,
            is_active=True
        )

        # Detect weekday system (0–6 or 1–7)
        USE_ISO = defaults.exists() and defaults.first().day_of_week == 1

        rules_by_day = {}
        for r in defaults:
            rules_by_day.setdefault(r.day_of_week, []).append(r)

        # -------------------------
        # ACTUAL OVERRIDES (PER DATE)
        # -------------------------
        actual = ActualTimetable.objects.filter(
            teacher=request.user,
            date__year=year,
            date__month=month
        )

        actual_map = {
            (a.date, a.slot_number): a for a in actual
        }

        # -------------------------
        # CALENDAR
        # -------------------------
        cal = calendar.Calendar(firstweekday=0)
        month_weeks = cal.monthdatescalendar(year, month)

        wizard_data = []

        for i, week in enumerate(month_weeks):
            week_days = []

            for day_date in week:

                weekday = day_date.weekday()
                if USE_ISO:
                    weekday += 1

                rules = rules_by_day.get(weekday, [])

                day_slots = []

                for rule in rules:
                    override = actual_map.get((day_date, rule.slot_number))

                    day_slots.append({
                        "default_id": rule.id,  # ALWAYS preserved
                        "slot_number": rule.slot_number,

                        "subject": override.subject if override else rule.subject,
                        "room": override.room if override else rule.room,
                        "group": override.group if override else rule.group,
                        "time_slot": rule.time_slot,
                        "status": override.status if override else "default",
                        "editable": True
                    })

                week_days.append({
                    "date": day_date,
                    "weekday_name": day_date.strftime("%A"),
                    "slots": day_slots,
                    "is_current_month": day_date.month == month
                })

            wizard_data.append({
                "number": i + 1,
                "days": week_days
            })
        print("RULE:", rule.id)
        return render(request, self.template_name, {
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "wizard_data": wizard_data,
        })


# =========================
# QUICK CONFIRM (WIZARD)
# =========================
@method_decorator(decorators, name="dispatch")
class LessonQuickConfirmView(View):

    def post(self, request, default_id, date_str):

        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        default = get_object_or_404(DefaultTimetable, pk=default_id, teacher=request.user)
        if is_red_day(slot_date):
            return JsonResponse({
                "success": False,
                "message": "Cannot schedule lessons on a holiday"
            })
        if is_red_day(slot_date):
            return JsonResponse({
                "success": False,
                "message": "Editing disabled on holidays"
            }, status=400)

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
                'lesson_type': default.lesson_type,  # ✅ HERE
                'status': 'confirmed',
                'filled_at': timezone.now()
            }
        )
        print("DATE:", date_str)
        print("DEFAULT_ID:", default_id)
        print("FOUND DEFAULT:", default)
        return JsonResponse({'status': 'success', 'new_status': 'confirmed'})

# =========================
# EDIT LESSON
# =========================
@method_decorator(decorators, name="dispatch")
class LessonEditView(View):
    def get(self, request, default_id, date_str):
        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        default = get_object_or_404(
            DefaultTimetable,
            pk=default_id,
            teacher=request.user
        )

        actual = ActualTimetable.objects.filter(
            teacher=request.user,
            date=slot_date,
            slot_number=default.slot_number
        ).first()

        form = ActualTimetableForm(instance=actual)

        return render(request, "timetable/teacher/edit_slot.html", {
            "form": form,
            "default": default,
            "actual": actual,
            "date": slot_date
        })
    def post(self, request, default_id, date_str):

        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        default = get_object_or_404(
            DefaultTimetable,
            pk=default_id,
            teacher=request.user
        )

        actual, _ = ActualTimetable.objects.get_or_create(
            teacher=request.user,
            date=slot_date,
            slot_number=default.slot_number,
            defaults={
                "default_entry": default,
                "subject": default.subject
            }
        )

        form = ActualTimetableForm(request.POST, instance=actual)

        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.status = "edited"
            lesson.filled_at = timezone.now()
            lesson.save()

            return JsonResponse({
                "success": True,
                "status": "edited"
            })

        return JsonResponse({"success": False, "errors": form.errors}, status=400)


# =========================
# BULK WEEK CONFIRM
# =========================
@method_decorator(decorators, name="dispatch")
class BulkConfirmWeekView(View):

    def post(self, request, year, month, week_num):

        week_dates = get_monthly_weeks(year, month)[week_num - 1]

        updated = 0

        for day_date in week_dates:
            if is_red_day(day_date):
                continue
            defaults = DefaultTimetable.objects.filter(
                teacher=request.user,
                day_of_week=day_date.weekday() + 1,
                is_active=True
            )

            for d in defaults:

                obj, created = ActualTimetable.objects.get_or_create(
                    teacher=request.user,
                    date=day_date,
                    slot_number=d.slot_number,
                    defaults={
                        "default_entry": d,
                        "subject": d.subject,
                        "room": d.room,
                        'lesson_type': d.lesson_type,
                        "group": d.group,
                        "time_slot": d.time_slot,
                        "status": "confirmed",
                        "filled_at": timezone.now()
                    }
                )

                if not created and obj.status == "pending":
                    obj.status = "confirmed"
                    obj.save()

                updated += 1

        return JsonResponse({
            "success": True,
            "updated": updated
        })


# =========================
# FINAL REPORT SUBMIT
# =========================
@method_decorator(decorators, name="dispatch")
class FinalizeMonthlyReportView(View):

    def post(self, request, year, month):

        weeks = get_monthly_weeks(year, month)
        first_day = weeks[0][0]
        last_day = weeks[-1][-1]

        pending = ActualTimetable.objects.filter(
            teacher=request.user,
            date__range=[first_day, last_day],
            status="pending"
        ).exists()

        if pending:
            return JsonResponse({
                "success": False,
                "message": "Confirm all lessons first"
            })

        form = ReportSubmitForm(request.POST)

        if form.is_valid():

            entries = ActualTimetable.objects.filter(
                teacher=request.user,
                date__range=[first_day, last_day],
                status__in=["confirmed", "edited"]
            )

            report = Report.objects.create(
                teacher=request.user,
                dekan=form.cleaned_data["dekan"],
                week_start=first_day,
                week_end=last_day,
                status="submitted"
            )

            report.entries.set(entries)

            return JsonResponse({"success": True})

        return JsonResponse({"success": False})