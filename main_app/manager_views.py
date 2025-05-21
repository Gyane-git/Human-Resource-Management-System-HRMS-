import json
from datetime import datetime
import calendar

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .forms import *
from .models import *
from .models import Task, Employee, Manager
from .forms import TaskForm



def manager_home(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    total_department = departments.count()
    total_employees = Employee.objects.filter(department__in=departments).count()
    
    attendance = Attendance.objects.filter(department__in=departments)
    total_attendance = attendance.count()
    
    leaves = LeaveReportManager.objects.filter(manager=manager)
    total_leave = leaves.count()
    
    # For Notification
    notification_count = NotificationManager.objects.filter(manager=manager, read=False).count()
    # For Unread feedback
    feedback_count = FeedbackManager.objects.filter(manager=manager, reply="").count()
    # For Pending leave
    pending_leave_count = LeaveReportManager.objects.filter(manager=manager, status=0).count()
    
    # Build department-specific data for bar chart
    department_list = []
    attendance_list = []
    
    # Get attendance data for each department
    for department in departments:
        total_dept_attendance = Attendance.objects.filter(department=department).count()
        department_list.append(department.name)
        attendance_list.append(total_dept_attendance if total_dept_attendance > 0 else 0)
    
    # Create a dynamic panel title based on the manager's name and division
    panel_title = f"Manager Panel - {manager.admin.first_name} ({manager.division})"
    
    context = {
        'total_employees': total_employees,
        'total_department': total_department,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'notification_count': notification_count,
        'feedback_count': feedback_count,
        'pending_leave_count': pending_leave_count,
        'department_list': json.dumps(department_list),
        'attendance_list': json.dumps(attendance_list),
        'panel_title': panel_title,
        'page_title': 'Manager Homepage'
    }
    return render(request, 'manager_template/home_content.html', context)


def manager_take_attendance(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'departments': departments,
        'page_title': 'Take Attendance'
    }

    return render(request, 'manager_template/manager_take_attendance.html', context)


@csrf_exempt
def get_employees(request):
    department_id = request.POST.get('department')
    attendance_date = request.POST.get('date', None)
    
    if not department_id:
        return JsonResponse({"success": False, "message": "Department ID is required"}, status=400)
    
    try:
        department = Department.objects.get(id=department_id)
        employees = Employee.objects.filter(department=department)
        
        employee_data = []
        
        # If attendance date is provided, get attendance status for each employee
        if attendance_date:
            try:
                # Get or create attendance record for the date
                attendance, created = Attendance.objects.get_or_create(
                    department=department,
                    date=attendance_date
                )
                
                for employee in employees:
                    # Get or create attendance report for this employee
                    attendance_report, _ = AttendanceReport.objects.get_or_create(
                        employee=employee,
                        attendance=attendance,
                        defaults={'status': False}
                    )
                    
                    data = {
                        "id": employee.id,
                        "name": f"{employee.admin.first_name} {employee.admin.last_name}",
                        "status": attendance_report.status
                    }
                    employee_data.append(data)
            except Exception as e:
                print(f"Error fetching attendance data: {e}")
                # Fall back to regular employee list without attendance status
                for employee in employees:
                    data = {
                        "id": employee.id,
                        "name": f"{employee.admin.first_name} {employee.admin.last_name}",
                        "status": False
                    }
                    employee_data.append(data)
        else:
            # Regular employee list without attendance status
            for employee in employees:
                data = {
                    "id": employee.id,
                    "name": f"{employee.admin.first_name} {employee.admin.last_name}"
                }
                employee_data.append(data)
        
        # Return employee data directly as JSON without double encoding
        return JsonResponse(employee_data, safe=False)
    except Department.DoesNotExist:
        return JsonResponse({"success": False, "message": "Department not found"}, status=404)
    except Exception as e:
        print(f"Error in get_employees: {e}")
        return JsonResponse({"success": False, "message": f"Error fetching employees: {str(e)}"}, status=500)



@csrf_exempt
def save_attendance(request):
    employee_ids_json = request.POST.get('employee_ids')
    date_str = request.POST.get('date')
    department_id = request.POST.get('department')
    
    # Debug logging of request parameters
    print(f"Save Attendance Request - Date: {date_str}, Department ID: {department_id}")
    print(f"Employee IDs JSON length: {len(employee_ids_json) if employee_ids_json else 'None'}")
    
    if not department_id or not date_str or not employee_ids_json:
        missing = []
        if not department_id: missing.append("department_id")
        if not date_str: missing.append("date")
        if not employee_ids_json: missing.append("employee_ids")
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
        
        employees = json.loads(employee_ids_json)
        print(f"Successfully parsed employee_ids JSON. Found {len(employees)} employees")
        
        # Validate employee data structure
        if not isinstance(employees, list):
            error_msg = "Employee data must be a list"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        if len(employees) == 0:
            error_msg = "No employees provided in the request"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        for i, emp in enumerate(employees):
            if not isinstance(emp, dict) or 'id' not in emp or 'status' not in emp:
                error_msg = f"Invalid employee data format at index {i}"
                print(error_msg, emp)
                return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        try:
            department = Department.objects.get(id=department_id)
            print(f"Found department: {department.name} (ID: {department.id})")
        except Department.DoesNotExist:
            error_msg = f"Department with ID {department_id} not found"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=404)

        # Check if an attendance object already exists for the given date
        try:
            attendance, created = Attendance.objects.get_or_create(department=department, date=date_obj)
            print(f"Attendance record {'created' if created else 'found'} for date {date_obj}")
        except Exception as e:
            error_msg = f"Error creating/getting attendance record: {str(e)}"
            print(error_msg)
            return JsonResponse({"success": False, "message": error_msg}, status=500)

        saved_count = 0
        error_count = 0
        error_messages = []
        
        for employee_dict in employees:
            try:
                employee_id = employee_dict.get('id')
                status_value = employee_dict.get('status')
                
                print(f"Processing employee ID: {employee_id}, Status: {status_value}")
                
                try:
                    employee = Employee.objects.get(id=employee_id)
                    print(f"Found employee: {employee.admin.first_name} {employee.admin.last_name} (ID: {employee.id})")
                except Employee.DoesNotExist:
                    error_msg = f"Employee with ID {employee_id} not found"
                    print(error_msg)
                    error_messages.append(error_msg)
                    error_count += 1
                    continue

                # Check if an attendance report already exists for the employee and the attendance object
                try:
                    attendance_report, report_created = AttendanceReport.objects.get_or_create(
                        employee=employee, 
                        attendance=attendance,
                        defaults={'status': status_value == 1}
                    )
                    print(f"Attendance report {'created' if report_created else 'updated'} for employee {employee.id}")

                    # Always update the status regardless of whether it was created or already existed
                    if not report_created:
                        attendance_report.status = status_value == 1  # Convert to boolean
                        attendance_report.save()
                        print(f"Updated status to {status_value == 1} for existing report")
                        
                    saved_count += 1
                except Exception as e:
                    error_msg = f"Error saving attendance report for employee {employee_id}: {str(e)}"
                    print(error_msg)
                    error_messages.append(error_msg)
                    error_count += 1
            except Exception as e:
                error_msg = f"Error processing employee {employee_dict.get('id', 'unknown')}: {str(e)}"
                print(error_msg)
                error_messages.append(error_msg)
                error_count += 1

        if saved_count > 0:
            success_msg = f"Successfully saved attendance for {saved_count} employees"
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
        print(f"Problematic JSON: {employee_ids_json[:100]}...")
        return JsonResponse({"success": False, "message": error_msg}, status=400)
    except Exception as e:
        error_msg = f"Error saving attendance: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "message": error_msg}, status=500)


