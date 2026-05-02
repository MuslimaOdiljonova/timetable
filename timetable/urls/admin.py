from django.urls import path
from timetable.views.admin import *

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),  # 👈 ADD THIS

    path('departments/', DepartmentListView.as_view(), name='admin_departments'),
    path('departments/create/', DepartmentCreateView.as_view(), name='admin_department_create'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='admin_department_detail'),

    path('departments/<int:dept_id>/teachers/create/', TeacherCreateInDepartmentView.as_view(), name='admin_teacher_create'),
    path(
        "departments/delete/<int:pk>/",
        DepartmentDeleteView.as_view(),
        name="admin_department_delete"
    ),
    path('teachers/<int:pk>/edit/', TeacherEditView.as_view(), name='admin_teacher_edit'),
    path('teachers/<int:pk>/delete/', TeacherDeleteView.as_view(), name='admin_teacher_delete'),
    path('teachers/<int:pk>/timetable/', TeacherTimetableRedirectView.as_view(), name='teacher_timetable'),
]
urlpatterns += [
    path(
        'timetable/grid/<int:teacher_id>/',
        AdminGridView.as_view(),
        name='admin_grid'
    ),

path(
    'timetable/grid/<int:teacher_id>/save/',
    AdminGridSaveView.as_view(),
    name='admin_grid_save'
),

    path(
        'timetable/grid/<int:teacher_id>/delete/',
        AdminGridDeleteView.as_view(),
        name='admin_grid_delete'
    ),
path("teachers/slots/", SlotAdminView.as_view(), name="slot_admin"),
path('teachers/slots/<int:pk>/update/', SlotUpdateView.as_view(), name="slot_update"),
path('red-days/', RedDayListView.as_view(), name='admin_red_days'),
path('red-days/create/', RedDayCreateView.as_view(), name='admin_red_day_create'),
path('red-days/delete/<int:pk>/', RedDayDeleteView.as_view(), name='admin_red_day_delete'),

]