# NBA MVP System - Admin Access Restrictions

## Overview
The NBA MVP system now has **strict role-based access control** where admins and regular users have different permissions and access levels.

## Admin Access (Role: 'admin')

### ✅ ALLOWED for Admins:
- **Admin Dashboard** (`/admin/dashboard`)
  - Create new users and admins
  - View user activity and session logs
  - Monitor system statistics
  - Activate/deactivate user accounts

- **Upload Data** (`/upload`)
  - Upload CSV files with NBA player statistics
  - Access file upload functionality

- **Authentication Routes**
  - Login/logout functionality
  - Session management

### ❌ RESTRICTED for Admins:
- **Data Management** (`/data_management`) - Blocked with redirect
- **MVP Rankings** (`/mvp_rankings/<season>`) - Blocked with redirect  
- **Player Comparison** (`/player_comparison`) - Blocked with redirect
- **Calculate MVP** (`/calculate_mvp/<season>`) - Blocked with redirect
- **Compare Players API** (`/api/compare_players`) - Blocked with redirect
- **Delete Season** (`/delete_season/<season>`) - Blocked with redirect
- **Export Rankings** (`/export_rankings/<season>`) - Blocked with redirect

## Regular User Access (Role: 'user')

### ✅ ALLOWED for Regular Users:
- **Dashboard** - Main NBA analysis dashboard
- **Upload Data** - Upload CSV files
- **Data Management** - Manage NBA data by season
- **MVP Rankings** - View calculated MVP rankings
- **Player Comparison** - Compare player statistics
- **Calculate MVP** - Trigger MVP calculations
- **Export/Delete** - Export rankings and delete season data

### ❌ RESTRICTED for Regular Users:
- **Admin Dashboard** - Cannot access admin functions
- **User Management** - Cannot create/manage users

## Implementation Details

### Admin Restriction Mechanism:
1. **@admin_restricted decorator** applied to analysis routes
2. **Session role checking** in route functions
3. **Automatic redirects** with error messages
4. **Sidebar navigation** shows only allowed features

### User Experience:
- **Admins** see simplified sidebar with only Admin Panel and Upload Data
- **Regular Users** see full NBA analysis navigation
- **Automatic redirects** prevent unauthorized access
- **Clear error messages** explain access restrictions

### Security Features:
- **Route-level protection** via decorators
- **Session validation** on every request
- **Role-based UI rendering** in templates
- **Activity logging** for all user actions

## How to Start the Application

```bash
python start_nba_mvp.py
```

### Default Credentials:
- **Admin**: `admin` / `admin123`
- **URL**: http://127.0.0.1:5000

### First Steps:
1. Login as admin
2. Create regular user accounts from Admin Dashboard
3. Regular users can then access full NBA analysis features
4. Admins focus on user management and data uploads

## Benefits of This Design:

1. **Clear Separation**: Admins focus on administration, users on analysis
2. **Security**: Prevents admins from accidentally accessing analysis features
3. **Simplified UX**: Clean interface for each role
4. **Controlled Access**: Only designated users can perform NBA analysis
5. **Audit Trail**: All actions are logged for security monitoring

This design ensures that the system has proper role separation while maintaining security and usability for both administrator and analyst roles.
