import json
import math
from datetime import datetime, timedelta

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa

from .forms import *
from .models import *
from .decorators import employee_required


def employee_home(request):
    employee = get_object_or_404(Employee, admin=request.user)
    total_department = Department.objects.filter(division=employee.division).count()
    total_attendance = AttendanceReport.objects.filter(employee=employee).count()
    total_present = AttendanceReport.objects.filter(employee=employee, status=True).count()
    task_count = Task.objects.filter(employee=employee, status="Pending").count()  # Only count pending tasks
    
    # Add notification count
    notification_count = NotificationEmployee.objects.filter(employee=employee, read=False).count()
    # Add unread feedback count
    feedback_count = FeedbackEmployee.objects.filter(employee=employee, reply="").count()
    # Add pending leave count
    pending_leave_count = LeaveReportEmployee.objects.filter(employee=employee, status=0).count()
    
    if total_attendance == 0:  # Don't divide. DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    
    department_name = []
    data_present = []
    data_absent = []
    
    # Get departments from the same division
    departments = Department.objects.filter(division=employee.division)
    
    # Get attendance data for each department
    for department in departments:
        department_name.append(department.name)
        
        attendance = Attendance.objects.filter(department=department)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, employee=employee).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, employee=employee).count()
        
        data_present.append(present_count if present_count > 0 else 0)
        data_absent.append(absent_count if absent_count > 0 else 0)
    
    # If no departments found, add employee's department
    if not department_name and employee.department:
        department_name.append(str(employee.department))
        data_present.append(total_present)
        data_absent.append(total_attendance - total_present)
    
    # Get panel title
    panel_title = 'Employee Homepage'
    if employee.department:
        panel_title = str(employee.department) + ' Department'
    
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_department': total_department,
        'departments': departments,
        'data_present': json.dumps(data_present),
        'data_absent': json.dumps(data_absent),
        'data_name': json.dumps(department_name),
        'task_count': task_count,
        'notification_count': notification_count,
        'feedback_count': feedback_count,
        'pending_leave_count': pending_leave_count,
        'page_title': 'Employee Homepage',
        'panel_title': panel_title
    }
    return render(request, 'employee_template/home_content.html', context)


