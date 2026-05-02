from django.urls import path
from timetable.views.teacher import (
    TeacherWizardView,
    LessonQuickConfirmView,
    LessonEditView,
    BulkConfirmWeekView,
    FinalizeMonthlyReportView,
    # ReportListView,
    # ReportDetailView,
)

app_name = 'teacher'

urlpatterns = [
    # Asosiy landing - joriy oy uchun Wizard
    path(
        '', 
        TeacherWizardView.as_view(), 
        name='wizard_current'
    ),

    path(
        'lesson/confirm/<int:default_id>/<str:date_str>/',
        LessonQuickConfirmView.as_view(),
        name='lesson_confirm_quick'
    ),

    # AJAX: Darsni tahrirlash (Blue Line)
    path(
        "teacher/edit/<int:default_id>/<str:date_str>/",
        LessonEditView.as_view(),
        name="teacher_edit"
    ),

    # AJAX: Butun haftani tasdiqlash
    path(
        'week/confirm-bulk/<int:year>/<int:month>/<int:week_num>/',
        BulkConfirmWeekView.as_view(),
        name='confirm_week_bulk'
    ),

    # Yakuniy oylik hisobotni dekanga yuborish
    path(
        'report/finalize/<int:year>/<int:month>/',
        FinalizeMonthlyReportView.as_view(),
        name='report_finalize'
    ),
path(
    "edit/<int:default_id>/<str:date_str>/",
    LessonEditView.as_view(),
    name="lesson_edit"
),

    # # Hisobotlar ro'yxati va detali
    # path(
    #     'reports/', 
    #     ReportListView.as_view(), 
    #     name='report_list'
    # ),
    # path(
    #     'reports/<int:pk>/', 
    #     ReportDetailView.as_view(), 
    #     name='report_detail'
    # ),
]