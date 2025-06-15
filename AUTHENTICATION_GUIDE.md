# NBA MVP Decision Support System - Authentication Guide

## Overview

This application now includes a comprehensive user authentication system with role-based access control. The system supports two user roles: **Admin** and **Regular User**.

## Authentication Features

### Login System
- **Database-backed authentication** using SQLite
- **Password hashing** with Werkzeug security
- **Session management** with activity tracking
- **Role-based redirection** after login

### User Roles

#### Regular User
- Access to NBA data analysis features
- Can upload CSV files
- Can view MVP rankings and player comparisons
- Can manage NBA data by season

#### Administrator
- All regular user permissions
- **User Management**: Create new users and admins
- **User Activity Monitoring**: View login/logout times and activity
- **User Status Control**: Activate/deactivate user accounts
- **System Analytics**: View system usage statistics

### Security Features
- **Password requirements**: Minimum 6 characters
- **Session timeout**: 24 hours
- **Activity logging**: All user actions are tracked
- **IP address tracking**: Login attempts and sessions are monitored
- **Self-protection**: Admins cannot deactivate their own accounts

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Application
```bash
python start_server.py
```

### 3. Access the System
- **URL**: http://localhost:5000
- **Default Admin**: 
  - Username: `admin`
  - Password: `admin123`

### 4. First Login
1. Navigate to http://localhost:5000
2. You'll be redirected to the login page
3. Use the default admin credentials
4. You'll be redirected to the Admin Dashboard

## User Management

### Creating New Users
1. Login as an admin
2. Go to the Admin Dashboard
3. Click "Create New User"
4. Fill in the required information:
   - Username (minimum 3 characters)
   - Email address
   - Password (minimum 6 characters)
   - Role (User or Admin)
5. Click "Create User"

### Managing Users
- **View User Activity**: See login/logout times and recent actions
- **Activate/Deactivate**: Toggle user account status
- **Monitor Sessions**: View active user sessions

## Directory Structure
```
MVPNBA/
├── app.py                 # Main application with authentication
├── start_server.py        # Application startup script
├── requirements.txt       # Python dependencies
├── nba_mvp.db            # SQLite database (created on first run)
├── templates/
│   ├── auth/
│   │   └── login.html    # Login page
│   ├── admin/
│   │   └── dashboard.html # Admin dashboard
│   ├── base.html         # Updated with auth navigation
│   └── ...               # Other NBA analysis templates
└── static/               # CSS, JS, and asset files
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Hashed password
- `role`: 'admin' or 'user'
- `is_active`: Account status
- `created_at`: Account creation timestamp
- `created_by`: ID of admin who created the account

### User Activity Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `action_type`: Type of action (login, logout, etc.)
- `action_details`: Additional details about the action
- `ip_address`: User's IP address
- `user_agent`: Browser/client information
- `timestamp`: When the action occurred

### User Sessions Table
- `id`: Session ID
- `user_id`: Foreign key to users table
- `login_time`: When the session started
- `logout_time`: When the session ended
- `last_activity`: Last activity timestamp
- `ip_address`: Session IP address
- `user_agent`: Browser/client information
- `is_active`: Session status

## API Endpoints

### Authentication
- `GET/POST /login` - Login page and authentication
- `GET /logout` - Logout and session cleanup
- `GET /dashboard` - User dashboard (requires login)

### Admin Functions
- `GET /admin/dashboard` - Admin dashboard (requires admin role)
- `POST /admin/create_user` - Create new user (requires admin role)
- `POST /admin/toggle_user/<user_id>` - Activate/deactivate user (requires admin role)

### NBA Data Features
- All existing NBA analysis features require authentication
- Data upload and management require login
- MVP calculations and comparisons require login

## Security Considerations

1. **Change Default Password**: Immediately change the default admin password
2. **Use Strong Passwords**: Enforce strong password policies for all users
3. **Monitor Activity**: Regularly check user activity logs
4. **Regular Backups**: Backup the SQLite database regularly
5. **HTTPS**: Use HTTPS in production environments

## Troubleshooting

### Common Issues

1. **Database Not Found**
   - Solution: Run `python start_server.py` to initialize the database

2. **Can't Login with Default Credentials**
   - Check if database was properly initialized
   - Verify the admin user was created (check console output)

3. **Permission Errors**
   - Ensure proper file permissions for the database
   - Check that the uploads directory is writable

4. **Session Issues**
   - Clear browser cookies/session data
   - Restart the application

### Support
For issues or questions about the authentication system, check the application logs and database activity table for debugging information.
