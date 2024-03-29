# Generated by Django 4.2 on 2023-08-26 16:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_profile_dob'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='cover_image',
            field=models.ImageField(default='media/cover_pics/cover.jpg', upload_to='media/cover_pics'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='profile_image',
            field=models.ImageField(default='media/profile_pics/default.jpg', upload_to='media/profile_pics'),
        ),
    ]
