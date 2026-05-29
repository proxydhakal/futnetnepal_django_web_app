# Custom user + profile (squashed for AUTH_USER_MODEL = accounts.User)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(
                    default=False,
                    help_text='Designates that this user has all permissions without explicitly assigning them.',
                    verbose_name='superuser status',
                )),
                ('role', models.IntegerField(
                    choices=[(0, 'Super Admin'), (1, 'User'), (2, 'Vendor')],
                    default=1,
                )),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('username', models.CharField(max_length=255, unique=True)),
                ('full_name', models.CharField(blank=True, default='', max_length=255)),
                ('profile_image', models.ImageField(
                    default='media/profile_pics/default.jpg',
                    upload_to='media/profile_pics',
                )),
                ('is_staff', models.BooleanField(default=False)),
                ('is_email_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('status', models.CharField(
                    choices=[
                        ('INACTIVE', 'Inactive'),
                        ('ACTIVE', 'Active'),
                        ('DELETED', 'Deleted'),
                    ],
                    default='ACTIVE',
                    max_length=50,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('groups', models.ManyToManyField(
                    blank=True,
                    related_name='useraccount_set',
                    to='auth.group',
                )),
                ('user_permissions', models.ManyToManyField(
                    blank=True,
                    related_name='useraccount_set',
                    to='auth.permission',
                )),
            ],
            options={
                'db_table': 'accounts_useraccount',
                'verbose_name': 'user account',
                'verbose_name_plural': 'user accounts',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cover_image', models.ImageField(
                    default='media/cover_pics/cover.jpg',
                    upload_to='media/cover_pics',
                )),
                ('phone', models.CharField(
                    blank=True,
                    default='',
                    help_text='10-digit contact number',
                    max_length=10,
                )),
                ('address', models.CharField(blank=True, max_length=50, null=True)),
                ('dob', models.DateField(blank=True, null=True)),
                ('email_verification_token', models.CharField(blank=True, db_index=True, max_length=64)),
                ('email_verification_sent_at', models.DateTimeField(blank=True, null=True)),
                ('email_otp_hash', models.CharField(blank=True, max_length=128)),
                ('email_otp_attempts', models.PositiveSmallIntegerField(default=0)),
                ('phone_verified', models.BooleanField(default=False)),
                ('phone_otp_hash', models.CharField(blank=True, max_length=128)),
                ('phone_otp_sent_at', models.DateTimeField(blank=True, null=True)),
                ('phone_otp_attempts', models.PositiveSmallIntegerField(default=0)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
