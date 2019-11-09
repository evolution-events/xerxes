"""Artaxerxes URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
"""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path

from apps.people import views as people_views

# Workaround to let the admin site use the regular login form instead of its own, see
# https://django-allauth.readthedocs.io/en/latest/advanced.html#admin
# TODO: This does not work when a user is logged in, but does not have admin site permissions.
admin.site.login = login_required(admin.site.login)


urlpatterns = [
    path('accounts/', include('allauth.urls')),

    # enable the admin interface
    path('admin/', admin.site.urls),

    # url to the welcome page
    path('', people_views.main_index_view, name='main_index_view'),

    # Include urls of the apps
    path('people/', include('apps.people.urls')),
    path('events/', include('apps.events.urls')),
    path('registrations/', include('apps.registrations.urls')),
]