def manager_update_attendance(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'departments': departments,
        'page_title': 'Update Attendance'
    }

    return render(request, 'manager_template/manager_update_attendance.html', context)


@csrf_exempt
def get_employee_attendance(request):
    department_id = request.POST.get('department')
    attendance_date = request.POST.get('date')
    
    print(f"Get Employee Attendance - Department ID: {department_id}, Date: {attendance_date}")
    
    if not department_id or not attendance_date:
        error_msg = "Missing required parameters: department and date"
        print(error_msg)
        return JsonResponse({"error": error_msg}, status=400)
    
    try:
        # Get the department
        department = Department.objects.get(id=department_id)
        print(f"Found department: {department.name}")
        
        # Parse the date
        try:
            parsed_date = datetime.strptime(attendance_date, "%Y-%m-%d").date()
            print(f"Parsed date: {parsed_date}")
        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}"
            print(error_msg)
            return JsonResponse({"error": error_msg}, status=400)
        
        # Get all employees for this department
        employees = Employee.objects.filter(department=department)
        print(f"Found {employees.count()} employees in department")
        
        # Get the attendance record for this date
        attendance, created = Attendance.objects.get_or_create(
            department=department,
            date=parsed_date
        )
        print(f"Attendance record {'created' if created else 'found'} for date {parsed_date}")
        
        # Get attendance reports for all employees
        attendance_data = AttendanceReport.objects.filter(attendance=attendance)
        print(f"Found {attendance_data.count()} attendance reports for this date")
        
        # Create a dictionary to quickly look up attendance status by employee ID
        attendance_status = {}
        for report in attendance_data:
            attendance_status[report.employee.id] = report.status
        
        # Create a list of all employees with their attendance status
        employee_data = []
        for employee in employees:
            status = attendance_status.get(employee.id, False)  # Default to absent if no record exists
            data = {
                "id": employee.id,
                "name": f"{employee.admin.last_name}, {employee.admin.first_name}",
                "status": status
            }
            employee_data.append(data)
        
        print(f"Returning data for {len(employee_data)} employees")
        return JsonResponse(employee_data, safe=False)
    except Department.DoesNotExist:
        error_msg = f"Department with ID {department_id} not found"
        print(error_msg)
        return JsonResponse({"error": error_msg}, status=404)
    except Exception as e:
        error_msg = f"Error retrieving attendance data: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": error_msg}, status=500)


