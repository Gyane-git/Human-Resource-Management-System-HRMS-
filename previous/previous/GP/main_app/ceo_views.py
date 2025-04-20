import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView

from .forms import *
from .models import *

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from .models import LeaveReportManager
from .models import LeaveReportEmployee

def admin_home(request):
    total_manager = Manager.objects.all().count()
    total_employees = Employee.objects.all().count()
    departments = Department.objects.all()
    total_department = departments.count()
    total_division = Division.objects.all().count()
    attendance_list = Attendance.objects.filter(department__in=departments)
    total_attendance = attendance_list.count()
    
    # Add counts for feedbacks and leave applications
    manager_feedback_count = FeedbackManager.objects.filter(reply="").count()
    employee_feedback_count = FeedbackEmployee.objects.filter(reply="").count()
    manager_leave_count = LeaveReportManager.objects.filter(status=0).count()
    employee_leave_count = LeaveReportEmployee.objects.filter(status=0).count()
    
    attendance_list = []
    department_list = []
    for department in departments:
        attendance_count = Attendance.objects.filter(department=department).count()
        department_list.append(department.name[:7])
        attendance_list.append(attendance_count)

    # Convert data to JSON for charts
    department_list_json = json.dumps(department_list)
    attendance_list_json = json.dumps(attendance_list)
    
    context = {
        'page_title': "Administrative Dashboard",
        'total_employees': total_employees,
        'total_manager': total_manager,
        'total_division': total_division,
        'total_department': total_department,
        'department_list': department_list_json,
        'attendance_list': attendance_list_json,
        'manager_feedback_count': manager_feedback_count,
        'employee_feedback_count': employee_feedback_count,
        'manager_leave_count': manager_leave_count,
        'employee_leave_count': employee_leave_count
    }
    return render(request, 'ceo_template/home_content.html', context)


def add_manager(request):
    form = ManagerForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'page_title': 'Add Manager'}
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password')
            division = form.cleaned_data.get('division')
            passport = request.FILES.get('profile_pic')
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=2, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.manager.division = division
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_manager'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Please fulfil all requirements")

    return render(request, 'ceo_template/add_manager_template.html', context)


def add_employee(request):
    employee_form = EmployeeForm(request.POST or None, request.FILES or None)
    context = {'form': employee_form, 'page_title': 'Add Employee'}
    
    # Handle AJAX request for departments based on division
    if request.method == 'GET' and 'division_id' in request.GET and 'action' in request.GET:
        division_id = request.GET.get('division_id')
        try:
            division = Division.objects.get(id=division_id)
            departments = Department.objects.filter(division=division)
            return JsonResponse({
                'departments': [{'id': dept.id, 'name': dept.name} for dept in departments]
            })
        except Division.DoesNotExist:
            return JsonResponse({'error': 'Division not found'}, status=404)
    
    if request.method == 'POST':
        if employee_form.is_valid():
            first_name = employee_form.cleaned_data.get('first_name')
            last_name = employee_form.cleaned_data.get('last_name')
            address = employee_form.cleaned_data.get('address')
            email = employee_form.cleaned_data.get('email')
            gender = employee_form.cleaned_data.get('gender')
            password = employee_form.cleaned_data.get('password')
            division = employee_form.cleaned_data.get('division')
            department = employee_form.cleaned_data.get('department')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=3, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.employee.division = division
                user.employee.department = department
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_employee'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'ceo_template/add_employee_template.html', context)


def add_division(request):
    form = DivisionForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Division'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                division = Division()
                division.name = name
                division.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_division'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'ceo_template/add_division_template.html', context)


def add_department(request):
    form = DepartmentForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Department'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            division = form.cleaned_data.get('division')
            try:
                department = Department()
                department.name = name
                department.division = division
                department.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_department'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")

    return render(request, 'ceo_template/add_department_template.html', context)


def manage_manager(request):
    allManager = CustomUser.objects.filter(user_type=2)
    context = {
        'allManager': allManager,
        'page_title': 'Manage Manager'
    }
    return render(request, "ceo_template/manage_manager.html", context)


