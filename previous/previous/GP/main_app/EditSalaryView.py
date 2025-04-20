from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.contrib import messages
from .models import Department, Manager, Employee, EmployeeSalary, Salary
from .forms import EditSalaryForm
from django.urls import reverse


class EditSalaryView(View):
    def get(self, request):
        # Get the departments for the form
        manager = request.user.manager
        departments = Department.objects.filter(division=manager.division)
        
        # Check if this is an edit for an existing salary
        salary_id = request.GET.get('salary_id')
        
        if salary_id:
            # Get the existing salary by ID
            salary = get_object_or_404(Salary, id=salary_id)
            
            # Check if salary is paid
            if salary.status == 'paid':
                messages.error(request, "Paid salaries cannot be edited.")
                return redirect('manager_add_salary')
            
            # Safely get leave_payment value
            leave_payment_value = None
            try:
                if hasattr(salary, 'leave_payment'):
                    leave_payment_value = salary.leave_payment
            except (AttributeError, Exception):
                leave_payment_value = None
            
            # Prepare the initial data for the form
            initial_data = {
                'employee': salary.employee,
                'department': salary.employee.department,
                'month_year': salary.month_year,
                'basic_salary': salary.basic_salary,
                'meal_allowance': salary.meal_allowance,
                'medical_allowance': salary.medical_allowance,
                'transportation_allowance': salary.transportation_allowance,
                'leave_payment': leave_payment_value,
            }
            
            # Get the employees for the selected department
            employees = Employee.objects.filter(division=manager.division, department=salary.employee.department)
            
            # Create the form with initial data
            form = EditSalaryForm(initial=initial_data)
            
            context = {
                'form': form,
                'departments': departments,
                'employees': employees,
                'page_title': f'Edit Salary - {salary.employee.admin.last_name}, {salary.employee.admin.first_name} ({salary.month_year.strftime("%B %Y")})',
                'salary_id': salary_id,
                'edit_mode': True
            }
            
            return render(request, 'manager_template/edit_employee_salary.html', context)
        else:
            # No salary_id means we're creating a new salary
            form = EditSalaryForm()
            context = {
                'form': form,
                'departments': departments,
                'page_title': 'Add Employee Salary',
                'edit_mode': False
            }
            
            return render(request, 'manager_template/edit_employee_salary.html', context)
    
    def post(self, request):
        # Get the departments and form data
        manager = request.user.manager
        departments = Department.objects.filter(division=manager.division)
        
        # Get form data
        employee_id = request.POST.get('employee')
        month_year = request.POST.get('month_year')
        basic_salary = request.POST.get('basic_salary')
        meal_allowance = request.POST.get('meal_allowance')
        medical_allowance = request.POST.get('medical_allowance')
        transportation_allowance = request.POST.get('transportation_allowance')
        leave_payment = request.POST.get('leave_payment')
        salary_id = request.POST.get('salary_id')
        
        # Check if we're editing an existing salary
        if salary_id:
            salary = get_object_or_404(Salary, id=salary_id)
            
            # Prevent editing paid salaries
            if salary.status == 'paid':
                messages.error(request, "Paid salaries cannot be edited.")
                return redirect('manager_add_salary')
            
            # Update the salary
            salary.basic_salary = basic_salary
            salary.meal_allowance = meal_allowance
            salary.medical_allowance = medical_allowance
            salary.transportation_allowance = transportation_allowance
            
            # Safely update leave_payment if the field exists
            try:
                if hasattr(salary, 'leave_payment'):
                    salary.leave_payment = leave_payment
            except:
                # If leave_payment field doesn't exist, we can't update it
                pass
                
            salary.save()
            
            messages.success(request, f"Salary for {salary.employee.admin.last_name}, {salary.employee.admin.first_name} ({salary.month_year.strftime('%B %Y')}) updated successfully.")
            return redirect('manager_add_salary')
        else:
            # We're creating a new salary
            employee = get_object_or_404(Employee, id=employee_id)
            month_year_date = f"{month_year}-01"  # Add day to make a valid date
            
            # Check if there's already a salary for this employee and month
            existing_salary = Salary.objects.filter(
                employee=employee,
                month_year=month_year_date
            ).first()
            
            if existing_salary:
                if existing_salary.status == 'paid':
                    messages.error(request, f"A paid salary already exists for {employee.admin.last_name}, {employee.admin.first_name} for {month_year}.")
                else:
                    messages.info(request, f"Updated existing salary record for {employee.admin.last_name}, {employee.admin.first_name} for {month_year}.")
                    existing_salary.basic_salary = basic_salary
                    existing_salary.meal_allowance = meal_allowance
                    existing_salary.medical_allowance = medical_allowance
                    existing_salary.transportation_allowance = transportation_allowance
                    
                    # Safely update leave_payment if the field exists
                    try:
                        if hasattr(existing_salary, 'leave_payment'):
                            existing_salary.leave_payment = leave_payment
                    except:
                        # If leave_payment field doesn't exist, we can't update it
                        pass
                        
                    existing_salary.save()
                
                return redirect('manager_add_salary')
            
            try:
                # Try to create a new salary record with leave_payment
                salary = Salary(
                    employee=employee,
                    month_year=month_year_date,
                    basic_salary=basic_salary,
                    meal_allowance=meal_allowance,
                    medical_allowance=medical_allowance,
                    transportation_allowance=transportation_allowance,
                    leave_payment=leave_payment,
                    tax_percentage=13,  # Default tax percentage
                    insurance_percentage=5,  # Default insurance percentage
                    status='pending'  # Default status
                )
                salary.save()
            except Exception as e:
                # If there's an error with leave_payment, try creating without it
                if "leave_payment" in str(e).lower():
                    salary = Salary(
                        employee=employee,
                        month_year=month_year_date,
                        basic_salary=basic_salary,
                        meal_allowance=meal_allowance,
                        medical_allowance=medical_allowance,
                        transportation_allowance=transportation_allowance,
                        tax_percentage=13,
                        insurance_percentage=5,
                        status='pending'
                    )
                    salary.save()
                else:
                    # If it's a different error, show it to the user
                    messages.error(request, f"Error saving salary: {str(e)}")
                    return redirect('manager_add_salary')
            
            messages.success(request, f"Salary for {employee.admin.last_name}, {employee.admin.first_name} ({month_year}) added successfully.")
            return redirect('manager_add_salary')
