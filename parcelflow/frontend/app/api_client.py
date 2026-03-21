"""
API Client Utilities
ParcelFlow - Multi-tenant Logistics Platform
"""
import requests
from flask import session, current_app


def get_api_url():
    """Get the API base URL"""
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    """Get authentication headers if user is logged in"""
    # Token is stored in session['token_data']['access_token']
    token_data = session.get('token_data', {})
    token = token_data.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


def api_get(endpoint, params=None):
    """Make a GET request to the API"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    return requests.get(url, headers=headers, params=params)


def api_post(endpoint, data=None):
    """Make a POST request to the API"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    headers['Content-Type'] = 'application/json'
    return requests.post(url, headers=headers, json=data)


def api_put(endpoint, data=None):
    """Make a PUT request to the API"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    headers['Content-Type'] = 'application/json'
    return requests.put(url, headers=headers, json=data)


def api_patch(endpoint, data=None):
    """Make a PATCH request to the API"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    headers['Content-Type'] = 'application/json'
    return requests.patch(url, headers=headers, json=data)


def api_delete(endpoint):
    """Make a DELETE request to the API"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    return requests.delete(url, headers=headers)


def api_post_raw(endpoint, data=None, files=None):
    """Make a POST request to the API with raw data (for file uploads, etc.)"""
    url = f"{get_api_url()}{endpoint}"
    headers = get_auth_headers()
    # Don't set Content-Type for multipart/form-data, let requests handle it
    return requests.post(url, headers=headers, data=data, files=files)
