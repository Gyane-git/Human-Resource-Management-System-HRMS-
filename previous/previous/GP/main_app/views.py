import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .EmailBackend import EmailBackend
from .models import Attendance, Department, Employee, Task, CustomUser, AttendanceReport, Division, FeedbackManager, FeedbackEmployee, LeaveReportManager, LeaveReportEmployee, NotificationManager, NotificationEmployee, Manager
from .decorators import ceo_required, employee_required


# Create your views here.


def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("manager_home"))
        elif request.user.user_type == '3':
            return redirect(reverse("employee_home"))
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        #Google recaptcha
        captcha_token = request.POST.get('g-recaptcha-response')
        captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        captcha_key = "6Lf9RfcnAAAAAIn2o_U8h3KQwb3lVMeDvenBCXYp"
        data = {
            'secret': captcha_key,
            'response': captcha_token
        }
        # Make request
        try:
            captcha_server = requests.post(url=captcha_url, data=data)
            response = json.loads(captcha_server.text)
            if response['success'] == False:
                messages.error(request, 'Invalid Captcha. Try Again')
                return redirect('/')
        except:
            messages.error(request, 'Captcha could not be verified. Try Again')
            return redirect('/')
        
        #Authenticate
        user = EmailBackend.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user != None:
            login(request, user)
            if user.user_type == '1':
                return redirect(reverse("admin_home"))
            elif user.user_type == '2':
                return redirect(reverse("manager_home"))
            elif user.user_type == '3':
                return redirect(reverse("employee_home"))
        else:
            messages.error(request, "Invalid details")
            return redirect("/")



def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    if request.method != 'POST':
        return HttpResponse("Invalid Method")
    
    # Get filter parameters - either department or division
    department_id = request.POST.get('department')
    division_id = request.POST.get('division')
    
    if department_id:
        # Filter by department (for employees)
        department = Department.objects.get(id=department_id)
        attendance_list = Attendance.objects.filter(department=department)
    elif division_id:
        # Filter by division (for managers)
        division = Division.objects.get(id=division_id)
        # Get departments in this division
        departments = Department.objects.filter(division=division)
        # Get attendance for these departments
        attendance_list = Attendance.objects.filter(department__in=departments)
    else:
        return HttpResponse(json.dumps([]))
    
    attendance_data = []
    for attendance in attendance_list:
        data = {
            "id": attendance.id,
            "attendance_date": str(attendance.date),
            "department": attendance.department.name
        }
        attendance_data.append(data)
    
    return HttpResponse(json.dumps(attendance_data))


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')



from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
import os
from datetime import datetime
from .models import Employee, Attendance, Task, AttendanceReport
from django.db.models import Avg

@login_required
@ceo_required
def ceo_rank_report(request):
    error_message = None
    if request.method == 'POST':
        month = request.POST.get('month')
        year = request.POST.get('year')
        
        try:
            # Get all employees
            employees = Employee.objects.all()
            employee_rankings = []
            
            for employee in employees:
                # Calculate attendance metrics
                attendances = Attendance.objects.filter(
                    department=employee.department,
                    date__year=year,
                    date__month=month
                )
                
                total_days = attendances.count()
                present_days = AttendanceReport.objects.filter(
                    attendance__in=attendances, 
                    status=True, 
                    employee=employee
                ).count()
                absent_days = total_days - present_days
                attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
                
                # Calculate task metrics
                tasks = Task.objects.filter(
                    employee=employee,
                    deadline__year=year,
                    deadline__month=month
                )
                
                total_tasks = tasks.count()
                completed_tasks = tasks.filter(status='Completed').count()
                average_rating = tasks.aggregate(Avg('rating'))['rating__avg'] or 0
                
                # Calculate score (customize this formula as needed)
                score = (attendance_percentage * 0.4) + (average_rating * 20 * 0.6)
                
                employee_rankings.append({
                    'employee': employee,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'attendance_percentage': attendance_percentage,
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'average_rating': average_rating,
                    'score': score
                })
            
            # Sort employees by score (descending)
            employee_rankings.sort(key=lambda x: x['score'], reverse=True)
            
            # Generate PDF
            template = get_template('ceo_template/ceo_rank_report_pdf.html')
            context = {
                'employee_rankings': employee_rankings,
                'month': datetime.strptime(month, "%m").strftime("%B"),
                'year': year,
                'generated_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            html = template.render(context)
            
            # Create PDF
            response = HttpResponse(content_type='application/pdf')
            filename = f"CEO_Rank_Report_{month}_{year}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Generate PDF
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                error_message = 'Error generating CEO report'
                # Fall through to the GET response below
            else:
                # Save PDF to media directory
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'ceo_reports', filename)
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                with open(pdf_path, 'wb') as pdf_file:
                    pisa.CreatePDF(html, dest=pdf_file)
                
                return response
            
        except Exception as e:
            error_message = str(e)
    
    # GET request or error in POST handling
    current_month = datetime.now().month
    current_year = datetime.now().year
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    years = range(datetime.now().year - 5, datetime.now().year + 1)
    
    return render(request, 'ceo_template/ceo_rank_report.html', {
        'months': months,
        'years': years,
        'current_month': current_month,
        'current_year': current_year,
        'error_message': error_message
    })

