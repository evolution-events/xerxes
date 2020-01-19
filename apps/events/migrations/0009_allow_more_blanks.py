# Generated by Django 2.2.7 on 2019-11-19 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_auto_20191109_2031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='description',
            field=models.TextField(blank=True, help_text='Event details like what is included or not', verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='event',
            name='location_info',
            field=models.TextField(blank=True, help_text='Address and additional information about the location', verbose_name='Location information'),
        ),
        migrations.AlterField(
            model_name='event',
            name='location_name',
            field=models.CharField(blank=True, help_text='Name of the location, will be used as link text if url is also available', max_length=100, verbose_name='Location name'),
        ),
    ]