@ csrf_exempt
def employee_view_attendance(request):
    employee = get_object_or_404(Employee, admin=request.user)
    if request.method != 'POST':
        context = {
            'employee': employee,
            'page_title': 'View Attendance'
        }
        return render(request, 'employee_template/employee_view_attendance.html', context)
    else:
        department_id = request.POST.get('department')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        
        # Log incoming data for debugging
        print(f"Employee View Attendance Request - Employee ID: {employee.id}")
        print(f"Department ID: {department_id}, Start Date: {start}, End Date: {end}")
        
        if not department_id or not start or not end:
            print("Missing required parameters")
            return JsonResponse([], safe=False)
        
        try:
            # Verify that the department belongs to the employee
            if str(employee.department.id) != department_id:
                print(f"Department ID mismatch: {department_id} vs {employee.department.id}")
                return JsonResponse([], safe=False)
                
            department = employee.department
            print(f"Using employee's department: {department.name} (ID: {department.id})")
            
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            print(f"Date range: {start_date} to {end_date}")
            
            # Get all attendance records for the department within the date range
            attendance_records = Attendance.objects.filter(
                date__range=(start_date, end_date), 
                department=department
            ).order_by('date')
            
            print(f"Found {attendance_records.count()} attendance records")
            
            # Get attendance reports for this employee for those attendance records
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance_records, 
                employee=employee
            )
            
            print(f"Found {attendance_reports.count()} attendance reports for employee")
            
            # If no records found for specific attendance records, create a complete date range
            if attendance_reports.count() == 0:
                print("No attendance reports found - checking if we need to generate default records")
                
                # Get all dates in the range
                json_data = []
                delta = end_date - start_date
                for i in range(delta.days + 1):
                    current_date = start_date + timedelta(days=i)
                    # Check if there's an attendance record for this date
                    attendance = Attendance.objects.filter(date=current_date, department=department).first()
                    
                    if attendance:
                        # Try to get a report for this attendance
                        report = AttendanceReport.objects.filter(attendance=attendance, employee=employee).first()
                        if report:
                            data = {
                                "date": str(current_date),
                                "status": report.status
                            }
                        else:
                            # No report for this attendance record, mark as absent by default
                            data = {
                                "date": str(current_date),
                                "status": False
                            }
                    else:
                        # No attendance record for this date, mark as absent by default
                        data = {
                            "date": str(current_date),
                            "status": False
                        }
                    
                    json_data.append(data)
                
                print(f"Generated {len(json_data)} date records for the range")
            else:
                # Create a dictionary to store date to status mapping for quick lookup
                date_status_map = {}
                for report in attendance_reports:
                    date_str = str(report.attendance.date)
                    date_status_map[date_str] = report.status
                
                # Create records for all dates in the range
                json_data = []
                delta = end_date - start_date
                for i in range(delta.days + 1):
                    current_date = start_date + timedelta(days=i)
                    date_str = str(current_date)
                    
                    # If we have a status for this date, use it, otherwise mark as absent
                    if date_str in date_status_map:
                        status = date_status_map[date_str]
                    else:
                        status = False
                    
                    data = {
                        "date": date_str,
                        "status": status
                    }
                    json_data.append(data)
                
                print(f"Generated {len(json_data)} date records with statuses from reports")
            
            # Return the data as JSON
            return JsonResponse(json_data, safe=False)
            
        except Department.DoesNotExist:
            print(f"Department with ID {department_id} not found")
            return JsonResponse([], safe=False)
        except Exception as e:
            print(f"Error in employee_view_attendance: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse([], safe=False)


def employee_apply_leave(request):
    form = LeaveReportEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportEmployee.objects.filter(employee=employee),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('employee_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_apply_leave.html", context)


def employee_feedback(request):
    form = FeedbackEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackEmployee.objects.filter(employee=employee),
        'page_title': 'Employee Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('employee_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_feedback.html", context)


def employee_view_profile(request):
    employee = get_object_or_404(Employee, admin=request.user)
    form = EmployeeEditForm(request.POST or None, request.FILES or None,
                           instance=employee)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = employee.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                employee.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('employee_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "employee_template/employee_view_profile.html", context)


@csrf_exempt
def employee_fcmtoken(request):
    token = request.POST.get('token')
    employee_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        employee_user.fcm_token = token
        employee_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def employee_view_notification(request):
    employee = get_object_or_404(Employee, admin=request.user)
    notifications = NotificationEmployee.objects.filter(employee=employee)
    
    # Mark all notifications as read when viewed
    unread_notifications = NotificationEmployee.objects.filter(employee=employee, read=False)
    for notification in unread_notifications:
        notification.read = True
        notification.save()
    
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "employee_template/employee_view_notification.html", context)


def employee_view_salary(request):
    employee = get_object_or_404(Employee, admin=request.user)
    month_year = request.GET.get('month_year')
    salary = None
    is_paid = False
    from datetime import datetime
    current_date = datetime.now()
    current_month = current_date.replace(day=1)
    if month_year:
        try:
            year, month = map(int, month_year.split('-'))
            first_of_month = datetime(year, month, 1)
            salary = Salary.objects.filter(employee=employee, month_year=first_of_month).first()
            current_month = first_of_month
        except Exception:
            salary = None
    else:
        try:
            salary = Salary.objects.filter(employee=employee).latest('month_year')
            current_month = salary.month_year
        except Salary.DoesNotExist:
            salary = None
    # Check leave_payment attribute
    if salary:
        if hasattr(salary, 'leave_payment'):
            if salary.leave_payment is None:
                salary.leave_payment = 0
        else:
            salary.leave_payment = 0
        total_earnings = (
            (salary.basic_salary or 0) +
            (salary.meal_allowance or 0) +
            (salary.medical_allowance or 0) +
            (salary.transportation_allowance or 0)
        )
        total_deductions = (
            (salary.tax_amount or 0) +
            (salary.insurance_amount or 0) +
            (salary.leave_payment or 0)
        )
        net_salary = total_earnings - total_deductions
    else:
        total_earnings = total_deductions = net_salary = 0
    # Check if salary is paid for the selected/current month
    is_paid = Salary.objects.filter(
        employee=employee,
        month_year=current_month,
        status='paid'
    ).exists()
    employee_data = {
        'name': f"{employee.admin.last_name}, {employee.admin.first_name}",
        'id': employee.id,
        'department': employee.department.name if employee.department else 'Not Assigned'
    }
    context = {
        'employee': employee,
        'employee_data': employee_data,
        'salary': salary,
        'is_paid': is_paid,
        'current_month': current_month,
        'page_title': 'My Salary',
        'total_earnings': total_earnings,
        'total_deductions': total_deductions,
        'net_salary': net_salary,
    }
    return render(request, 'employee_template/employee_view_salary.html', context)

def employee_view_tasks(request):
    employee = get_object_or_404(Employee, admin=request.user)
    tasks = Task.objects.filter(employee=employee)

    context = {
        'tasks': tasks,
        'page_title': 'My Tasks'
    }
    return render(request, 'employee_template/view_tasks.html', context)

def employee_task_count(request):
    employee = get_object_or_404(Employee, admin=request.user)
    task_count = Task.objects.filter(employee=employee, status="Pending").count()
    
    return JsonResponse({"task_count": task_count})

def update_task_status(request):
    if request.method == "POST":
        task_id = request.POST.get("task_id")
        new_status = request.POST.get("status")
        task = get_object_or_404(Task, id=task_id)
        task.status = new_status
        task.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})

