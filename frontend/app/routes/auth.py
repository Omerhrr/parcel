"""
Authentication Routes Blueprint
"""
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from flask_login import login_user, logout_user, current_user
import requests

auth_bp = Blueprint('auth', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    error = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        response = requests.post(f"{get_api_url()}/auth/login", json={
            'email': email,
            'password': password
        })
        
        if response.status_code == 200:
            data = response.json()
            
            # Store in session
            session['user_data'] = data['user']
            session['token_data'] = data['token']
            
            # Create user object for Flask-Login
            from app.routes.auth import User
            user = User(data['user'], data['token'])
            login_user(user, remember=remember)
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            error = response.json().get('detail', 'Login failed')
    
    return render_template('auth/login.html', error=error)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    error = None
    
    if request.method == 'POST':
        data = {
            'business_name': request.form.get('business_name'),
            'business_email': request.form.get('business_email'),
            'business_phone': request.form.get('business_phone'),
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'password': request.form.get('password'),
            'accept_terms': True
        }
        
        response = requests.post(f"{get_api_url()}/auth/register", json=data)
        
        if response.status_code == 201:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            error = response.json().get('detail', 'Registration failed')
    
    return render_template('auth/register.html', error=error)


@auth_bp.route('/logout')
def logout():
    """Logout"""
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    message = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        response = requests.post(f"{get_api_url()}/auth/forgot-password", json={'email': email})
        
        if response.status_code == 200:
            message = 'If the email exists, a password reset link has been sent.'
    
    return render_template('auth/forgot_password.html', message=message)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password page"""
    error = None
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            error = 'Passwords do not match'
        else:
            response = requests.post(f"{get_api_url()}/auth/reset-password", json={
                'token': token,
                'new_password': new_password,
                'confirm_password': confirm_password
            })
            
            if response.status_code == 200:
                flash('Password reset successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                error = response.json().get('detail', 'Password reset failed')
    
    return render_template('auth/reset_password.html', token=token, error=error)


class User:
    """User class for Flask-Login"""
    def __init__(self, user_data, token_data=None):
        self.id = user_data['id']
        self.name = user_data['name']
        self.email = user_data['email']
        self.phone = user_data.get('phone')
        self.avatar_url = user_data.get('avatar_url')
        self.status = user_data.get('status')
        self.token = token_data.get('access_token') if token_data else None
        self.business_id = token_data.get('business_id') if token_data else None
        self.branch_id = token_data.get('branch_id') if token_data else None
        self.roles = token_data.get('roles', []) if token_data else []
        self.permissions = token_data.get('permissions', []) if token_data else []
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return self.status == 'active'
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def has_role(self, role_name):
        return role_name in self.roles

    def has_permission(self, permission):
        # Super admin and admin have all permissions
        if 'super_admin' in self.roles or 'admin' in self.roles:
            return True
        return permission in self.permissions or '*' in self.permissions