def manage_employee(request):
    employees = CustomUser.objects.filter(user_type=3)
    context = {
        'employees': employees,
        'page_title': 'Manage Employees'
    }
    return render(request, "ceo_template/manage_employee.html", context)


def manage_division(request):
    divisions = Division.objects.all()
    context = {
        'divisions': divisions,
        'page_title': 'Manage Divisions'
    }
    return render(request, "ceo_template/manage_division.html", context)


def manage_department(request):
    departments = Department.objects.all()
    context = {
        'departments': departments,
        'page_title': 'Manage Departments'
    }
    return render(request, "ceo_template/manage_department.html", context)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from main_app.models import Manager, CustomUser  # Adjust based on your models
from main_app.forms import ManagerForm  # Adjust based on your forms

def edit_manager(request, manager_id):
    manager = get_object_or_404(Manager, id=manager_id)
    form = ManagerForm(request.POST or None, request.FILES or None, instance=manager)
    context = {
        'form': form,
        'manager_id': manager_id,
        'page_title': 'Edit Manager'
    }

    if request.method == 'POST':
        if form.is_valid():
            try:
                # Extract cleaned data
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                address = form.cleaned_data.get('address')
                username = form.cleaned_data.get('username')
                email = form.cleaned_data.get('email')
                gender = form.cleaned_data.get('gender')
                password = form.cleaned_data.get('password') or None
                division = form.cleaned_data.get('division')
                passport = request.FILES.get('profile_pic') or None

                # Update the associated user
                user = manager.admin  # Access related CustomUser via ForeignKey
                user.username = username
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address

                # Handle password update
                if password:
                    user.set_password(password)

                # Handle profile picture upload
                if passport:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    user.profile_pic = fs.url(filename)

                # Save updates to user and manager
                user.save()
                manager.division = division
                manager.save()

                # Success message and redirect
                messages.success(request, "Manager details successfully updated.")
                return redirect(reverse('edit_manager', args=[manager_id]))

            except Exception as e:
                # Handle any unexpected errors
                messages.error(request, f"Could not update manager: {e}")
        else:
            # Provide error feedback for invalid form
            messages.error(request, "Please correct the highlighted errors below.")

    # Render the form with context (GET or POST with errors)
    return render(request, "ceo_template/edit_manager_template.html", context)



def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    form = EmployeeForm(request.POST or None, instance=employee)
    context = {
        'form': form,
        'employee_id': employee_id,
        'page_title': 'Edit Employee'
    }
    
    # Handle AJAX request for departments based on division
    if request.method == 'GET' and 'division_id' in request.GET and 'action' in request.GET:
        division_id = request.GET.get('division_id')
        try:
            division = Division.objects.get(id=division_id)
            departments = Department.objects.filter(division=division)
            return JsonResponse({
                'departments': [{'id': dept.id, 'name': dept.name} for dept in departments]
            })
        except Division.DoesNotExist:
            return JsonResponse({'error': 'Division not found'}, status=404)
    
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            division = form.cleaned_data.get('division')
            department = form.cleaned_data.get('department')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=employee.admin.id)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                employee.division = division
                employee.department = department
                user.save()
                employee.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_employee', args=[employee_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please Fill Form Properly!")
    else:
        return render(request, "ceo_template/edit_employee_template.html", context)


def edit_division(request, division_id):
    instance = get_object_or_404(Division, id=division_id)
    form = DivisionForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'division_id': division_id,
        'page_title': 'Edit Division'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                division = Division.objects.get(id=division_id)
                division.name = name
                division.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'ceo_template/edit_division_template.html', context)


def edit_department(request, department_id):
    instance = get_object_or_404(Department, id=department_id)
    form = DepartmentForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'department_id': department_id,
        'page_title': 'Edit Department'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            division = form.cleaned_data.get('division')
            try:
                department = Department.objects.get(id=department_id)
                department.name = name
                department.division = division
                department.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_department', args=[department_id]))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")
    return render(request, 'ceo_template/edit_department_template.html', context)


@csrf_exempt
def check_email_availability(request):
    email = request.POST.get("email")
    try:
        user = CustomUser.objects.filter(email=email).exists()
        if user:
            return HttpResponse(True)
        return HttpResponse(False)
    except Exception as e:
        return HttpResponse(False)