@csrf_exempt
def update_attendance(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method Not Allowed"}, status=405)
        
    department_id = request.POST.get('department')
    attendance_date = request.POST.get('date')
    employee_ids_json = request.POST.get('employee_ids')
    
    print("=== UPDATE ATTENDANCE REQUEST ===")
    print(f"Department ID: {department_id}")
    print(f"Date: {attendance_date}")
    print(f"Employee IDs JSON: {employee_ids_json}")
    
    if not department_id or not attendance_date or not employee_ids_json:
        missing = []
        if not department_id: missing.append("department_id")
        if not attendance_date: missing.append("date")
        if not employee_ids_json: missing.append("employee_ids")
        error_msg = f"Missing required parameters: {', '.join(missing)}"
        print(f"Validation Error: {error_msg}")
        return JsonResponse({"success": False, "message": error_msg}, status=400)
    
    try:
        # Parse the date
        try:
            parsed_date = datetime.strptime(attendance_date, "%Y-%m-%d").date()
            print(f"Successfully parsed date: {parsed_date}")
        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}"
            print(f"Date Parse Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        today = datetime.now().date()
        if parsed_date > today:
            error_msg = "Cannot update attendance for future dates"
            print(f"Date Validation Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        # Past and today are allowed
        
        # Get the department
        try:
            department = Department.objects.get(id=department_id)
            print(f"Found department: {department.name} (ID: {department.id})")
        except Department.DoesNotExist:
            error_msg = f"Department with ID {department_id} not found"
            print(f"Department Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=404)
        
        # Parse employee data
        try:
            employee_ids = json.loads(employee_ids_json)
            print(f"Successfully parsed {len(employee_ids)} employee records")
            print(f"Employee data: {employee_ids}")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON data: {str(e)}"
            print(f"JSON Parse Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        # Validate employee data structure
        if not isinstance(employee_ids, list):
            error_msg = "Employee data must be a list"
            print(f"Data Structure Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        if len(employee_ids) == 0:
            error_msg = "No employees provided in the request"
            print(f"Data Validation Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=400)
            
        for i, emp in enumerate(employee_ids):
            if not isinstance(emp, dict) or 'id' not in emp or 'status' not in emp:
                error_msg = f"Invalid employee data format at index {i}: {emp}"
                print(f"Employee Data Error: {error_msg}")
                return JsonResponse({"success": False, "message": error_msg}, status=400)
        
        # Get or create attendance record for the date
        try:
            attendance, created = Attendance.objects.get_or_create(
                department=department,
                date=parsed_date
            )
            print(f"Attendance record {'created' if created else 'found'} for date {parsed_date}")
            print(f"Attendance ID: {attendance.id}")
        except Exception as e:
            error_msg = f"Error creating/getting attendance record: {str(e)}"
            print(f"Attendance Creation Error: {error_msg}")
            return JsonResponse({"success": False, "message": error_msg}, status=500)
        
        # Process each employee's attendance status
        updated_count = 0
        created_count = 0
        error_count = 0
        error_messages = []
        
        for employee_data in employee_ids:
            try:
                employee_id = employee_data.get('id')
                status_value = employee_data.get('status')
                
                print(f"\nProcessing employee ID: {employee_id}, Status: {status_value}")
                
                try:
                    employee = Employee.objects.get(id=employee_id)
                    print(f"Found employee: {employee.admin.first_name} {employee.admin.last_name} (ID: {employee.id})")
                except Employee.DoesNotExist:
                    error_msg = f"Employee with ID {employee_id} not found"
                    print(f"Employee Lookup Error: {error_msg}")
                    error_messages.append(error_msg)
                    error_count += 1
                    continue
                
                try:
                    # Get or create attendance report
                    attendance_report, created = AttendanceReport.objects.get_or_create(
                        employee=employee,
                        attendance=attendance,
                        defaults={'status': status_value == 1}
                    )
                    
                    if created:
                        created_count += 1
                        print(f"Created new attendance report for employee {employee_id}")
                    else:
                        # Update existing report
                        attendance_report.status = status_value == 1
                        attendance_report.save()
                        print(f"Updated attendance report for employee {employee_id}")
                    
                    updated_count += 1
                except Exception as e:
                    error_msg = f"Error saving attendance report for employee {employee_id}: {str(e)}"
                    print(f"Attendance Report Error: {error_msg}")
                    error_messages.append(error_msg)
                    error_count += 1
                    continue
                    
            except Exception as e:
                error_msg = f"Unexpected error processing employee {employee_data.get('id', 'unknown')}: {str(e)}"
                print(f"Unexpected Error: {error_msg}")
                error_messages.append(error_msg)
                error_count += 1
                continue
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Successfully processed {updated_count} attendance records ({created_count} created)",
            "stats": {
                "total_processed": len(employee_ids),
                "updated": updated_count,
                "created": created_count,
                "errors": error_count
            }
        }
        
        if error_messages:
            response_data["errors"] = error_messages[:5]  # Include only first 5 errors
            
        print("\n=== UPDATE ATTENDANCE RESPONSE ===")
        print(f"Response data: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"\n=== CRITICAL ERROR ===")
        print(error_msg)
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "message": error_msg}, status=500)


def manager_apply_leave(request):
    form = LeaveReportManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportManager.objects.filter(manager=manager),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('manager_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_apply_leave.html", context)


def manager_feedback(request):
    form = FeedbackManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackManager.objects.filter(manager=manager),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('manager_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_feedback.html", context)


def manager_view_profile(request):
    manager = get_object_or_404(Manager, admin=request.user)
    form = ManagerEditForm(request.POST or None, request.FILES or None,instance=manager)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = manager.admin
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
                manager.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('manager_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "manager_template/manager_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "manager_template/manager_view_profile.html", context)

    return render(request, "manager_template/manager_view_profile.html", context)


@csrf_exempt
def manager_fcmtoken(request):
    token = request.POST.get('token')
    try:
        manager_user = get_object_or_404(CustomUser, id=request.user.id)
        manager_user.fcm_token = token
        manager_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def manager_view_notification(request):
    manager = get_object_or_404(Manager, admin=request.user)
    notifications = NotificationManager.objects.filter(manager=manager)
    
    # Mark all notifications as read when viewed
    unread_notifications = NotificationManager.objects.filter(manager=manager, read=False)
    for notification in unread_notifications:
        notification.read = True
        notification.save()
    
    context = {
        'notifications': notifications,
        'page_title': 'View Notifications'
    }
    return render(request, "manager_template/manager_view_notification.html", context)


@csrf_exempt
def manager_view_attendance(request):
    if request.method != 'POST':
        context = {
            'page_title': 'View My Attendance'
        }
        return render(request, "manager_template/manager_view_attendance.html", context)
    else:
        # Get date range from POST request
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Get current manager
        manager = get_object_or_404(Manager, admin=request.user)
        
        # Get all attendance records for departments in this manager's division
        departments = Department.objects.filter(division=manager.division)
        attendance_objects = Attendance.objects.filter(
            department__in=departments,
            date__range=(start_date, end_date)
        ).order_by('date')
        
        attendance_data = []
        
        # Check manager's attendance for each date
        for attendance in attendance_objects:
            try:
                # Look for attendance record for this manager
                report = AttendanceReport.objects.get(
                    attendance=attendance,
                    manager=manager
                )
                data = {
                    'date': attendance.date.strftime('%Y-%m-%d'),
                    'status': report.status
                }
                attendance_data.append(data)
            except AttendanceReport.DoesNotExist:
                # If no record exists for this date, consider absent
                data = {
                    'date': attendance.date.strftime('%Y-%m-%d'),
                    'status': False
                }
                attendance_data.append(data)
        
        return JsonResponse(json.dumps(attendance_data), safe=False)


def manager_add_salary(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'page_title': 'Add Employee Salary',
        'departments': departments
    }
    return render(request, 'manager_template/manager_add_salary.html', context)


@csrf_exempt
def fetch_employee_salary(request):
    if request.method == 'POST':
        department_id = request.POST.get('department')
        employee_id = request.POST.get('employee')
        
        try:
            if department_id:
                # Get all salaries for employees in this department's division
                department = get_object_or_404(Department, id=department_id)
                salaries = Salary.objects.filter(
                    employee__division=department.division
                ).select_related('employee', 'employee__admin').order_by('-month_year')
                
                salary_list = []
                for salary in salaries:
                    try:
                        leave_payment = 0
                        # Handle case where leave_payment column might not exist yet
                        try:
                            if hasattr(salary, 'leave_payment') and salary.leave_payment is not None:
                                leave_payment = float(salary.leave_payment)
                        except (AttributeError, TypeError):
                            leave_payment = 0
                            
                        salary_data = {
                            'id': salary.id,  # Include salary ID
                            'employee_id': salary.employee.id,  # Include employee ID
                            'employee_name': f"{salary.employee.admin.last_name}, {salary.employee.admin.first_name}",
                            'month_year': salary.month_year.strftime('%Y-%m-%d'),
                            'basic_salary': float(salary.basic_salary),
                            'meal_allowance': float(salary.meal_allowance),
                            'medical_allowance': float(salary.medical_allowance),
                            'transportation_allowance': float(salary.transportation_allowance),
                            'leave_payment': leave_payment,
                            'tax_amount': float(salary.tax_amount),
                            'insurance_amount': float(salary.insurance_amount),
                            'total_earnings': float(salary.total_earnings),
                            'total_deductions': float(salary.total_deductions),
                            'net_salary': float(salary.net_salary),
                            'status': salary.status
                        }
                        salary_list.append(salary_data)
                    except Exception as e:
                        print(f"Error processing salary {salary.id}: {str(e)}")
                        continue
                
                return JsonResponse({
                    'success': True,
                    'salaries': salary_list,
                    'message': None if salary_list else 'No salary records found for this department'
                })
            
            elif employee_id:
                # Get single employee salary
                try:
                    salary = Salary.objects.filter(employee_id=employee_id).latest('month_year')
                    
                    # Handle case where leave_payment column might not exist yet
                    leave_payment = 0
                    try:
                        if hasattr(salary, 'leave_payment') and salary.leave_payment is not None:
                            leave_payment = float(salary.leave_payment)
                    except (AttributeError, TypeError):
                        leave_payment = 0
                        
                    data = {
                        'success': True,
                        'salary': {
                            'basic_salary': float(salary.basic_salary),
                            'meal_allowance': float(salary.meal_allowance),
                            'medical_allowance': float(salary.medical_allowance),
                            'transportation_allowance': float(salary.transportation_allowance),
                            'leave_payment': leave_payment,
                            'tax_amount': float(salary.tax_amount),
                            'insurance_amount': float(salary.insurance_amount),
                            'total_earnings': float(salary.total_earnings),
                            'total_deductions': float(salary.total_deductions),
                            'net_salary': float(salary.net_salary)
                        }
                    }
                    return JsonResponse(data)
                except Salary.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'No salary record found for this employee'
                    })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Either department_id or employee_id is required'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

@csrf_exempt
def save_salary(request):
    if request.method == 'POST':
        try:
            data = request.POST
            employee = get_object_or_404(Employee, id=data.get('employee'))
            month_year = data.get('month_year') + "-01"  # Add day to make a valid date
            
            # Check if the employee already has a paid salary for this month
            existing_salary = Salary.objects.filter(
                employee=employee,
                month_year=month_year,
                status='paid'
            ).first()
            
            if existing_salary:
                # Format month/year from the existing salary for readability
                formatted_date = existing_salary.month_year.strftime('%B %Y')
                
                # Get employee name
                employee_name = f"{employee.admin.last_name}, {employee.admin.first_name}"
                
                return JsonResponse({
                    'success': False,
                    'message': f'ALERT: {employee_name} already has a PAID salary record for {formatted_date}. Cannot add duplicate entry.',
                    'details': {
                        'employee_id': employee.id,
                        'employee_name': employee_name,
                        'month_year': formatted_date,
                        'status': existing_salary.status,
                        'payment_date': existing_salary.payment_date.strftime('%d-%m-%Y') if existing_salary.payment_date else 'Not set'
                    }
                }, status=400)
            
            # Validate numeric fields
            basic_salary = float(data.get('basic_salary', 0))
            meal_allowance = float(data.get('meal_allowance', 0))
            medical_allowance = float(data.get('medical_allowance', 0))
            transportation_allowance = float(data.get('transportation_allowance', 0))
            leave_payment = float(data.get('leave_payment', 0)) if data.get('leave_payment') else None
            
            if basic_salary <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Basic salary must be greater than 0'
                }, status=400)
            
            try:
                # Try to create or update salary record with leave_payment
                salary, created = Salary.objects.update_or_create(
                    employee=employee,
                    month_year=month_year,
                    defaults={
                        'basic_salary': basic_salary,
                        'meal_allowance': meal_allowance,
                        'medical_allowance': medical_allowance,
                        'transportation_allowance': transportation_allowance,
                        'leave_payment': leave_payment,
                        'tax_percentage': 13,  # Default tax percentage
                        'insurance_percentage': 5,  # Default insurance percentage
                        'status': 'pending'  # Default status
                    }
                )
            except Exception as e:
                # If there was an error (likely due to missing leave_payment column),
                # try again without leave_payment
                if "leave_payment" in str(e).lower():
                    salary, created = Salary.objects.update_or_create(
                        employee=employee,
                        month_year=month_year,
                        defaults={
                            'basic_salary': basic_salary,
                            'meal_allowance': meal_allowance,
                            'medical_allowance': medical_allowance,
                            'transportation_allowance': transportation_allowance,
                            'tax_percentage': 13,  # Default tax percentage
                            'insurance_percentage': 5,  # Default insurance percentage
                            'status': 'pending'  # Default status
                        }
                    )
                else:
                    # If it's some other error, re-raise it
                    raise
            
            # Calculate all values
            salary.refresh_from_db()
            
            # Manually set leave_payment if it doesn't exist in the DB
            if not hasattr(salary, 'leave_payment'):
                salary.leave_payment = leave_payment
            
            # Compute leave_payment value for response
            leave_payment_value = 0
            if hasattr(salary, 'leave_payment') and salary.leave_payment is not None:
                leave_payment_value = float(salary.leave_payment)
            
            # Return success response with the saved salary data
            return JsonResponse({
                'success': True,
                'message': 'Salary saved successfully',
                'salary': {
                    'employee_name': f"{employee.admin.last_name}, {employee.admin.first_name}",
                    'month_year': salary.month_year.strftime('%Y-%m-%d'),
                    'basic_salary': float(salary.basic_salary),
                    'meal_allowance': float(salary.meal_allowance),
                    'medical_allowance': float(salary.medical_allowance),
                    'transportation_allowance': float(salary.transportation_allowance),
                    'leave_payment': leave_payment_value,
                    'tax_amount': float(salary.tax_amount),
                    'insurance_amount': float(salary.insurance_amount),
                    'total_earnings': float(salary.total_earnings),
                    'total_deductions': float(salary.total_deductions),
                    'net_salary': float(salary.net_salary),
                    'status': salary.status
                }
            })
        except Employee.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Employee not found'
            }, status=404)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': 'Invalid salary amount. Please enter valid numbers.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to save salary: {str(e)}'
            }, status=400)
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

