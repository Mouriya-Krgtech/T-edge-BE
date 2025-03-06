import os
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import pandas as pd
import time
import shutil 
from django.db.models import Count,Prefetch
from rest_framework import generics,permissions,status,viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from api.models import *
from api.serializers import *

# Create your views here.
def device_count(request):
    count = Device.objects.count()
    return JsonResponse({"device_count": count})

def convertor_device_counts(request):
    convertor_counts = []

    convertors = Convertor.objects.all()
    for convertor in convertors:
        device_count = Device.objects.filter(host_configuration__configuration__convertor=convertor).count()
        convertor_counts.append({
            "convertor_name": convertor.name,
            "device_count": device_count
        })

    return JsonResponse({"convertor_device_counts": convertor_counts})


class RecentActivityView(APIView):
    """ API endpoint to get recent activity logs """

    def get(self, request, *args, **kwargs):
        limit = int(request.GET.get("limit", 10))  # Get limit from query params, default is 10
        activities = ActivityLog.objects.order_by("-timestamp")[:limit]
        serializer = ActivityLogSerializer(activities, many=True)
        return Response(serializer.data)


class ActivityByModelView(APIView):
    """ API endpoint to filter activities by model name """

    def get(self, request, model_name, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model=model_name.lower())
            activities = ActivityLog.objects.filter(content_type=content_type).order_by("-timestamp")
            serializer = ActivityLogSerializer(activities, many=True)
            return Response(serializer.data)
        except ContentType.DoesNotExist:
            return Response({"error": "Invalid model name"}, status=400)


            
class ConvertorView(viewsets.ModelViewSet):
    queryset = Convertor.objects.all()
    serializer_class = ConvertorSerializer

class ConfigurationView(viewsets.ModelViewSet):
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer

class HostConfigurationView(viewsets.ModelViewSet):
    queryset=HostConfiguration.objects.all()
    serializer_class = HostConfigurationSerializer

