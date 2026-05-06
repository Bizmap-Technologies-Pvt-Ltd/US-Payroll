app_name = "us_payroll"
app_title = "us_payroll"
app_publisher = "us_payroll"
app_description = "us_payroll"
app_email = "us_payroll@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "us_payroll",
# 		"logo": "/assets/us_payroll/logo.png",
# 		"title": "us_payroll",
# 		"route": "/us_payroll",
# 		"has_permission": "us_payroll.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/us_payroll/css/us_payroll.css"
# app_include_js = "/assets/us_payroll/js/us_payroll.js"

# include js, css files in header of web template
# web_include_css = "/assets/us_payroll/css/us_payroll.css"
# web_include_js = "/assets/us_payroll/js/us_payroll.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "us_payroll/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

doctype_js = {
                "Salary Structure Assignment" : "custom_script/salary_structure_assignment.js",
                "Salary Component" : "custom_script/salary_component.js",
                "Employee" : "custom_script/employee.js", 
                "Journal Entry": "custom_script/journal_entry/journal_entry.js",

            }


doctype_list_js = {
    "W2 Form Details": "us_payroll/doctype/w2_form_details/w2_form_details_list.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "us_payroll/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "us_payroll.utils.jinja_methods",
# 	"filters": "us_payroll.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "us_payroll.install.before_install"
# after_install = "us_payroll.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "us_payroll.uninstall.before_uninstall"
# after_uninstall = "us_payroll.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "us_payroll.utils.before_app_install"
# after_app_install = "us_payroll.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "us_payroll.utils.before_app_uninstall"
# after_app_uninstall = "us_payroll.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "us_payroll.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    # "ToDo": "custom_app.overrides.CustomToDo"
    "Salary Slip":"us_payroll.override.salary_slip.OverrideSalarySlip",
    "Payroll Entry": "us_payroll.override.payroll_entry.OverridePayrollEntry"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    #   "*": {
    #       "on_update": "method",
    #       "on_cancel": "method",
    #       "on_trash": "method"
    #   }

    "Salary Slip":{
                   "after_insert":"us_payroll.custom_script.salary_slip.after_insert",
                   "validate":"us_payroll.custom_script.salary_slip.validate",
                   "on_cancel":"us_payroll.custom_script.salary_slip.on_cancel",
                   "before_save":"us_payroll.custom_script.salary_slip.before_save",
                   "before_submit":"us_payroll.custom_script.salary_slip.before_submit",
                },

    "Employee":{
        "validate":"us_payroll.custom_script.employee.validate"
  },


  # "Payroll Entry":{ 
  #                   "validate":"overtonfa.custom_script.payroll_entry.validate",
  #                   "before_submit": "overtonfa.custom_script.payroll_entry.before_submit"

  #               },

  # "Batch Payment Entry":{"validate":"overtonfa.custom_script.batch_payment_entry.validate"},

  # "Leave Allocation" : {
  #                       "validate":"overtonfa.custom_script.leave_allocation.validate",
  #                       "before_insert":"overtonfa.custom_script.leave_allocation.before_insert",
  #                       "after_insert":"overtonfa.custom_script.leave_allocation.after_insert"
  #                       }
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"us_payroll.tasks.all"
# 	],
# 	"daily": [
# 		"us_payroll.tasks.daily"
# 	],
# 	"hourly": [
# 		"us_payroll.tasks.hourly"
# 	],
# 	"weekly": [
# 		"us_payroll.tasks.weekly"
# 	],
# 	"monthly": [
# 		"us_payroll.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "us_payroll.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "us_payroll.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "us_payroll.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["us_payroll.utils.before_request"]
# after_request = ["us_payroll.utils.after_request"]

# Job Events
# ----------
# before_job = ["us_payroll.utils.before_job"]
# after_job = ["us_payroll.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"us_payroll.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

