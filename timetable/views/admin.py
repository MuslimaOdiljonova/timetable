from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from accounts.models import CustomUser
from timetable.models import Department
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from timetable.models import DefaultTimetable, LessonSlot

class AdminDashboardView(View):
    def get(self, request):
        return redirect("admin_departments")

class DepartmentListView(View):
    def get(self, request):
        departments = Department.objects.all()
        return render(request, "timetable/admin/departments/list.html", {
            "departments": departments
        })


class DepartmentCreateView(View):
    def get(self, request):
        return render(request, "timetable/admin/departments/create.html")

    def post(self, request):
        name = request.POST.get("name")

        Department.objects.create(name=name)

        return redirect("admin_departments")

class DepartmentDetailView(View):
    def get(self, request, pk):

        # ✅ THIS must use integer pk from URL
        department = get_object_or_404(Department, pk=pk)

        # ✅ Your DB uses VARCHAR for department → match by name
        teachers = CustomUser.objects.filter(
            department=department,  # 👈 PASS OBJECT, NOT NAME
            role="teacher"
        )

        return render(request, "timetable/admin/departments/details.html", {
            "department": department,
            "teachers": teachers
        })
class DepartmentDeleteView(View):

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        dept.delete()
        return redirect("admin_departments")

class TeacherCreateInDepartmentView(View):

    def get(self, request, dept_id):
        department = get_object_or_404(Department, id=dept_id)

        return render(request, "timetable/admin/teachers/create.html", {
            "department": department
        })

    def post(self, request, dept_id):
        department = get_object_or_404(Department, id=dept_id)

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        password = request.POST.get("password")

        CustomUser.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role="teacher",
            department=department   # ✅ AUTO ASSIGN HERE
        )

        return redirect("admin_department_detail", pk=dept_id)
class TeacherEditView(View):

    def get(self, request, pk):
        teacher = get_object_or_404(CustomUser, id=pk)

        return render(request, "timetable/admin/teachers/edit.html", {
            "teacher": teacher
        })

    def post(self, request, pk):
        teacher = get_object_or_404(CustomUser, id=pk)

        teacher.first_name = request.POST.get("first_name")
        teacher.last_name = request.POST.get("last_name")
        teacher.username = request.POST.get("username")

        new_password = request.POST.get("password")

        # reset password only if provided
        if new_password:
            teacher.password = make_password(new_password)

        teacher.save()

        return redirect("admin_department_detail", pk=teacher.department.id)
class TeacherDeleteView(View):

    def post(self, request, pk):
        teacher = get_object_or_404(CustomUser, id=pk)
        dept_id = teacher.department.id if teacher.department else None

        teacher.delete()

        if dept_id:
            return redirect("admin_department_detail", pk=dept_id)

        return redirect("admin_departments")

class TeacherTimetableRedirectView(View):
    def get(self, request, pk):
        return redirect("admin_grid", teacher_id=pk)
class AdminGridView(View):

    def get(self, request, teacher_id):
        teacher = get_object_or_404(CustomUser, pk=teacher_id)

        rules = DefaultTimetable.objects.filter(teacher=teacher)

        grid = {day: {} for day in range(7)}

        for r in rules:
            grid.setdefault(r.day_of_week, {})[r.slot_number] = {
                "id": r.id,
                "subject": r.subject,
                "room": r.room,
                "group": r.group,
                "lesson_type": r.lesson_type,
                "time_slot": r.time_slot,
            }
        print(grid)

        days = [
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),  # 👈 ADD THIS
        ]

        slots = list(LessonSlot.objects.all().order_by("number")[:8])

        # If DB has LESS than 8 → fill manually
        while len(slots) < 8:
            slots.append(type("Slot", (), {
                "number": len(slots) + 1,
                "start_time": "--",
                "end_time": "--"
            })())

        return render(request, "timetable/admin/teachers/grid_editor.html", {
            "teacher": teacher,
            "grid": grid,
            "days": days,
            "slots": slots,
        })
class AdminGridSaveView(View):

    def post(self, request, teacher_id):

        teacher = get_object_or_404(CustomUser, id=teacher_id)

        lesson_id = request.POST.get("lesson_id")

        data = {
            "teacher": teacher,
            "day_of_week": request.POST.get("day"),
            "slot_number": request.POST.get("slot"),
            "subject": request.POST.get("subject"),
            "room": request.POST.get("room"),
            "group": request.POST.get("group"),
            "lesson_type": request.POST.get("lesson_type"),
            "is_active": True,
        }
        slot = int(request.POST.get("slot"))
        slot_obj = LessonSlot.objects.filter(number=slot).first()

        if not slot_obj:
            return JsonResponse({
                "success": False,
                "error": f"Slot {slot} does not exist"
            })

        data["time_slot"] = f"{slot_obj.start_time} - {slot_obj.end_time}"
        # 🔥 FIX: validate day/slot
        if not data["day_of_week"] or not data["slot_number"]:
            return JsonResponse({
                "success": False,
                "error": "Missing day or slot"
            })

        if lesson_id:
            obj = DefaultTimetable.objects.filter(id=lesson_id, teacher=teacher).first()
            if not obj:
                return JsonResponse({"success": False, "error": "Not found"})

            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()

        else:
            obj = DefaultTimetable.objects.create(**data)

        return JsonResponse({"success": True, "id": obj.id})
class AdminGridDeleteView(View):
    def post(self, request, teacher_id):

        lesson_id = request.POST.get("lesson_id")

        DefaultTimetable.objects.filter(
            id=lesson_id,
            teacher_id=teacher_id
        ).delete()

        return JsonResponse({"success": True})
class SlotAdminView(View):
    def get(self, request):
        slots = LessonSlot.objects.all().order_by("number")
        return render(request, "admin/slots.html", {"slots": slots})
class SlotUpdateView(View):
    def post(self, request, pk):
        slot = LessonSlot.objects.get(id=pk)
        slot.start_time = request.POST.get("start_time")
        slot.end_time = request.POST.get("end_time")
        slot.save()
        return JsonResponse({"success": True})
from timetable.models import RedDay
from datetime import datetime

class RedDayListView(View):
    def get(self, request):
        red_days = RedDay.objects.all()
        return render(request, "timetable/admin/red_days/list.html", {
            "red_days": red_days
        })


class RedDayCreateView(View):
    def get(self, request):
        return render(request, "timetable/admin/red_days/create.html")

    def post(self, request):
        date = request.POST.get("date")
        reason = request.POST.get("reason")

        if date:
            RedDay.objects.create(
                date=date,
                reason=reason,
                set_by=request.user
            )

        return redirect("admin_red_days")


class RedDayDeleteView(View):
    def post(self, request, pk):
        red_day = get_object_or_404(RedDay, pk=pk)
        red_day.delete()
        return redirect("admin_red_days")