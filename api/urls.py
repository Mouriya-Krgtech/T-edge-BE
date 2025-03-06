from django.urls import path,include
from rest_framework import routers
from rest_framework.routers import DefaultRouter
from api.views import *

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r'deviceinputpoints', DeviceInputPointsView, basename='deviceinputpoints')
router.register(r'convertors', ConvertorView, basename='convertors')
router.register(r'hostconfiguration', HostConfigurationView, basename='hostconfiguration')
router.register(r'configuration', ConfigurationView, basename='configuration')
router.register(r'devices', DeviceView, basename='devices')

urlpatterns = [
    path('', include(router.urls)),
    path("device/count/", device_count, name="device_count"),
    path("api/device-counts/", convertor_device_counts, name="device_counts"),

    path("upload-excel/", UploadExcelView.as_view(), name="upload-excel"),
    path('delete-excel/', DeleteExcelFileView.as_view(), name='delete-excel'),


    path("activity/recent/", RecentActivityView.as_view(), name="recent-activity"),
    path("activity/model/<str:model_name>/", ActivityByModelView.as_view(), name="activity-by-model"),

]