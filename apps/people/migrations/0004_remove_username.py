# Generated by Django 2.0.5 on 2018-07-01 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0003_emergencycontact'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='artauser',
            options={},
        ),
        migrations.AlterModelManagers(
            name='artauser',
            managers=[
            ],
        ),
        migrations.RemoveField(
            model_name='artauser',
            name='username',
        ),
        migrations.AlterField(
            model_name='artauser',
            name='email',
            field=models.EmailField(max_length=64, unique=True, verbose_name='email address'),
        ),
    ]
