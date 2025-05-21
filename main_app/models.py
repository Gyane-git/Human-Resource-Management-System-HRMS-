from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from datetime import datetime




class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE = ((1, "CEO"), (2, "Manager"), (3, "Employee"))
    GENDER = [("M", "Male"), ("F", "Female")]
    
    
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField()
    fcm_token = models.TextField(default="")  # For firebase notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.last_name + ", " + self.first_name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



class Division(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Manager(models.Model):
    division = models.ForeignKey(Division, on_delete=models.DO_NOTHING, null=True, blank=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.last_name + " " + self.admin.first_name


class Department(models.Model):
    name = models.CharField(max_length=120)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.DO_NOTHING, null=True, blank=False)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True, blank=False)

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name


class Attendance(models.Model):
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AttendanceReport(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.DO_NOTHING, null=True, blank=True)
    manager = models.ForeignKey(Manager, on_delete=models.DO_NOTHING, null=True, blank=True)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(employee__isnull=False, manager__isnull=True) | 
                    models.Q(employee__isnull=True, manager__isnull=False)
                ),
                name='attendance_either_employee_or_manager'
            )
        ]


class LeaveReportEmployee(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES, default='annual')
    date_from = models.DateField(default=datetime.now)
    date_to = models.DateField(default=datetime.now)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportManager(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
    ]
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES, default='annual')
    date_from = models.DateField(default=datetime.now)
    date_to = models.DateField(default=datetime.now)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackEmployee(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackManager(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationManager(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationEmployee(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    base = models.FloatField(default=0)
    ctc = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        if instance.user_type == 2:
            Manager.objects.create(admin=instance)
        if instance.user_type == 3:
            Employee.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    if instance.user_type == 2:
        instance.manager.save()
    if instance.user_type == 3:
        instance.employee.save()


class Task(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]

    manager = models.ForeignKey("Manager", on_delete=models.CASCADE)
    employee = models.ForeignKey("Employee", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    file = models.FileField(upload_to="task_files/", null=True, blank=True)  # Task file
    rating = models.IntegerField(null=True, blank=True)  # Task rating (1-5)

    def __str__(self):
        return self.title


class Salary(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month_year = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    meal_allowance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transportation_allowance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    leave_payment = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=13)
    insurance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super(Salary, self).__init__(*args, **kwargs)
        # This is a workaround for the missing column in the database
        # It will be used until the migration can be properly applied
        if not hasattr(self, 'leave_payment'):
            self.leave_payment = None
    
    @property
    def tax_amount(self):
        return (self.basic_salary * self.tax_percentage) / 100
    
    @property
    def insurance_amount(self):
        return (self.basic_salary * self.insurance_percentage) / 100
    
    @property
    def total_earnings(self):
        return (
            self.basic_salary + 
            self.meal_allowance + 
            self.medical_allowance + 
            self.transportation_allowance -
            (self.leave_payment or 0)
        )
    
    @property
    def total_deductions(self):
        return self.tax_amount + self.insurance_amount
    
    @property
    def net_salary(self):
        return self.total_earnings - self.total_deductions
    
    def __str__(self):
        return f"{self.employee.admin.last_name}, {self.employee.admin.first_name} - {self.month_year.strftime('%B %Y')}"
    
    class Meta:
        unique_together = ('employee', 'month_year')
        ordering = ['-month_year']