@login_required
@employee_required
def employee_rank_report(request):
    error_message = None
    if request.method == 'POST':
        month = request.POST.get('month')
        year = request.POST.get('year')
        
        try:
            employee = request.user.employee
            
            # Calculate attendance metrics
            attendances = Attendance.objects.filter(
                department=employee.department,
                date__year=year,
                date__month=month
            )
            
            total_days = attendances.count()
            present_days = AttendanceReport.objects.filter(
                attendance__in=attendances, 
                status=True, 
                employee=employee
            ).count()
            absent_days = total_days - present_days
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
            
            # Calculate task metrics
            tasks = Task.objects.filter(
                employee=employee,
                deadline__year=year,
                deadline__month=month
            )
            
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(status='Completed').count()
            average_rating = tasks.aggregate(Avg('rating'))['rating__avg'] or 0
            
            # Generate PDF
            template = get_template('employee_template/employee_rank_report_pdf.html')
            context = {
                'employee': employee,
                'present_days': present_days,
                'absent_days': absent_days,
                'attendance_percentage': attendance_percentage,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'average_rating': average_rating,
                'month': datetime.strptime(month, "%m").strftime("%B"),
                'year': year,
                'generated_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            html = template.render(context)
            
            # Create PDF
            response = HttpResponse(content_type='application/pdf')
            filename = f"Employee_Rank_Report_{employee.id}_{month}_{year}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Generate PDF
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                error_message = 'Error generating employee report'
                # Fall through to the GET response below
            else:
                # Save PDF to media directory
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'employee_reports', filename)
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                with open(pdf_path, 'wb') as pdf_file:
                    pisa.CreatePDF(html, dest=pdf_file)
                
                return response
            
        except Exception as e:
            error_message = str(e)
    
    # GET request or error in POST handling
    current_month = datetime.now().month
    current_year = datetime.now().year
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    years = range(datetime.now().year - 5, datetime.now().year + 1)
    
    return render(request, 'employee_template/employee_rank_report.html', {
        'months': months,
        'years': years,
        'current_month': current_month,
        'current_year': current_year,
        'error_message': error_message
    })

# Function to get notification and counts for templates
def get_user_context_data(request, context={}):
    """Add notification, feedback and leave counts to context data based on user type"""
    if request.user.is_authenticated:
        if request.user.user_type == '1':  # Admin
            context['manager_feedback_count'] = FeedbackManager.objects.filter(reply="").count()
            context['employee_feedback_count'] = FeedbackEmployee.objects.filter(reply="").count()
            context['manager_leave_count'] = LeaveReportManager.objects.filter(status=0).count()
            context['employee_leave_count'] = LeaveReportEmployee.objects.filter(status=0).count()
        elif request.user.user_type == '2':  # Manager
            manager = Manager.objects.get(admin=request.user)
            context['notification_count'] = NotificationManager.objects.filter(manager=manager, read=False).count()
            context['feedback_count'] = FeedbackManager.objects.filter(manager=manager, reply="").count()
            context['pending_leave_count'] = LeaveReportManager.objects.filter(manager=manager, status=0).count()
        elif request.user.user_type == '3':  # Employee
            employee = Employee.objects.get(admin=request.user)
            context['notification_count'] = NotificationEmployee.objects.filter(employee=employee, read=False).count()
            context['feedback_count'] = FeedbackEmployee.objects.filter(employee=employee, reply="").count()
            context['pending_leave_count'] = LeaveReportEmployee.objects.filter(employee=employee, status=0).count()
            context['task_count'] = Task.objects.filter(employee=employee, status="Pending").count()
    return context


