import frappe
import json

def validate(self,method):
	pass

def on_submit(self,method):
	pass

def additional_salary(self,amount,component):
	additional = frappe.new_doc("Additional Salary")
	additional.employee=self.employee
	additional.company=self.company
	additional.salary_component=component
	additional.amount=amount
	additional.payroll_date=self.attendance_date
	additional.insert()
	additional.submit()

@frappe.whitelist()
def get_global_defaults_values(doctype):
    global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
    company = global_defaults_doc.default_company
    return {"company":company}


@frappe.whitelist()
def get_department_working_hours(employee):
	"""
	Fetch the custom working hours for the employee's department.
	Returns 0 if the department name is not set for the employee
	or if the working hours are 0.
	"""
	if not employee:
		return {"error": "Employee is required"}

	employee_doc = frappe.get_doc("Employee", employee)
	department_name = getattr(employee_doc, 'department', None)
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
		return {"error": f"Unexpected error: {str(e)}"}