import frappe
import json
from frappe import _
from frappe.utils import getdate, today,flt

def validate(doc, method):
	primary_pct = float(doc.custom_account_allocation_ or 100)
	second_pct = float(doc.custom_second_account_allocation_ or 0)

	total_pct = primary_pct + second_pct
	if round(total_pct, 2) != 100:
		frappe.throw(f"Total allocation percentage must equal 100%, but got {total_pct}%.")


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company":company}
