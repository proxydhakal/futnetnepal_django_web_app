# Generated by Django 3.0.6 on 2020-05-31 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20200514_0610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='cover_image',
            field=models.ImageField(default='cover.jpg', upload_to='media/cover_pics'),
        ),
    ]