@csrf_exempt
def employee_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackEmployee.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Employee Feedback Messages'
        }
        return render(request, 'ceo_template/employee_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackEmployee, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


def admin_employee_feedback_count(request):
    feedback_count = FeedbackEmployee.objects.filter(reply="").count()
    return JsonResponse({"feedback_count": feedback_count})


@csrf_exempt
def manager_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackManager.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Manager Feedback Messages'
        }
        return render(request, 'ceo_template/manager_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackManager, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


def admin_manager_feedback_count(request):
    feedback_count = FeedbackManager.objects.filter(reply="").count()
    return JsonResponse({"feedback_count": feedback_count})


@csrf_exempt
def view_manager_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportManager.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Manager'
        }
        return render(request, "ceo_template/manager_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportManager, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


@csrf_exempt
def view_employee_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportEmployee.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Employees'
        }
        return render(request, "ceo_template/employee_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportEmployee, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


def admin_view_attendance(request):
    departments = Department.objects.all()
    context = {
        'departments': departments,
        'page_title': 'View Employee Attendance'
    }
    return render(request, 'ceo_template/admin_view_attendance.html', context)


def admin_update_attendance(request):
    divisions = Division.objects.all()
    context = {
        'divisions': divisions,
        'page_title': 'Update Attendance'
    }
    return render(request, 'ceo_template/admin_update_attendance.html', context)


@csrf_exempt
def get_admin_attendance(request):
    department_id = request.POST.get('department')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    
    try:
        department = get_object_or_404(Department, id=department_id)
        
        # Get all attendance records for this department in the date range
        attendance_objs = Attendance.objects.filter(
            department=department,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        if not attendance_objs.exists():
            return JsonResponse(json.dumps([]), safe=False)
        
        # Get all employees in this department
        employees = Employee.objects.filter(department=department)
        
        json_data = []
        
        # For each attendance record, get all employee attendance reports
        for attendance in attendance_objs:
            # Get attendance reports for this date
            attendance_reports = AttendanceReport.objects.filter(
                attendance=attendance,
                employee__isnull=False  # Only employee reports, not manager
            )
            
            for report in attendance_reports:
                if report.employee:  # Make sure there's an employee
                    data = {
                        "name": f"{report.employee.admin.first_name} {report.employee.admin.last_name}",
                        "status": str(report.status),
                        "date": attendance.date.strftime('%Y-%m-%d')
                    }
                    json_data.append(data)
        
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse(json.dumps([]), safe=False)


def admin_view_profile(request):
    admin = get_object_or_404(Admin, admin=request.user)
    form = AdminForm(request.POST or None, request.FILES or None,
                     instance=admin)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                passport = request.FILES.get('profile_pic') or None
                custom_user = admin.admin
                if password != None:
                    custom_user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    custom_user.profile_pic = passport_url
                custom_user.first_name = first_name
                custom_user.last_name = last_name
                custom_user.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('admin_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
    return render(request, "ceo_template/admin_view_profile.html", context)


def admin_notify_manager(request):
    manager = CustomUser.objects.filter(user_type=2)
    context = {
        'page_title': "Send Notifications To Manager",
        'allManager': manager
    }
    return render(request, "ceo_template/manager_notification.html", context)


def admin_notify_employee(request):
    employee = CustomUser.objects.filter(user_type=3)
    context = {
        'page_title': "Send Notifications To Employees",
        'employees': employee
    }
    return render(request, "ceo_template/employee_notification.html", context)


@csrf_exempt
def send_employee_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    employee = get_object_or_404(Employee, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "OfficeOps",
                'body': message,
                'click_action': reverse('employee_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': employee.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationEmployee(employee=employee, message=message, read=False)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


@csrf_exempt
def send_manager_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    manager = get_object_or_404(Manager, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "OfficeOps",
                'body': message,
                'click_action': reverse('manager_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': manager.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationManager(manager=manager, message=message, read=False)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def delete_manager(request, manager_id):
    manager = get_object_or_404(CustomUser, manager__id=manager_id)
    manager.delete()
    messages.success(request, "Manager deleted successfully!")
    return redirect(reverse('manage_manager'))


def delete_employee(request, employee_id):
    employee = get_object_or_404(CustomUser, employee__id=employee_id)
    employee.delete()
    messages.success(request, "Employee deleted successfully!")
    return redirect(reverse('manage_employee'))


def delete_division(request, division_id):
    division = get_object_or_404(Division, id=division_id)
    try:
        division.delete()
        messages.success(request, "Division deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some employees are assigned to this division already. Kindly change the affected employee division and try again")
    return redirect(reverse('manage_division'))


def delete_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    department.delete()
    messages.success(request, "Department deleted successfully!")
    return redirect(reverse('manage_department'))




@csrf_exempt  # Temporarily disable CSRF for debugging (remove in production)
def view_manager_leave(request):
    if request.method == "POST":
        # Debugging: Print POST data
        print("POST data:", request.POST)

        # Get leave ID and status from the POST request
        leave_id = request.POST.get("id")
        status = request.POST.get("status")

        # Debugging: Print leave ID and status
        print("Leave ID:", leave_id, "Status:", status)

        # Validate leave ID and status
        if not leave_id or not status:
            return JsonResponse("False", safe=False)

        try:
            # Fetch the leave request from the database
            leave = get_object_or_404(LeaveReportManager, id=leave_id)

            # Update the leave status
            leave.status = int(status)
            leave.save()

            # Define the email subject and message based on the status
            if leave.status == 1:
                subject = "Leave Request Approved ✅"
                message = f"Dear {leave.manager.admin.first_name},\n\nYour leave request for {leave.date} has been **approved** by the Admin.\n\nBest regards,\nHR Team"
            elif leave.status == -1:
                subject = "Leave Request Denied ❌"
                message = f"Dear {leave.manager.admin.first_name},\n\nYour leave request for {leave.date} has been **denied** by the Admin.\n\nPlease contact HR for more details.\n\nBest regards,\nHR Team"
            else:
                return JsonResponse("False", safe=False)

            # Send email notification to the manager
            try:
                send_mail(
                    subject,
                    message,
                    "alpen750@gmail.com",  # Replace with your sender email
                    [leave.manager.admin.email],  # Send email to the manager
                    fail_silently=False,
                )
                return JsonResponse("True", safe=False)
            except Exception as e:
                print(f"Error sending email: {e}")  # Debugging: Print email error
                return JsonResponse("False", safe=False)
        except Exception as e:
            print(f"Error processing leave request: {e}")  # Debugging: Print general error
            return JsonResponse("False", safe=False)
    else:
        # Handle GET request (render the leave requests page)
        allLeave = LeaveReportManager.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Manager'
        }
        return render(request, "ceo_template/manager_leave_view.html", context)
    
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import LeaveReportEmployee
from django.conf import settings

def view_employee_leave(request):
    if request.method == "GET":
        # ✅ Handle GET request to display leave requests in the admin panel
        allLeave = LeaveReportEmployee.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Employees'
        }
        return render(request, "ceo_template/employee_leave_view.html", context)

    elif request.method == "POST":
        # ✅ Handle POST request to approve/reject leave and send email
        leave_id = request.POST.get("id")
        status = request.POST.get("status")

        try:
            leave = LeaveReportEmployee.objects.get(id=leave_id)
        except LeaveReportEmployee.DoesNotExist:
            return JsonResponse({"status": "False", "message": "Leave request not found"}, safe=False)

        if status not in ['1', '-1']:
            return JsonResponse({"status": "False", "message": "Invalid status value"}, safe=False)

        # Update leave status
        leave.status = int(status)
        leave.save()

        # Define email content
        if leave.status == 1:
            subject = "Leave Request Approved ✅"
            message = f"Dear {leave.employee.admin.first_name},\n\nYour leave request for {leave.date} has been **approved** by the Admin.\n\nBest regards,\nHR Team"
        else:
            subject = "Leave Request Rejected ❌"
            message = f"Dear {leave.employee.admin.first_name},\n\nYour leave request for {leave.date} has been **rejected** by the Admin.\n\nPlease contact HR for more details.\n\nBest regards,\nHR Team"

        # Send email notification
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,  # Use email from settings
                [leave.employee.admin.email],  # Send email to employee
                fail_silently=False,
            )
        except Exception as e:
            return JsonResponse({"status": "False", "message": f"Error sending email: {e}"}, safe=False)

        return JsonResponse({"status": "True", "message": "Leave status updated and email sent successfully"}, safe=False)

    else:
        return JsonResponse({"status": "False", "message": "Invalid request method"}, safe=False)
    


# from django.shortcuts import render
# from django.http import JsonResponse, HttpResponse
# from django.template.loader import get_template
# from xhtml2pdf import pisa
# from django.conf import settings
# import os
# from datetime import datetime
# from employee.models import Employee, Attendance, Task
# from django.contrib.auth.decorators import login_required
# from main_app.decorators import ceo_required

# @login_required
# @ceo_required
# def ceo_rank_report(request):
#     if request.method == 'POST':
#         month = request.POST.get('month')
#         year = request.POST.get('year')
        
#         try:
#             # Get all employees
#             employees = Employee.objects.all()
#             employee_rankings = []
            
#             for employee in employees:
#                 # Calculate attendance metrics
#                 attendances = Attendance.objects.filter(
#                     employee=employee,
#                     date__year=year,
#                     date__month=month
#                 )
                
#                 total_days = attendances.count()
#                 present_days = attendances.filter(status=True).count()
#                 absent_days = total_days - present_days
#                 attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
                
#                 # Calculate task metrics
#                 tasks = Task.objects.filter(
#                     employee=employee,
#                     deadline__year=year,
#                     deadline__month=month
#                 )
                
#                 total_tasks = tasks.count()
#                 completed_tasks = tasks.filter(status='Completed').count()
#                 average_rating = tasks.aggregate(Avg('rating'))['rating__avg'] or 0
                
#                 # Calculate score (customize this formula as needed)
#                 score = (attendance_percentage * 0.4) + (average_rating * 20 * 0.6)
                
#                 employee_rankings.append({
#                     'employee': employee,
#                     'present_days': present_days,
#                     'absent_days': absent_days,
#                     'attendance_percentage': attendance_percentage,
#                     'total_tasks': total_tasks,
#                     'completed_tasks': completed_tasks,
#                     'average_rating': average_rating,
#                     'score': score
#                 })
            
#             # Sort employees by score (descending)
#             employee_rankings.sort(key=lambda x: x['score'], reverse=True)
            
#             # Generate PDF
#             template = get_template('ceo_rank_report_pdf.html')
#             context = {
#                 'employee_rankings': employee_rankings,
#                 'month': datetime.strptime(month, "%m").strftime("%B"),
#                 'year': year,
#                 'generated_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             }
#             html = template.render(context)
            
#             # Create PDF
#             response = HttpResponse(content_type='application/pdf')
#             filename = f"CEO_Rank_Report_{month}_{year}.pdf"
#             response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
#             # Generate PDF
#             pisa_status = pisa.CreatePDF(html, dest=response)
#             if pisa_status.err:
#                 return HttpResponse('Error generating CEO report')
            
#             # Save PDF to media directory
#             pdf_path = os.path.join(settings.MEDIA_ROOT, 'ceo_reports', filename)
#             os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
#             with open(pdf_path, 'wb') as pdf_file:
#                 pisa.CreatePDF(html, dest=pdf_file)
            
#             return response
            
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
    
#     # GET request - show form
#     current_month = datetime.now().month
#     current_year = datetime.now().year
#     months = [
#         (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
#         (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
#         (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
#     ]
#     years = range(datetime.now().year - 5, datetime.now().year + 1)
    
#     return render(request, 'ceo/ceo_rank_report.html', {
#         'months': months,
#         'years': reversed(years),  # Show recent years first
#         'current_month': current_month,
#         'current_year': current_year
#     })

@csrf_exempt
def get_manager_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        attendance = Attendance.objects.get(id=attendance_date_id)
        attendance_reports = AttendanceReport.objects.filter(attendance=attendance)
        
        json_data = []
        for report in attendance_reports:
            if hasattr(report, 'manager'):  # Check if this is a manager attendance report
                data = {
                    "id": report.id,
                    "name": report.manager.admin.first_name + " " + report.manager.admin.last_name,
                    "status": report.status
                }
                json_data.append(data)
        
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        print(e)
        return HttpResponse("Error")

@csrf_exempt
def update_manager_attendance(request):
    """Update manager attendance for a specific date"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method Not Allowed"}, status=405)
        
    division_id = request.POST.get('division')
    attendance_date = request.POST.get('date')
    manager_ids_json = request.POST.get('manager_ids')
    
    if not division_id or not attendance_date or not manager_ids_json:
        return JsonResponse({"success": False, "message": "Missing required parameters"}, status=400)
    
    try:
        manager_ids = json.loads(manager_ids_json)
        division = Division.objects.get(id=division_id)
        
        # Get departments for this division
        departments = Department.objects.filter(division=division)
        
        if not departments.exists():
            return JsonResponse({"success": False, "message": "No departments found for this division"}, status=404)
        
        # Find attendance records for this date in any department of this division
        attendance_objs = Attendance.objects.filter(
            department__in=departments,
            date=attendance_date
        )
        
        if not attendance_objs.exists():
            # Create a new attendance record for the first department
            first_dept = departments.first()
            attendance_obj = Attendance.objects.create(
                department=first_dept,
                date=attendance_date
            )
            attendance_objs = [attendance_obj]
        
        # Process attendance for each manager
        updated_count = 0
        for manager_data in manager_ids:
            manager_id = manager_data['id']
            status = manager_data['status']
            
            manager = Manager.objects.get(id=manager_id)
            
            # Use the first attendance record for the reports
            attendance = attendance_objs[0]
            
            # Update or create attendance report
            _, created = AttendanceReport.objects.update_or_create(
                attendance=attendance,
                manager=manager,
                defaults={'status': status == 1}
            )
            updated_count += 1
        
        return JsonResponse({"success": True, "message": f"Successfully updated attendance for {updated_count} managers"})
    except Division.DoesNotExist:
        return JsonResponse({"success": False, "message": "Division not found"}, status=404)
    except Manager.DoesNotExist:
        return JsonResponse({"success": False, "message": "One or more managers not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON format for manager data"}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "message": f"Error updating attendance: {str(e)}"}, status=500)

def admin_take_manager_attendance(request):
    divisions = Division.objects.all()
    context = {
        'divisions': divisions,
        'page_title': 'Take Manager Attendance'
    }
    return render(request, 'ceo_template/admin_take_manager_attendance.html', context)


@csrf_exempt
def get_managers(request):
    division_id = request.POST.get('division')
    attendance_date = request.POST.get('date', None)
    
    try:
        division = Division.objects.get(id=division_id)
        managers = Manager.objects.filter(division=division)
        
        manager_list = []
        
        # If attendance date is provided, get attendance status for each manager
        if attendance_date:
            try:
                # Get departments for this division
                departments = Department.objects.filter(division=division)
                
                # Find attendance records for this date in any department of this division
                attendance_objs = Attendance.objects.filter(
                    department__in=departments,
                    date=attendance_date
                )
                
                if not attendance_objs.exists():
                    # Create a new attendance record for the first department
                    first_dept = departments.first()
                    if first_dept:
                        attendance_obj = Attendance.objects.create(
                            department=first_dept,
                            date=attendance_date
                        )
                        attendance_objs = [attendance_obj]
                    else:
                        attendance_objs = []
                
                for manager in managers:
                    # Look for attendance report in any of the found attendance records
                    status = False
                    for attendance in attendance_objs:
                        try:
                            report = AttendanceReport.objects.get(
                                attendance=attendance,
                                manager=manager
                            )
                            status = report.status
                            break
                        except AttendanceReport.DoesNotExist:
                            continue
                    
                    data = {
                        "id": manager.id,
                        "name": f"{manager.admin.first_name} {manager.admin.last_name}",
                        "status": status
                    }
                    manager_list.append(data)
            except Exception as e:
                print(f"Error getting attendance status: {e}")
                # Fall back to regular manager list without attendance status
                for manager in managers:
                    data = {
                        "id": manager.id,
                        "name": f"{manager.admin.first_name} {manager.admin.last_name}",
                        "status": False
                    }
                    manager_list.append(data)
        else:
            # Regular manager list without attendance status
            for manager in managers:
                data = {
                    "id": manager.id,
                    "name": f"{manager.admin.first_name} {manager.admin.last_name}"
                }
                manager_list.append(data)
        
        return JsonResponse(manager_list, safe=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def save_manager_attendance(request):
    """Save manager attendance"""
    division_id = request.POST.get('division')
    date_str = request.POST.get('date')
    manager_ids_json = request.POST.get('manager_ids')
    
    # Debug logging of request parameters
    print(f"Save Manager Attendance Request - Date: {date_str}, Division ID: {division_id}")
    print(f"Manager IDs JSON length: {len(manager_ids_json) if manager_ids_json else 'None'}")
    
    if not division_id or not date_str or not manager_ids_json:
        missing = []
        if not division_id: missing.append("division_id")
        if not date_str: missing.append("date")
        if not manager_ids_json: missing.append("manager_ids")
        error_msg = f"Missing required parameters: {', '.join(missing)}"
        print(error_msg)
        return JsonResponse({"success": False, "message": error_msg}, status=400)
    
    try:
        # Validate date is current day (ignoring time)
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        print(f"Date provided: {date_obj}, Today's date: {today}")
        
        if date_obj > today:
            error_msg = "Cannot mark attendance for future dates"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        if date_obj < today:
            error_msg = "Attendance can only be marked for the current day"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        manager_ids = json.loads(manager_ids_json)
        print(f"Successfully parsed manager_ids JSON. Found {len(manager_ids)} managers")
        
        # Validate manager data structure
        if not isinstance(manager_ids, list):
            error_msg = "Manager data must be a list"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        if len(manager_ids) == 0:
            error_msg = "No managers provided in the request"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        for i, mgr in enumerate(manager_ids):
            if not isinstance(mgr, dict) or 'id' not in mgr or 'status' not in mgr:
                error_msg = f"Invalid manager data format at index {i}"
                print(error_msg, mgr)
                return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        try:
            division = Division.objects.get(id=division_id)
            print(f"Found division: {division.name} (ID: {division.id})")
        except Division.DoesNotExist:
            error_msg = f"Division with ID {division_id} not found"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=404)
        
        # Get the first department in the division for attendance record
        try:
            department = Department.objects.filter(division=division).first()
            if not department:
                error_msg = "No department found for division"
                print(error_msg)
                return JsonResponse({"success": False, "message": error_msg}, status=404)
            print(f"Using department: {department.name} (ID: {department.id})")
        except Exception as e:
            error_msg = f"Error finding department for division: {str(e)}"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=500)
        
        # Create attendance record
        try:
            attendance, created = Attendance.objects.get_or_create(
                department=department,
                date=date_obj
            )
            print(f"Attendance record {'created' if created else 'found'} for date {date_obj}")
        except Exception as e:
            error_msg = f"Error creating/getting attendance record: {str(e)}"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=500)
        
        # Process attendance for each manager
        saved_count = 0
        error_count = 0
        error_messages = []
        
        for manager_data in manager_ids:
            try:
                manager_id = manager_data['id']
                status_value = manager_data['status']
                
                print(f"Processing manager ID: {manager_id}, Status: {status_value}")
                
                try:
                    manager = Manager.objects.get(id=manager_id)
                    print(f"Found manager: {manager.admin.first_name} {manager.admin.last_name} (ID: {manager.id})")
                except Manager.DoesNotExist:
                    error_msg = f"Manager with ID {manager_id} not found"
                    print(error_msg)
                    error_messages.append(error_msg)
                    error_count += 1
                    continue
                
                # Create or update attendance report
                try:
                    attendance_report, created = AttendanceReport.objects.get_or_create(
                        attendance=attendance,
                        manager=manager,
                        defaults={'status': status_value == 1}
                    )
                    print(f"Attendance report {'created' if created else 'found'} for manager {manager.id}")
                    
                    if not created:
                        attendance_report.status = status_value == 1
                        attendance_report.save()
                        print(f"Updated status to {status_value == 1} for existing report")
                    
                    saved_count += 1
                except Exception as e:
                    error_msg = f"Error saving attendance report for manager {manager_id}: {str(e)}"
                    print(error_msg)
                    error_messages.append(error_msg)
                    error_count += 1
            except Exception as e:
                error_msg = f"Error processing manager {manager_data.get('id', 'unknown')}: {str(e)}"
                print(error_msg)
                error_messages.append(error_msg)
                error_count += 1
        
        if saved_count > 0:
            success_msg = f"Successfully saved attendance for {saved_count} managers"
            if error_count > 0:
                success_msg += f" ({error_count} errors occurred)"
            print(success_msg)
            return JsonResponse({"success": True, "message": success_msg})
        else:
            error_msg = "No attendance records were saved"
            if error_messages:
                error_msg += ". Errors: " + "; ".join(error_messages[:3])
                if len(error_messages) > 3:
                    error_msg += f" and {len(error_messages) - 3} more errors"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=500)
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON data: {str(e)}"
        print(error_msg)
        # Log the actual JSON for debugging
        print(f"Problematic JSON: {manager_ids_json[:100]}...")
        return JsonResponse({"success": False, "message": error_msg}, status=400)
    except Exception as e:
        error_msg = f"Error saving attendance: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "message": error_msg}, status=500)

def admin_view_manager_attendance(request):
    divisions = Division.objects.all()
    context = {
        'divisions': divisions,
        'page_title': 'View Manager Attendance'
    }
    return render(request, 'ceo_template/admin_view_manager_attendance.html', context)


@csrf_exempt
def view_manager_attendance_data(request):
    """Get attendance data for managers in a specific date range"""
    division_id = request.POST.get('division')
    manager_id = request.POST.get('manager')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    
    try:
        # Get all departments in the division
        division = Division.objects.get(id=division_id)
        departments = Department.objects.filter(division=division)
        
        # Get all attendance records for these departments in the date range
        attendance_records = Attendance.objects.filter(
            department__in=departments,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        attendance_data = []
        
        # If specific manager is selected
        if manager_id != 'all':
            manager = Manager.objects.get(id=manager_id)
            for attendance in attendance_records:
                try:
                    # Get this manager's attendance for this date
                    report = AttendanceReport.objects.get(
                        attendance=attendance,
                        manager=manager
                    )
                    
                    data = {
                        'date': attendance.date.strftime('%Y-%m-%d'),
                        'manager_name': f"{manager.admin.first_name} {manager.admin.last_name}",
                        'status': report.status
                    }
                    attendance_data.append(data)
                except AttendanceReport.DoesNotExist:
                    # No record for this date - count as absent
                    data = {
                        'date': attendance.date.strftime('%Y-%m-%d'),
                        'manager_name': f"{manager.admin.first_name} {manager.admin.last_name}",
                        'status': False
                    }
                    attendance_data.append(data)
        else:
            # Get all managers in this division
            managers = Manager.objects.filter(division=division)
            
            for attendance in attendance_records:
                for manager in managers:
                    try:
                        # Get this manager's attendance for this date
                        report = AttendanceReport.objects.get(
                            attendance=attendance,
                            manager=manager
                        )
                        
                        data = {
                            'date': attendance.date.strftime('%Y-%m-%d'),
                            'manager_name': f"{manager.admin.first_name} {manager.admin.last_name}",
                            'status': report.status
                        }
                        attendance_data.append(data)
                    except AttendanceReport.DoesNotExist:
                        # No record for this date - count as absent
                        data = {
                            'date': attendance.date.strftime('%Y-%m-%d'),
                            'manager_name': f"{manager.admin.first_name} {manager.admin.last_name}",
                            'status': False
                        }
                        attendance_data.append(data)
        
        return JsonResponse(json.dumps(attendance_data), safe=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=400)

def admin_manager_leave_count(request):
    leave_count = LeaveReportManager.objects.filter(status=0).count()
    return JsonResponse({"leave_count": leave_count})

def admin_employee_leave_count(request):
    leave_count = LeaveReportEmployee.objects.filter(status=0).count()
    return JsonResponse({"leave_count": leave_count})
