from rest_framework import serializers
from api.models import *
from django.contrib.auth.models import User
import os
#-------------------------------------Convertor----------------------------------------------- 
class ActivityLogSerializer(serializers.ModelSerializer): 
    class Meta:
        model = ActivityLog
        fields = "__all__"

class ConvertorSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Convertor
        fields = "__all__"

class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = "__all__"  # Include all model fields + custom field


class HostConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostConfiguration
        fields = ['id','configuration', 'port', 'baudrate', 'stopbits', 'parity', 'databits', 'reg_type', 'data_type']

    def validate_configuration(self, value):
        # Validate if Configuration exists
        try:
            return Configuration.objects.get(name=value)
        except Configuration.DoesNotExist:
            raise serializers.ValidationError("Configuration not found.")

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id','host_configuration', 'name', 'address']

    # def validate_host_configuration(self, value):
    #     # Validate if HostConfiguration exists
    #     try:
    #         return HostConfiguration.objects.get(port=value)
    #     except HostConfiguration.DoesNotExist:
    #         raise serializers.ValidationError("HostConfiguration not found.")

class DeviceInputPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInputPoint
        fields = ['id', 'device', 'name', 'actual_name', 'address', 'register_type', 'data_type']
        read_only_fields = ['actual_name']  # Make it read-only since it's auto-generated

    def validate_device(self, value):
        # Ensure the device instance exists
        if not Device.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Device not found.")
        return value

    def create(self, validated_data):
        # Auto-generate actual_name before saving
        device = validated_data['device']
        validated_data['actual_name'] = f"{device.name}_{validated_data['name']}"
        return super().create(validated_data)