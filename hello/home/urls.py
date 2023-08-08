from django.contrib import admin
from django.urls import path,include
from home import views


urlpatterns = [
    path('', views.home, name='home'),
    path('aws/', views.aws_button, name='aws_button'),
    path('gcp/', views.gcp_button, name='gcp_button'),
    path('aws/create_vm/', views.create_vm, name='create_vm'),
    path('aws/list_vms/', views.list_vms, name='list_vms'),
    path('aws/stop_vm/', views.stop_vm, name='stop_vm'),
    path('aws/delete_vm/', views.delete_vm, name='delete_vm'),
    path('aws/create_ami/', views.create_ami, name='create_ami'),
    path('aws/list_amis/', views.list_amis, name='list_amis'),
    path('aws/delete_ami/', views.delete_ami, name='delete_ami'),
    path('gcp/create_vm_gcp/', views.create_vm_gcp, name='create_vm_gcp'),
    path('gcp/list_vm_gcp/', views.list_vm_gcp, name='list_vm_gcp'),
    path('gcp/create_machine_gcp/', views.create_machine_gcp, name='create_machine_gcp'),
    path('gcp/list_machines_gcp/', views.list_machines_gcp, name='list_machines_gcp'),
    path('gcp/stop_vm_gcp/',views.stop_vm_gcp,name='stop_vm_gcp'),
    path('gcp/vm_stopped/<str:vm_name>/', views.vm_stopped, name='vm_stopped'),
    path('gcp/delete_vm_gcp/<str:vm_name>/', views.delete_vm_gcp, name='delete_vm_gcp'),
    path('gcp/delete_machine_image_gcp/', views.delete_machine_image_gcp, name='delete_machine_image_gcp'),
]