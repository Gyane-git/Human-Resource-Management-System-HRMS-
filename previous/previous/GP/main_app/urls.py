"""office_ops URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views, ceo_views, manager_views, employee_views
from .EditSalaryView import EditSalaryView
from .decorators import ceo_required, employee_required

urlpatterns = [
    path("", views.login_page, name='login_page'),
    path("get_attendance", views.get_attendance, name='get_attendance'),
    path("firebase-messaging-sw.js", views.showFirebaseJS, name='showFirebaseJS'),
    path("doLogin/", views.doLogin, name='user_login'),
    path("logout_user/", views.logout_user, name='user_logout'),
    path("admin/home/", ceo_views.admin_home, name='admin_home'),
    path("manager/add", ceo_views.add_manager, name='add_manager'),
    path("division/add", ceo_views.add_division, name='add_division'),
    path("send_employee_notification/", ceo_views.send_employee_notification,
         name='send_employee_notification'),
    path("send_manager_notification/", ceo_views.send_manager_notification,
         name='send_manager_notification'),
    path("admin_notify_employee", ceo_views.admin_notify_employee,
         name='admin_notify_employee'),
    path("admin_notify_manager", ceo_views.admin_notify_manager,
         name='admin_notify_manager'),
    path("admin_view_profile", ceo_views.admin_view_profile,
         name='admin_view_profile'),
    path("check_email_availability", ceo_views.check_email_availability,
         name="check_email_availability"),
    path("employee/view/feedback/", ceo_views.employee_feedback_message,
         name="employee_feedback_message",),
    path("manager/view/feedback/", ceo_views.manager_feedback_message,
         name="manager_feedback_message",),
    path("employee/view/leave/", ceo_views.view_employee_leave,
         name="view_employee_leave",),
    path("manager/view/leave/", ceo_views.view_manager_leave, name="view_manager_leave",),
    path("attendance/view/", ceo_views.admin_view_attendance,
         name="admin_view_attendance",),
    path("attendance/update/", ceo_views.admin_update_attendance,
         name="admin_update_attendance"),
    path("attendance/fetch/", ceo_views.get_admin_attendance,
         name='get_admin_attendance'),
    path("get_manager_attendance/", ceo_views.get_manager_attendance,
         name='get_manager_attendance'),
    path("update_manager_attendance/", ceo_views.update_manager_attendance,
         name='update_manager_attendance'),
    path("manager_attendance/take/", ceo_views.admin_take_manager_attendance,
         name="admin_take_manager_attendance"),
    path("manager_attendance/view/", ceo_views.admin_view_manager_attendance,
         name="admin_view_manager_attendance"),
    path("view_manager_attendance_data/", ceo_views.view_manager_attendance_data,
         name="view_manager_attendance_data"),
    path("get_managers/", ceo_views.get_managers,
         name="get_managers"),
    path("save_manager_attendance/", ceo_views.save_manager_attendance,
         name="save_manager_attendance"),
    path("employee/add/", ceo_views.add_employee, name='add_employee'),
    path("department/add/", ceo_views.add_department, name='add_department'),
    path("manager/manage/", ceo_views.manage_manager, name='manage_manager'),
    path("employee/manage/", ceo_views.manage_employee, name='manage_employee'),
    path("division/manage/", ceo_views.manage_division, name='manage_division'),
    path("department/manage/", ceo_views.manage_department, name='manage_department'),
    path("manager/edit/<int:manager_id>", ceo_views.edit_manager, name='edit_manager'),
    path("manager/delete/<int:manager_id>",
         ceo_views.delete_manager, name='delete_manager'),

    path("division/delete/<int:division_id>",
         ceo_views.delete_division, name='delete_division'),

    path("department/delete/<int:department_id>",
         ceo_views.delete_department, name='delete_department'),

    path("employee/delete/<int:employee_id>",
         ceo_views.delete_employee, name='delete_employee'),
    path("employee/edit/<int:employee_id>",
         ceo_views.edit_employee, name='edit_employee'),
    path("division/edit/<int:division_id>",
         ceo_views.edit_division, name='edit_division'),
    path("department/edit/<int:department_id>",
         ceo_views.edit_department, name='edit_department'),
    path("admin/manager_leave/view/", ceo_views.view_manager_leave, name="view_manager_leave"),
    path("admin/employee_leave/view/", ceo_views.view_employee_leave, name="view_employee_leave"),

    path('ceo/rank-report/', 
         login_required(ceo_required(views.ceo_rank_report)), 
         name='ceo_rank_report'),
    


    # Manager
    path("manager/home/", manager_views.manager_home, name='manager_home'),
    path("manager/apply/leave/", manager_views.manager_apply_leave,
         name='manager_apply_leave'),
    path("manager/feedback/", manager_views.manager_feedback, name='manager_feedback'),
    path("manager/view/profile/", manager_views.manager_view_profile,
         name='manager_view_profile'),
    path("manager/attendance/take/", manager_views.manager_take_attendance,
         name='manager_take_attendance'),
    path("manager/attendance/update/", manager_views.manager_update_attendance,
         name='manager_update_attendance'),
    path("manager/get_employees/", manager_views.get_employees, name='get_employees'),
    path("manager/get-employee-stats/", manager_views.get_employee_stats, name='get_employee_stats'),
    path("manager/get-employee-leave-stats/", manager_views.get_employee_leave_stats, name='get_employee_leave_stats'),
    path("manager/attendance/fetch/", manager_views.get_employee_attendance,
         name='get_employee_attendance'),
    path("manager/attendance/save/",
         manager_views.save_attendance, name='save_attendance'),
    path("manager/attendance/update/",
         manager_views.update_attendance, name='update_attendance'),
    path("manager/fcmtoken/", manager_views.manager_fcmtoken, name='manager_fcmtoken'),
    path("manager/view/notification/", manager_views.manager_view_notification,
         name="manager_view_notification"),
    path("manager/view/attendance/", manager_views.manager_view_attendance,
         name="manager_view_attendance"),
    path("manager/salary/add/", manager_views.manager_add_salary, name='manager_add_salary'),
    path("manager/salary/edit/", EditSalaryView.as_view(),
         name='edit_employee_salary'),
    path('manager/salary/fetch/', manager_views.fetch_employee_salary,
         name='fetch_employee_salary'),
    path("manager/salary/save/", manager_views.save_salary, name='save_salary'),
    path("manager/salary/update-status/", manager_views.update_salary_status, name='update_salary_status'),
    path("manager/salary/delete/", manager_views.delete_salary, name='delete_salary'),
    path("manager/task/assign/", manager_views.manager_assign_task, name='manager_assign_task'),
    path("manager/task/view/", manager_views.manager_view_tasks, name='manager_view_tasks'),
    path("manager/task/update_rating/", manager_views.update_task_rating, name="update_task_rating"),
    
    # Employee
    path("employee/home/", employee_views.employee_home, name='employee_home'),
    path("employee/view/attendance/", employee_views.employee_view_attendance,
         name='employee_view_attendance'),
    path("employee/apply/leave/", employee_views.employee_apply_leave,
         name='employee_apply_leave'),
    path("employee/feedback/", employee_views.employee_feedback,
         name='employee_feedback'),
    path("employee/view/profile/", employee_views.employee_view_profile,
         name='employee_view_profile'),
    path("employee/fcmtoken/", employee_views.employee_fcmtoken,
         name='employee_fcmtoken'),
    path("employee/view/notification/", employee_views.employee_view_notification,
         name="employee_view_notification"),
    path('employee/view/salary/', employee_views.employee_view_salary,
         name='employee_view_salary'),
    path("employee/tasks/", employee_views.employee_view_tasks, name='employee_view_tasks'),
    path("employee/task/count/", employee_views.employee_task_count, name="employee_task_count"),
    path("employee/task/update_status/", employee_views.update_task_status, name="update_task_status"),
    path("employee/task/upload_file/", employee_views.upload_task_file, name="upload_task_file"),

    path('employee/rank-report/', 
         login_required(employee_required(views.employee_rank_report)), 
         name='employee_rank_report'),

]
