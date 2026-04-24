# HR Employee Secondment Module

## Overview
This module provides comprehensive employee secondment management for Odoo 18 EE, allowing organizations to manage temporary assignments of employees to higher-grade or vacant positions with complete flexibility and automation.

## Key Features

### 🎯 Dynamic Configuration
All business rules are configurable through **HR Settings** without requiring code changes:

- **Duration Settings**
  - Maximum secondment duration (default: 6 months)
  - Maximum extension duration (default: 6 months)
  - Enable/disable extensions

- **Allowance Settings**
  - Eligibility threshold in months (default: 2 months)
  - Allowance percentage of base salary (default: 25%)
  - Option to require maintenance of original duties

- **Grade Eligibility**
  - Maximum grade difference allowed (default: 2 levels)

- **Notifications**
  - Days before end date to notify HR (default: 30 days)
  - Auto-complete on end date option

### 📋 Secondment Management

#### Employee Information Section
- Employee selection with auto-populated fields:
  - Current department (readonly)
  - Current position (readonly)
  - Current grade (readonly)
  - Current basic salary (readonly)

#### Secondment Details
- Target position selection
- Auto-populated secondment department
- Secondment position base salary (for allowance calculation)
- Start and end dates with duration calculation
- HTML editor for duties and responsibilities

#### State Workflow
- **Draft** → **Submitted** → **Approved** → **Active** → **Completed**
- Alternative states: **Rejected**, **Cancelled**
- State-specific field readonly controls

### 💰 Automatic Allowance Calculation

The system automatically calculates allowances based on configured rules:

1. **Eligibility Check**
   - Duration must exceed configured threshold (default: 2 months)
   - Optional: Employee must maintain original duties

2. **Calculation**
   - Monthly allowance = Secondment position salary × Configured percentage
   - Total allowance = Monthly allowance × Eligible months (duration - threshold)

3. **Configuration Snapshot**
   - Settings at time of creation are stored on the record
   - Ensures consistency even if settings change later

### 🔄 Extension Management

- One-time extension allowed per secondment
- Maximum extension duration configurable
- Extension tracking with separate duration calculation
- Total duration = Original duration + Extension duration
- Effective end date shows actual end including extension

### ✅ Validations & Constraints

#### Date Validations
- End date must be after start date
- Duration cannot exceed configured maximum
- No overlapping active secondments per employee

#### Extension Validations
- Only one extension allowed
- Extension duration cannot exceed configured maximum
- Only active secondments can be extended

#### Business Rules
- One active secondment per employee at any time
- Grade difference restrictions (configurable)
- Proper state transitions enforced

### 📊 Smart Features

#### Smart Buttons
- **History Count**: View all previous secondments for the employee
- **View Employee**: Quick access to employee record

#### Employee Form Integration
- Smart button showing secondment count
- Display active secondment on employee form
- Quick access to view all secondments

### 🔔 Automated Notifications

#### Daily Scheduled Actions

1. **Ending Secondments Checker**
   - Runs daily
   - Creates activities for HR Manager X days before end date
   - Configurable notification window
   - Prevents duplicate notifications

2. **Auto-Complete Secondments** (Optional)
   - Automatically marks secondments as completed on end date
   - Only runs if enabled in settings

### 📈 Reporting & Views

#### Multiple View Types
- **Tree View**: List with color-coded states and monetary summaries
- **Kanban View**: Visual board grouped by state
- **Form View**: Comprehensive detail view with all information
- **Calendar View**: (Can be added) Timeline of secondments

#### Smart Filters
- My Secondments
- Draft / Submitted / Approved / Active / Completed
- To Approve (HR Managers)
- Allowance Eligible
- Extended secondments
- Ending This Month
- Ending Next Month

#### Group By Options
- Employee
- Current Department
- Secondment Department
- Secondment Position
- Status
- Start Date

### 🔐 Security & Access Rights

#### Access Levels
- **HR User** (hr.group_hr_user): Read, Write, Create
- **HR Manager** (hr.group_hr_manager): Full access including Delete
- **Employee** (base.group_user): Read only

#### State-Based Security
- Draft: Editable by creator
- Submitted: Only HR Manager can approve/reject
- Approved/Active: Only HR Manager can modify
- Completed: Readonly for all

## Installation

1. Copy the `hr_employee_secondment` folder to your Odoo addons directory
2. Update the apps list: Settings → Apps → Update Apps List
3. Search for "HR Employee Secondment"
4. Click Install

## Configuration

1. Navigate to: **HR → Configuration → Settings**
2. Scroll to **Secondment Management** section
3. Configure all parameters according to your organization's policies:
   - Duration limits
   - Allowance rules
   - Grade restrictions
   - Notification timing

## Usage

### Creating a Secondment Request

1. Go to: **HR → Secondments → My Secondments**
2. Click **Create**
3. Fill in the form:
   - Select employee
   - Choose secondment position
   - Set start and end dates
   - Define duties and responsibilities
   - Check "Maintains Original Duties" if applicable
   - Enter secondment position base salary
4. Click **Submit**

### Approval Process (HR Manager)

1. Go to: **HR → Secondments → To Approve**
2. Review the request
3. Click **Approve** or **Reject**
4. If rejecting, provide a reason
5. Once approved, click **Activate** when the secondment starts

### Extending a Secondment

1. Open an active secondment
2. Click **Extend** button
3. Enter extension end date
4. System validates against maximum extension duration
5. Allowance recalculates automatically

### Completing a Secondment

1. Open an active secondment
2. Click **Complete** button
3. Or enable auto-completion in settings

## Technical Details

### Models

#### hr.employee.secondment
- Main model for secondment records
- Inherits: mail.thread, mail.activity.mixin
- Computed fields for durations and allowances
- Dynamic validation based on configuration

#### res.config.settings (inherited)
- All configuration parameters
- Stored in ir.config_parameter

#### hr.employee (inherited)
- Smart button for secondments
- Active secondment display

### Dependencies
- hr
- hr_contract
- mail

### Database Tables
- hr_employee_secondment

### Scheduled Actions
- Check Ending Secondments (Daily)
- Auto-Complete Secondments (Daily, if enabled)

## Customization

### Adding Custom Fields

Edit `models/hr_employee_secondment.py`:
```python
custom_field = fields.Char(string='Custom Field')
```

Update views in `views/hr_employee_secondment_views.xml`:
```xml
<field name="custom_field"/>
```

### Modifying Allowance Logic

Override the compute method:
```python
@api.depends('your_fields')
def _compute_allowance_amount(self):
    # Your custom logic
    pass
```

### Adding Grade Validation

Implement grade comparison in constraints:
```python
@api.constrains('employee_id', 'secondment_job_id')
def _check_grade_eligibility(self):
    # Your validation logic
    pass
```

## Support

For issues, questions, or feature requests, please contact the HR department or system administrator.

## License

LGPL-3

## Credits

- **Author**: KUEC
- **Version**: 18.0.1.0.0
- **Category**: Human Resources
