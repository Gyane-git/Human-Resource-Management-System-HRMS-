from .models import (
    FeedbackManager, FeedbackEmployee, 
    LeaveReportManager, LeaveReportEmployee, 
    NotificationManager, NotificationEmployee,
    Manager, Employee, Task
)

def user_notifications(request):
    """Context processor to add notification counts to all templates"""
    context = {}
    
    if request.user.is_authenticated:
        if request.user.user_type == '1':  # Admin
            context['manager_feedback_count'] = FeedbackManager.objects.filter(reply="").count()
            context['employee_feedback_count'] = FeedbackEmployee.objects.filter(reply="").count()
            context['manager_leave_count'] = LeaveReportManager.objects.filter(status=0).count()
            context['employee_leave_count'] = LeaveReportEmployee.objects.filter(status=0).count()
        
        elif request.user.user_type == '2':  # Manager
            try:
                manager = Manager.objects.get(admin=request.user)
                context['notification_count'] = NotificationManager.objects.filter(manager=manager, read=False).count()
                context['feedback_count'] = FeedbackManager.objects.filter(manager=manager, reply="").count()
                context['pending_leave_count'] = LeaveReportManager.objects.filter(manager=manager, status=0).count()
            except Manager.DoesNotExist:
                pass
        
        elif request.user.user_type == '3':  # Employee
            try:
                employee = Employee.objects.get(admin=request.user)
                context['notification_count'] = NotificationEmployee.objects.filter(employee=employee, read=False).count()
                context['feedback_count'] = FeedbackEmployee.objects.filter(employee=employee, reply="").count()
                context['pending_leave_count'] = LeaveReportEmployee.objects.filter(employee=employee, status=0).count()
                context['task_count'] = Task.objects.filter(employee=employee, status="Pending").count()
            except Employee.DoesNotExist:
                pass
    
    return context 