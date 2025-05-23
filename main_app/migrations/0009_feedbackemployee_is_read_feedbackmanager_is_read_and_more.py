# Generated by Django 5.2 on 2025-04-19 11:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0008_remove_rankreport_employee_attendancereport_manager_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedbackemployee',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='feedbackmanager',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='leavereportemployee',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='leavereportmanager',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationemployee',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationmanager',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='task',
            name='is_viewed',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='NotificationCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pending_tasks', models.IntegerField(default=0)),
                ('unread_notifications', models.IntegerField(default=0)),
                ('pending_leave_requests', models.IntegerField(default=0)),
                ('unread_feedback', models.IntegerField(default=0)),
                ('pending_salary', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user',)},
            },
        ),
    ]
