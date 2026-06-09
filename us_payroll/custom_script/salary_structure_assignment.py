import json

import frappe


@frappe.whitelist()
def get_global_defaults_values(doctype: str):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company": company}
