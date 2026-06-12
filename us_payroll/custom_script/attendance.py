import json
from datetime import datetime

import frappe
from frappe.utils import flt, get_time
from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details


def validate(self, method):
	if self.custom_overtime_hours:
		self.custom_overtime_amount = self.custom_overtime_hours * self.custom_overtime_rate

	if self.working_hours:
		self.custom_total_amount = self.working_hours * self.custom_hourly_rate


def on_submit(self, method):
	pass


def additional_salary(self, amount, component):
	additional = frappe.new_doc("Additional Salary")
	additional.employee = self.employee
	additional.company = self.company
	additional.salary_component = component
	additional.amount = amount
	additional.payroll_date = self.attendance_date
	additional.insert()
	additional.submit()


def set_total_and_overtime_hours(doc, method=None):
	if not doc.shift or not doc.attendance_date:
		return

	timestamp = doc.in_time

	if not timestamp:
		shift_start_time = frappe.db.get_value("Shift Type", doc.shift, "start_time")
		timestamp = datetime.combine(doc.attendance_date, get_time(shift_start_time))

	shift_details = get_shift_details(doc.shift, timestamp)

	if not shift_details:
		return

	duration_hours = flt(
		(shift_details.end_datetime - shift_details.start_datetime).total_seconds() / 3600,
		2,
	)
	working_hours = flt(doc.working_hours, 2)

	overtime_hours = 0
	if working_hours > duration_hours:
		overtime_hours = working_hours - duration_hours

	else:
		overtime_hours = 0
		duration_hours = working_hours

	doc.custom_total_working_hours = duration_hours
	doc.custom_overtime_hours = flt(overtime_hours, 2)


@frappe.whitelist()
def get_global_defaults_values(doctype: str):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company": company}


@frappe.whitelist()
def get_department_working_hours(employee: str):
	"""
	Fetch the custom working hours for the employee's department.
	Returns 0 if the department name is not set for the employee
	or if the working hours are 0.
	"""
	if not employee:
		return {"error": "Employee is required"}

	employee_doc = frappe.get_doc("Employee", employee)
	department_name = getattr(employee_doc, "department", None)
	if not department_name:
		return {"working_hours": 0}

	try:
		# Fetch the department document from the department doctype
		department_doc = frappe.get_doc("Department", department_name)
		working_hours = getattr(department_doc, "custom_working_hours", None)
		if not working_hours or working_hours == 0:
			return {"working_hours": 0}

		return {"working_hours": working_hours}

	except frappe.DoesNotExistError:
		return 0

	except Exception as e:
		return {"error": f"Unexpected error: {e!s}"}
