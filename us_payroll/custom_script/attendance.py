import frappe
import json

def validate(self,method):
	if self.custom_overtime_hours:
		self.custom_overtime_amount = self.custom_overtime_hours * self.custom_overtime_rate

	if self.working_hours:
		self.custom_total_amount = self.working_hours * self.custom_hourly_rate

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