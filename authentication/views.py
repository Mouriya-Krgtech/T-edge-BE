from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
# Create your views here.
from authentication.models import *

import json
import os
import pyzipper
from django.db import connections
import uuid

class ActivateAccountView(APIView):
    def get(self, request):
        """Check activation status by MAC address."""
        mac_address = self.get_mac_address()
        if not mac_address:
            return Response({'message': 'Unable to fetch MAC address.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        zip_path = "D:/Zip-Key/Key"
        if not os.path.exists(zip_path):
            return Response({'message': 'Activation record not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with pyzipper.AESZipFile(zip_path, 'r', encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(b"1234")
                with zf.open("new_license_output.json") as file:
                    activation_data = json.load(file)

            if activation_data.get("mac_address") == mac_address:
                return Response({'is_active': True, 'mac_address': mac_address}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error reading zip file: {e}")
            return Response({'message': 'Error accessing activation data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'Activation record not found.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """Activate or update an account based on the provided license key."""
        raw_license_key = request.data.get('license_key')
        if not raw_license_key:
            return Response({'message': 'Please provide a license key.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mac_address = self.get_mac_address()
        if not mac_address:
            return Response({'message': 'Unable to fetch MAC address.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check license key in the secondary database
        try:
            with connections['licence_keys'].cursor() as cursor:
                cursor.execute("SELECT id, is_used FROM licencekeys_license WHERE raw_license_key = %s", [raw_license_key])
                license_data = cursor.fetchone()
                if not license_data:
                    return Response({'message': 'Invalid license key.'}, status=status.HTTP_400_BAD_REQUEST)
                
                license_id, is_used = license_data
                if is_used:
                    return Response({'message': 'License key has already been used.'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark the license key as used
                cursor.execute("UPDATE licencekeys_license SET is_used = 1 WHERE id = %s", [license_id])
        except Exception as e:
            print(f"Database error: {e}")
            return Response({'message': 'An error occurred while accessing the license database.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save activation record to zip
        activation_data = {
            'mac_address': mac_address,
            'license_key': raw_license_key,
        }
        self.save_to_zip(activation_data)

        return Response({'message': 'Account activated successfully!'}, status=status.HTTP_200_OK)

    @staticmethod
    def get_mac_address():
        """Fetch the MAC address of the backend system."""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xFF) 
                            for ele in range(0, 8 * 6, 8)][::-1])
            if mac == "00:00:00:00:00:00":
                raise ValueError("Invalid MAC address detected.")
            return mac
        except Exception as e:
            print(f"Error fetching MAC address: {e}")
            return None

    def save_to_zip(self, activation_data):
        """Save activation data to a password-protected ZIP file."""
        output_content = json.dumps(activation_data, indent=4)
        password = "1234"
        output_zip_path = "D:/Zip-Key/Key"
        inner_file_name = "new_license_output.json"

        os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)

        with pyzipper.AESZipFile(output_zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            zf.writestr(inner_file_name, output_content)

        print(f"Password-protected zip file created at {output_zip_path}")


# from django.contrib.auth.hashers import check_password

# class LoginView(APIView):
#     def post(self, request):
#         data = request.data
#         identifier = data.get('identifier')  # Can be email or username
#         password = data.get('password')

#         # Print the input data for debugging
#         print("Received data:", data)

#         if not identifier or not password:
#             print("Missing identifier or password")
#             return Response({'message': 'Please provide both identifier (email or username) and password.'}, status=status.HTTP_400_BAD_REQUEST)

#         # Try to fetch user by email or username
#         try:
#             if '@' in identifier:
#                 user = User.objects.get(email__iexact=identifier)  # Fetch user by email
#                 print("User fetched by email:", user.email)
#             else:
#                 user = User.objects.get(username__iexact=identifier)  # Fetch user by username
#                 print("User fetched by username:", user.username)
#         except User.DoesNotExist:
#             print("User not found for identifier:", identifier)
#             return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

#         # Check if user is active
#         if not user.is_active:
#             print("User account is inactive:", user.username)
#             return Response({'error': 'User account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

#         # Print details about the user before checking password
#         print(f"Checking password for user: {user.username}")

#         # Manually check password hash
#         if not check_password(password, user.password):
#             print(f"Password for user {user.username} is incorrect")
#             return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

#         # If password is correct, proceed with authentication
#         user_type = 'admin' if user.is_admin else None
#         print(f"User authenticated successfully. User Type: {user_type}")

#         # Generate JWT tokens
#         refresh = RefreshToken.for_user(user)
#         refresh['user_id'] = user.id
#         refresh['username'] = user.username
#         refresh['user_type'] = user_type

#         response_data = {
#             'Status': status.HTTP_200_OK,
#             'message': f'{user_type.capitalize()} logged in successfully' if user_type else 'User logged in successfully',
#             'refreshToken': str(refresh),
#             'accessToken': str(refresh.access_token),
#             'user_id': user.id,
#             'username': user.username,
#             'user_type': user_type,
#         }
#         print("Response data:", response_data)
#         return Response(response_data, status=status.HTTP_200_OK)


# class LoginView(APIView):
#     def post(self, request):
#         data = request.data
#         identifier = data.get('identifier')  # Can be email or username
#         password = data.get('password')

#         # Check if identifier and password are provided
#         if not identifier or not password:
#             return Response({'message': 'Please provide both identifier (email or username) and password.'}, 
#                              status=status.HTTP_400_BAD_REQUEST)

#         # Try to fetch user by email or username
#         try:
#             if '@' in identifier:
#                 user = User.objects.get(email__iexact=identifier)  # Fetch user by email
#             else:
#                 user = User.objects.get(username__iexact=identifier)  # Fetch user by username
#         except User.DoesNotExist:
#             return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

#         # Check if user is active
#         if not user.is_active:
#             return Response({'error': 'User account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

#         # Authenticate user (using email or username)
#         authenticated_user = authenticate(request, username=user.username, password=password)
        
#         # If authentication fails, return an error
#         if not authenticated_user:
#             return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

#         # Authentication success
#         user_type = 'admin' if user.is_admin else None

#         # Generate JWT tokens
#         refresh = RefreshToken.for_user(authenticated_user)
#         refresh['user_id'] = authenticated_user.id
#         refresh['username'] = authenticated_user.username
#         refresh['user_type'] = user_type

#         response_data = {
#             'Status': status.HTTP_200_OK,
#             'message': f'{user_type.capitalize()} logged in successfully' if user_type else 'User logged in successfully',
#             'refreshToken': str(refresh),
#             'accessToken': str(refresh.access_token),
#             'user_id': authenticated_user.id,
#             'username': authenticated_user.username,
#             'user_type': user_type,
#         }
#         return Response(response_data, status=status.HTTP_200_OK)


class LoginView(APIView):
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response({'message': 'Please provide both email and password.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        authenticated_user = authenticate(request, email=email, password=password)
        
        if authenticated_user:
            user_type = None
            if user.is_admin:
                user_type = 'admin'

            payload = {
                'user_id': authenticated_user.id,
                'username': authenticated_user.username,
                'user_type': user_type,
            }
            refresh = RefreshToken.for_user(authenticated_user)
            refresh['user_id'] = payload['user_id']
            refresh['username'] = payload['username']
            refresh['user_type'] = payload['user_type']
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            response_data = {
                'Status': status.HTTP_200_OK,
                'message': f'{user_type.capitalize()} logged in successfully' if user_type else 'User logged in successfully',
                'refreshToken': refresh_token,
                'accessToken': access_token,
                'user_id': payload['user_id'],
                'username': payload['username'],
                'user_type': payload['user_type'],
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return Response({'error': 'Invalid refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'User logged out successfully.'}, status=status.HTTP_200_OK)