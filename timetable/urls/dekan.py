from django.urls import path
from timetable.views.dekan import (
    DekanDashboardView,
    ReportDetailView,
    TeacherListView,
    TeacherScheduleView, export_excel
)

app_name = 'dekan'

urlpatterns = [
    path('',
        DekanDashboardView.as_view(),
        name='dashboard'),


    path('reports/<int:pk>/',
        ReportDetailView.as_view(),
        name='report_detail'),


    # See list of teachers assigned to this dekan
    path('teachers/',
        TeacherListView.as_view(),
        name='teachers'),

    # See a specific teacher's schedule (read-only)
    path('teachers/<int:teacher_id>/schedule/<int:year>/<int:month>/<int:week>/',
        TeacherScheduleView.as_view(),
        name='teacher_schedule'),
    path('reports/export/excel/', export_excel, name='export_excel'),
]