def upload_task_file(request):
    if request.method == "POST" and request.FILES.get("task_file"):
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id)

        # Save file
        file = request.FILES["task_file"]
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        task.file = fs.url(filename)  # Save file URL in database
        task.save()

        return JsonResponse({"success": True, "file_url": task.file.url})
    return JsonResponse({"success": False})


@login_required
@employee_required
def employee_rank_report(request):
    if request.method == 'POST':
        month = request.POST.get('month')
        year = request.POST.get('year')
        
        print(f"Generating report for month: {month}, year: {year}")  # Debug print
        
        try:
            employee = get_object_or_404(Employee, admin=request.user)
            print(f"Found employee: {employee.admin.first_name} {employee.admin.last_name}")  # Debug print
            
            # Calculate attendance metrics
            attendances = Attendance.objects.filter(
                department=employee.department,
                date__year=year,
                date__month=month
            )
            
            print(f"Found {attendances.count()} attendance records")  # Debug print
            
            total_days = attendances.count()
            present_days = 0
            absent_days = 0
            
            for attendance in attendances:
                try:
                    report = AttendanceReport.objects.get(
                        attendance=attendance,
                        employee=employee
                    )
                    if report.status:
                        present_days += 1
                    else:
                        absent_days += 1
                except AttendanceReport.DoesNotExist:
                    absent_days += 1
            
            print(f"Attendance stats - Present: {present_days}, Absent: {absent_days}")  # Debug print
            
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
            
            # Calculate task metrics
            tasks = Task.objects.filter(
                employee=employee,
                deadline__year=year,
                deadline__month=month
            )
            
            print(f"Found {tasks.count()} tasks")  # Debug print
            
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(status='Completed').count()
            pending_tasks = tasks.filter(status='Pending').count()
            
            # Calculate completion rate
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Generate PDF
            template = get_template('employee_template/employee_rank_report_pdf.html')
            context = {
                'employee': employee,
                'present_days': present_days,
                'absent_days': absent_days,
                'attendance_percentage': round(attendance_percentage, 2),
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'completion_rate': round(completion_rate, 2),
                'month': datetime.strptime(month, "%m").strftime("%B"),
                'year': year,
                'generated_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print("Rendering template with context")  # Debug print
            html = template.render(context)
            
            # Create PDF
            response = HttpResponse(content_type='application/pdf')
            filename = f"Employee_Performance_Report_{employee.admin.first_name}_{employee.admin.last_name}_{month}_{year}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            print("Generating PDF")  # Debug print
            # Generate PDF
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                print(f"PDF generation error: {pisa_status.err}")  # Debug print
                messages.error(request, "Error generating PDF report")
                return redirect('employee_rank_report')
            
            print("PDF generated successfully")  # Debug print
            return response
            
        except Exception as e:
            print(f"Error in employee_rank_report: {str(e)}")  # Debug print
            import traceback
            traceback.print_exc()  # Print full traceback
            messages.error(request, f"Error generating report: {str(e)}")
            return redirect('employee_rank_report')
    
    # GET request - show form
    current_month = datetime.now().month
    current_year = datetime.now().year
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    years = range(datetime.now().year - 5, datetime.now().year + 1)
    
    context = {
        'months': months,
        'years': reversed(years),  # Show recent years first
        'current_month': current_month,
        'current_year': current_year,
        'page_title': 'My Performance Report'
    }
    return render(request, 'employee_template/employee_rank_report.html', context)

def employee_notification_count(request):
    employee = get_object_or_404(Employee, admin=request.user)
    notification_count = NotificationEmployee.objects.filter(employee=employee, read=False).count()
    return JsonResponse({"notification_count": notification_count})

def employee_feedback_count(request):
    employee = get_object_or_404(Employee, admin=request.user)
    feedback_count = FeedbackEmployee.objects.filter(employee=employee, reply="").count()
    return JsonResponse({"feedback_count": feedback_count})

def employee_leave_count(request):
    employee = get_object_or_404(Employee, admin=request.user)
    leave_count = LeaveReportEmployee.objects.filter(employee=employee, status=0).count()
    return JsonResponse({"leave_count": leave_count})

