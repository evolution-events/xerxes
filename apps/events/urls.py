from django.conf.urls import url

from . import views

app_name = 'events'
urlpatterns = [
    url(r'^$', views.event_index_view, name='index'),
    url(r'/list/', views.event_list_view, name='eventlist'),
    url(r'r/pd/(?P<eventid>[0-9]+)/', views.registration_step_personal_details, name="personaldetailform"),
    url(r'r/md/(?P<eventid>[0-9]+)/', views.registration_step_medical_details, name="medicaldetailform"),
    url(r'r/op/(?P<eventid>[0-9]+)/', views.registration_step_options, name="optionsform"),
    url(r'r/fc/(?P<eventid>[0-9]+)/', views.registration_step_final_check, name="finalcheckform"),
]
