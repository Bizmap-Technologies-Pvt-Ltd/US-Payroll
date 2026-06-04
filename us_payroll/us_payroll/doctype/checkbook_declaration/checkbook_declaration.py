# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CheckbookDeclaration(Document):
	pass


@frappe.whitelist()
def generate_checks(docname):
	checkbook_doc = frappe.get_doc("Checkbook Declaration", docname)
	first_check_number = checkbook_doc.first_check_number
	no_of_leaves = checkbook_doc.no_of_leaves
	no_of_leaves = int(no_of_leaves)
	bank = checkbook_doc.bank
	for i in range(no_of_leaves):
		first_check_number = int(first_check_number)
		check_number = first_check_number + i
		check_doc = frappe.get_doc(
			{"doctype": "Check", "check_number": check_number, "bank": bank, "status": "Available"}
		)
		check_doc.insert()
	return "Checks generated successfully."