def manager_assign_task(request):
    manager = get_object_or_404(Manager, admin=request.user)
    employees = Employee.objects.filter(division=manager.division)

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.manager = manager
            task.save()
            messages.success(request, "Task assigned successfully!")
            return redirect('manager_view_tasks')
    else:
        form = TaskForm()

    context = {'form': form, 'employees': employees}
    return render(request, 'manager_template/assign_task.html', context)

def manager_view_tasks(request):
    manager = get_object_or_404(Manager, admin=request.user)
    tasks = Task.objects.filter(manager=manager)

    context = {'tasks': tasks}
    return render(request, 'manager_template/view_tasks.html', context)

def update_task_rating(request):
    if request.method == "POST":
        task_id = request.POST.get("task_id")
        rating = request.POST.get("rating")
        task = get_object_or_404(Task, id=task_id)

        # Save rating in database
        task.rating = int(rating)
        task.save()

        return JsonResponse({"success": True})
    return JsonResponse({"success": False})

@csrf_exempt
def update_salary_status(request):
    if request.method == 'POST':
        try:
            salary_id = request.POST.get('salary_id')
            new_status = request.POST.get('status')
            
            # Validate status
            if new_status not in ['pending', 'paid']:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status value'
                }, status=400)
            
            # Find and update the salary record
            salary = get_object_or_404(Salary, id=salary_id)
            
            # Update status and payment date if paid
            salary.status = new_status
            if new_status == 'paid':
                salary.payment_date = datetime.now().date()
            else:
                salary.payment_date = None
            
            salary.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Status updated successfully'
            })
            
        except Salary.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Salary record not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to update status: {str(e)}'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