class DeviceView(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

class DeviceListView(generics.ListAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

class DeviceInputPointsView(viewsets.ModelViewSet):
    serializer_class = DeviceInputPointSerializer

    def get_queryset(self):
        queryset = DeviceInputPoint.objects.all()
        device_id = self.request.query_params.get('device_id')
        
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        return queryset

class UploadExcelView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        convertor_id = request.data.get("convertor_id")
        configuration_id = request.data.get("configuration_id")

        if not file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Convertor selection
        try:
            convertor = Convertor.objects.get(id=convertor_id)
        except Convertor.DoesNotExist:
            return Response({"error": "Convertor not found!"}, status=status.HTTP_404_NOT_FOUND)

        # Validate Configuration
        try:
            configuration = Configuration.objects.get(id=configuration_id, convertor=convertor)
        except Configuration.DoesNotExist:
            return Response({"error": "Configuration not found for the provided Convertor."}, status=status.HTTP_404_NOT_FOUND)

        # Save file uniquely per Configuration (use ID to avoid conflicts)
        file_name = f"config_{configuration_id}_{file.name}"
        file_path = default_storage.save(f"temp/{file_name}", file)

        # ✅ Store the file name in the Configuration model
        configuration.excel_file_name = file_name
        configuration.save()

        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)
            df = pd.read_excel(xls, sheet_name="R1")
            host_df = pd.read_excel(xls, sheet_name="HostConfig")

            # ✅ Read Host Configuration dynamically
            host_config_dict = dict(zip(host_df.iloc[:, 0], host_df.iloc[:, 1]))

            baudrate = int(host_config_dict.get("BAUDRATE", 9600))
            parity = host_config_dict.get("PARITY", "EVEN").strip().upper()
            databits = int(host_config_dict.get("DATA BITS", 8))
            stopbits = int(host_config_dict.get("STOP BITS", 1))
            reg_type = host_config_dict.get("REG TYPE", "Holding Register").strip()
            data_type = host_config_dict.get("Data Type", "Integer Type").strip()

            # ✅ Store Host Configuration
            host_config, _ = HostConfiguration.objects.get_or_create(
                configuration=configuration,
                port="502",
                baudrate=baudrate,
                stopbits=stopbits,
                parity=parity,
                databits=databits,
                reg_type=reg_type,
                data_type=data_type
            )

            # ✅ Extract device input points & addresses
            device_names = df.iloc[1, 2:].dropna().values
            device_addresses = df.iloc[2, 2:].dropna().values
            device_input_points = df.iloc[3:, 1].dropna().values
            device_input_addresses = df.iloc[3:, 2:].dropna(how="all").values

            # ✅ Loop through each device and add points
            for i, (name, address) in enumerate(zip(device_names, device_addresses)):
                device, _ = Device.objects.get_or_create(
                    host_configuration=host_config,
                    name=name.strip(),
                    address=int(address)
                )

                for j, (point_name, reg_addresses) in enumerate(zip(device_input_points, device_input_addresses)):
                    actual_name = f"{name.strip()}_{point_name.strip()}"
                    reg_address = reg_addresses[i]

                    DeviceInputPoint.objects.get_or_create(
                        device=device,
                        name=point_name.strip(),
                        actual_name=actual_name,
                        address=int(reg_address),
                        register_type=reg_type,
                        data_type=data_type
                    )

            return Response({
                "message": "Excel file processed successfully!",
                "file_name": file_name
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# class DeleteExcelFileView(APIView):
#     """
#     Delete a specific Excel file and remove related records only.
#     """

#     def post(self, request, *args, **kwargs):
#         file_name = request.data.get("file_name")

#         if not file_name:
#             return Response({"error": "File name is required."}, status=status.HTTP_400_BAD_REQUEST)

#         # Find the Configuration with this file
#         try:
#             configuration = Configuration.objects.get(excel_file_name=file_name)
#         except Configuration.DoesNotExist:
#             return Response({"error": "Configuration with this file name not found."}, status=status.HTTP_404_NOT_FOUND)

#         # Construct file path
#         file_path = os.path.join(settings.MEDIA_ROOT, "uploads", file_name)

#         # Retry deletion to avoid PermissionError
#         def delete_file_with_retry(path, retries=5, delay=2):
#             for attempt in range(retries):
#                 try:
#                     if os.path.exists(path):  # Ensure file exists
#                         os.chmod(path, 0o777)  # Change permissions in case it's locked
#                         default_storage.delete(path)  # Try deleting via Django storage
#                     return True
#                 except PermissionError:
#                     time.sleep(delay)  # Wait before retrying
#                 except Exception as e:
#                     print(f"Attempt {attempt + 1} failed: {e}")
            
#             # Try shutil as an alternative
#             try:
#                 shutil.rmtree(path, ignore_errors=True)  # Attempt full removal
#                 return True
#             except Exception as e:
#                 print(f"shutil delete failed: {e}")
#                 return False

#         if delete_file_with_retry(file_path):
#             message = f"File '{file_name}' deleted successfully."
#         else:
#             return Response({"error": "File could not be deleted (still in use)."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         # Delete only data related to this Configuration
#         related_host_configs = HostConfiguration.objects.filter(configuration=configuration)
#         related_devices = Device.objects.filter(host_configuration__in=related_host_configs)
#         related_device_input_points = DeviceInputPoint.objects.filter(device__in=related_devices)

#         related_device_input_points.delete()
#         related_devices.delete()
#         related_host_configs.delete()
#         configuration.delete()  # Finally, delete the Configuration itself

#         return Response({"message": message + " Related data deleted."}, status=status.HTTP_200_OK)


class DeleteExcelFileView(APIView):
    """
    Delete a specific Excel file and remove related records only.
    """

    def post(self, request, *args, **kwargs):
        file_name = request.data.get("file_name")

        if not file_name:
            return Response({"error": "File name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the Configuration with this file
        try:
            configuration = Configuration.objects.get(excel_file_name=file_name)
        except Configuration.DoesNotExist:
            return Response({"error": "Configuration with this file name not found."}, status=status.HTTP_404_NOT_FOUND)

        # Construct full file path
        file_path = os.path.join(settings.MEDIA_ROOT, "temp", file_name)

        # Force delete function
        def force_delete_file(path, retries=5, delay=2):
            """Attempts to delete the file multiple times to handle file lock issues."""
            for attempt in range(retries):
                try:
                    if os.path.exists(path):
                        os.chmod(path, 0o777)  # Change file permission to ensure delete access
                        os.remove(path)  # Force delete
                        return True
                except PermissionError:
                    print(f"Attempt {attempt + 1}: File locked, retrying in {delay} sec...")
                    time.sleep(delay)  # Wait before retrying
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
            return False

        # Try to delete file
        if force_delete_file(file_path):
            message = f"File '{file_name}' deleted successfully."
        else:
            return Response({"error": "File could not be deleted (still in use)."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Delete only data related to this Configuration
        related_host_configs = HostConfiguration.objects.filter(configuration=configuration)
        related_devices = Device.objects.filter(host_configuration__in=related_host_configs)
        related_device_input_points = DeviceInputPoint.objects.filter(device__in=related_devices)

        related_device_input_points.delete()
        related_devices.delete()
        related_host_configs.delete()
        configuration.delete()  # Finally, delete the Configuration itself

        return Response({"message": message + " Related data deleted."}, status=status.HTTP_200_OK)