# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccountNumber(Document):
	def validate(self):
		self.validate_account_number_length()

	def validate_account_number_length(self):
		fund_settings = frappe.get_doc("Fund Settings", "Fund Settings")
		required_account_number_length = fund_settings.required_account_number_length
		account_number = self.account_number
		if len(account_number) > required_account_number_length:
			frappe.throw(
				f"Account number length should not be greater than {required_account_number_length} characters."
			)


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company": company}
