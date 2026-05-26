import frappe
import json
from frappe import _
from frappe.utils import getdate


# def validate(self,method):
# 	print("Aaaaalalallalalaa")
# 	if not self.cheque_date:
# 		self.cheque_date =  today()


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company":company}