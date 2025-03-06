# from django.db import models
# from django.http import JsonResponse

# # Create your models here.


# class Convertor(models.Model):
#     name = models.CharField(max_length=250)
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)

#     def __str__(self):
#         return self.name

# class Configuration(models.Model):
#     convertor = models.ForeignKey(Convertor, on_delete=models.CASCADE, related_name="configurations")
#     name = models.CharField(max_length=250)
#     channel = models.CharField(max_length=250)
#     excel_file_name = models.CharField(max_length=250, blank=True, null=True)  # Store file name
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)

#     def __str__(self):
#         return self.name

# class HostConfiguration(models.Model):
#     configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE, related_name="host_configurations")
#     port = models.CharField(max_length=250)
#     baudrate = models.CharField(max_length=250)
#     stopbits = models.CharField(max_length=250)
#     parity = models.CharField(max_length=250)
#     databits = models.CharField(max_length=250)
#     reg_type = models.CharField(max_length=250)
#     data_type = models.CharField(max_length=250)
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)

#     def __str__(self):
#         return f"HostConfig {self.id} - {self.port}"

# class Device(models.Model):
#     host_configuration = models.ForeignKey(HostConfiguration, on_delete=models.CASCADE, related_name="devices")
#     name = models.CharField(max_length=250)
#     address = models.CharField(max_length=250)
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)

#     def __str__(self):
#         return self.name

# class DeviceInputPoint(models.Model):
#     device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="input_points")
#     name = models.CharField(max_length=250)
#     actual_name = models.CharField(max_length=250,null=True,blank=True)
#     address = models.CharField(max_length=250)  # Removed duplicate fields
#     register_type = models.CharField(max_length=250)
#     data_type = models.CharField(max_length=250)
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} ({self.address})"

# class DeviceOutputPoints(models.Model):
#     name = models.CharField(max_length=250)
#     actual_name = models.CharField(max_length=250)
#     address = models.CharField(max_length=250)
#     address = models.CharField(max_length=250)
#     address = models.CharField(max_length=250)



from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Convertor(models.Model):
    name = models.CharField(max_length=250)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class Configuration(models.Model):
    convertor = models.ForeignKey(Convertor, on_delete=models.CASCADE, related_name="configurations")
    name = models.CharField(max_length=250)
    channel = models.CharField(max_length=250)
    excel_file_name = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class HostConfiguration(models.Model):
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE, related_name="host_configurations")
    port = models.CharField(max_length=250)
    baudrate = models.CharField(max_length=250)
    stopbits = models.CharField(max_length=250)
    parity = models.CharField(max_length=250)
    databits = models.CharField(max_length=250)
    reg_type = models.CharField(max_length=250)
    data_type = models.CharField(max_length=250)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return f"HostConfig {self.id} - {self.port}"


class Device(models.Model):
    host_configuration = models.ForeignKey(HostConfiguration, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=250)
    address = models.CharField(max_length=250)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class DeviceInputPoint(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="input_points")
    name = models.CharField(max_length=250)
    actual_name = models.CharField(max_length=250, null=True, blank=True)
    address = models.CharField(max_length=250)
    register_type = models.CharField(max_length=250)
    data_type = models.CharField(max_length=250)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.address})"


# Activity Log Model
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("deleted", "Deleted"),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Generic model type
    object_id = models.PositiveIntegerField()  # ID of affected object
    content_object = GenericForeignKey("content_type", "object_id")  # Link to affected object
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.content_type} {self.object_id} {self.action} at {self.timestamp}"


# Django Signals to Log Activity
@receiver(post_save, sender=Convertor)
@receiver(post_save, sender=Configuration)
@receiver(post_save, sender=HostConfiguration)
@receiver(post_save, sender=Device)
@receiver(post_save, sender=DeviceInputPoint)
def log_create_update(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    ActivityLog.objects.create(
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.id,
        action=action
    )


@receiver(post_delete, sender=Convertor)
@receiver(post_delete, sender=Configuration)
@receiver(post_delete, sender=HostConfiguration)
@receiver(post_delete, sender=Device)
@receiver(post_delete, sender=DeviceInputPoint)
def log_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.id,
        action="deleted"
    )
