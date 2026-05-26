import frappe
import json
from frappe import _
from frappe.utils import getdate, today,flt

def validate(doc, method):
	# hourly_rate = doc.custom_hourly_rate
	# if hourly_rate:
	#     overtime_rate = hourly_rate*1.5
	#     doc.overtime_rate = overtime_rate

	primary_pct = float(doc.custom_account_allocation_ or 100)
	second_pct = float(doc.custom_second_account_allocation_ or 0)
	# third_pct = float(doc.custom_third_account_allocation or 0)
	# total_pct = primary_pct + second_pct + third_pct

	total_pct = primary_pct + second_pct
	if round(total_pct, 2) != 100:
		frappe.throw(f"Total allocation percentage must equal 100%, but got {total_pct}%.")


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company":company}
