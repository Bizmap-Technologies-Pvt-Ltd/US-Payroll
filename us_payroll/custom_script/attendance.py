import frappe
import json

def validate(self,method):
	if self.custom_overtime_hours:
		self.custom_overtime_amount = self.custom_overtime_hours * self.custom_overtime_rate

	if self.working_hours:
		self.custom_total_amount = self.working_hours * self.custom_hourly_rate

def on_submit(self,method):
	pass
	# if self.overtime_amount:
	# 	additional_salary(self,self.overtime_amount,component = "Overtime")
	# if self.misc_ded_amount:
	# 	additional_salary(self,self.misc_ded_amount,component = "MISC_DED")
	# if self.penalty_amount:
	# 	additional_salary(self,self.penalty_amount,component = "PENALTY")
	# if self.salary_advance_amount:
	# 	additional_salary(self,self.salary_advance_amount,component = "SAL_ADV")
	# if self.other_allowance_amount:
	# 	additional_salary(self,self.other_allowance_amount,component = "OTHER ALLOWANCE")
	# if self.tds_amount:
	#	additional_salary(self,self.tds_amount,component = "TDS")

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