@csrf_exempt
def delete_salary(request):
    if request.method == 'POST':
        try:
            salary_id = request.POST.get('salary_id')
            
            # Get the salary record
            salary = get_object_or_404(Salary, id=salary_id)
            
            # Check if the salary is already paid
            if salary.status == 'paid':
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot delete PAID salary record for {salary.employee.admin.last_name}, {salary.employee.admin.first_name} ({salary.month_year.strftime("%B %Y")})'
                }, status=400)
            
            # Store info for response
            employee_name = f"{salary.employee.admin.last_name}, {salary.employee.admin.first_name}"
            month_year = salary.month_year.strftime('%B %Y')
            
            # Delete the salary record
            salary.delete()
            
            # Return success response
            return JsonResponse({
                'success': True,
                'message': f'Salary record for {employee_name} ({month_year}) deleted successfully',
                'employee_name': employee_name,
                'month_year': month_year
            })
            
        except Salary.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Salary record not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to delete salary: {str(e)}'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

@csrf_exempt
def get_employee_stats(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        month_year = request.POST.get('month_year')
        
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            
            # Parse the month_year string to datetime
            date_parts = month_year.split('-')
            year = int(date_parts[0])
            month = int(date_parts[1])
            
            # Get the first and last day of the month
            first_day = datetime(year, month, 1)
            last_day = datetime(year, month, calendar.monthrange(year, month)[1])
            
            # Get attendance records for the month
            attendances = Attendance.objects.filter(
                date__gte=first_day,
                date__lte=last_day,
                department=employee.department
            )
            
            # Count present days
            present_count = AttendanceReport.objects.filter(
                attendance__in=attendances,
                employee=employee,
                status=True
            ).count()
            
            # Count absent days
            absent_count = AttendanceReport.objects.filter(
                attendance__in=attendances,
                employee=employee,
                status=False
            ).count()
            
            # Get approved leave count for this month
            leave_count = LeaveReportEmployee.objects.filter(
                employee=employee,
                status=1,  # Approved leave
                date_from__gte=first_day.date(),
                date_from__lte=last_day.date()
            ).count()
            
            # Get total working days in the month
            total_attendance_days = attendances.count()
            
            # Calculate attendance percentage
            attendance_percentage = 0
            if total_attendance_days > 0:
                attendance_percentage = round((present_count / total_attendance_days) * 100)
            
            # Get the month name for display
            month_name = first_day.strftime('%B %Y')
            
            return JsonResponse({
                'success': True,
                'stats': {
                    'present_count': present_count,
                    'absent_count': absent_count,
                    'leave_count': leave_count,
                    'total_days': total_attendance_days,
                    'attendance_percentage': attendance_percentage,
                    'month_name': month_name
                }
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

def manager_notification_count(request):
    manager = get_object_or_404(Manager, admin=request.user)
    notification_count = NotificationManager.objects.filter(manager=manager, read=False).count()
    return JsonResponse({"notification_count": notification_count})

def manager_feedback_count(request):
    manager = get_object_or_404(Manager, admin=request.user)
    feedback_count = FeedbackManager.objects.filter(manager=manager, reply="").count()
    return JsonResponse({"feedback_count": feedback_count})

def manager_leave_count(request):
    manager = get_object_or_404(Manager, admin=request.user)
    leave_count = LeaveReportManager.objects.filter(manager=manager, status=0).count()
    return JsonResponse({"leave_count": leave_count})

@csrf_exempt
def get_employee_leave_stats(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        month_year = request.POST.get('month_year')
        
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            
            if not month_year:
                return JsonResponse({
                    'success': False,
                    'message': 'Month/year parameter is required'
                }, status=400)
            
            # Parse month_year (format: YYYY-MM)
            year, month = map(int, month_year.split('-'))
            
            # Get the first and last day of the month
            first_day = datetime(year, month, 1).date()
            last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
            
            # Month name for display
            month_name = first_day.strftime('%B %Y')
            
            # Filter leaves that overlap with the month
            # A leave overlaps with the month if:
            # - date_from is within the month, OR
            # - date_to is within the month, OR
            # - date_from is before the month starts AND date_to is after the month ends
            month_leaves = LeaveReportEmployee.objects.filter(
                employee=employee
            ).filter(
                Q(date_from__gte=first_day, date_from__lte=last_day) |
                Q(date_to__gte=first_day, date_to__lte=last_day) |
                Q(date_from__lte=first_day, date_to__gte=last_day)
            )
            
            # Count leaves by type and status
            total_leaves = month_leaves.count()
            sick_leaves = month_leaves.filter(leave_type='sick').count()
            annual_leaves = month_leaves.filter(leave_type='annual').count()
            
            approved_leaves = month_leaves.filter(status=1).count()
            pending_leaves = month_leaves.filter(status=0).count()
            rejected_leaves = month_leaves.filter(status=-1).count()
            
            # Calculate total leave days in the month
            total_leave_days = 0
            for leave in month_leaves:
                # Ensure date range is within month boundaries
                start_date = max(leave.date_from, first_day)
                end_date = min(leave.date_to, last_day)
                
                # Calculate days difference (inclusive of start and end dates)
                days_count = (end_date - start_date).days + 1
                total_leave_days += days_count
            
            # Get leave data for display
            leave_details = []
            for leave in month_leaves.filter(status=1):  # Only approved leaves
                leave_details.append({
                    'type': leave.leave_type,
                    'from': leave.date_from.strftime('%d-%m-%Y'),
                    'to': leave.date_to.strftime('%d-%m-%Y'),
                    'days': (leave.date_to - leave.date_from).days + 1
                })
            
            return JsonResponse({
                'success': True,
                'stats': {
                    'month_name': month_name,
                    'total_leaves': total_leaves,
                    'sick_leaves': sick_leaves,
                    'annual_leaves': annual_leaves,
                    'approved_leaves': approved_leaves,
                    'pending_leaves': pending_leaves,
                    'rejected_leaves': rejected_leaves,
                    'total_leave_days': total_leave_days,
                    'leave_details': leave_details
                }
            })
        
        except ValueError as ve:
            return JsonResponse({
                'success': False,
                'message': f'Invalid month/year format: {str(ve)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

