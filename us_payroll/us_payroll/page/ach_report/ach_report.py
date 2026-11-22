import math
import sys
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.utils import now_datetime

from us_payroll.ach_lib.builder import AchFile


@frappe.whitelist()
def generate_ach_file(payroll_entry: str):

	# Fetch allowed roles from ACH Report Page
	page_roles = frappe.get_all(
		"Has Role",
		filters={
			"parent": "ach-report",
			"parenttype": "Page",
			"parentfield": "roles",
		},
		pluck="role",
	)

	if not page_roles:
		frappe.throw(
			_("No roles are configured for the ACH Report Page."),
			frappe.PermissionError,
		)

	# Fetch roles explicitly assigned to logged-in user
	user_roles = frappe.get_all(
		"Has Role",
		filters={
			"parent": frappe.session.user,
			"parenttype": "User",
			"role": ["in", page_roles],
		},
		pluck="role",
	)

	# Strict permission check
	if not user_roles:
		frappe.throw(
			_("You do not have permission to generate an ACH file."),
			frappe.PermissionError,
		)

	# Check Payroll Entry permission
	if not frappe.has_permission("Payroll Entry", "read", payroll_entry):
		frappe.throw(
			_("You do not have permission to generate an ACH file for this Payroll Entry."),
			frappe.PermissionError,
		)

	# Existing ACH generation logic continues here
	ach_data = frappe.get_single("ACH Report Details")

	if ach_data and any(
		[ach_data.bank_routing_no, ach_data.bank_account_no, ach_data.bank_name, ach_data.company_id]
	):
		settings = {
			"immediate_dest": ach_data.bank_routing_no,
			"immediate_org": ach_data.bank_account_no,
			"immediate_dest_name": ach_data.bank_name,
			"immediate_org_name": ach_data.company_name,
			"company_id": ach_data.company_id,
		}
	else:
		site_url = get_url()
		ach_url = f"{site_url}/app/ach-report-details/ACH%20Report%20Details"
		frappe.throw(_(f"Please update the details in <a href= '{ach_url}' >ACH Report Details</a>"))

	ach_file = AchFile("A", settings)
	entries = []
	salary_slips = frappe.db.sql(
		"""
		SELECT
			ss.name AS salary_slip,
			ss.employee AS employee_id,
			e.employee_name,
			ss.net_pay,
			ss.posting_date,

			e.bank_ac_no,
			e.custom_routing_number,
			e.custom_type_of_account,
			e.custom_account_allocation_,

			e.custom_second_bank_ac_no,
			e.custom_second_routing_number,
			e.custom_second_type_of_account,
			e.custom_second_account_allocation_

		FROM `tabSalary Slip` ss
		LEFT JOIN `tabEmployee` e ON ss.employee = e.name
		WHERE ss.payroll_entry = %s
		AND e.custom_payment_method = 'Bank'
	""",
		(payroll_entry),
		as_dict=True,
	)

	client_setup_doc = frappe.get_single("Client Setup")
	deduct_flat_amount_from_net_pay = client_setup_doc.deduct_flat_amount_from_net_pay

	if salary_slips and len(salary_slips) > 0:
		for row in salary_slips:
			net_pay = float(row.get("net_pay") or 0)

			if deduct_flat_amount_from_net_pay:
				flat_amount = row.get("custom_flat_amount") or 0
				net_pay = net_pay - flat_amount

			primary_pct = float(row.get("custom_account_allocation_") or 100)
			second_pct = float(row.get("custom_second_account_allocation_") or 0)

			primary_amt = round(net_pay * primary_pct / 100, 2)
			second_amt = round(net_pay * second_pct / 100, 2)

			# PRIMARY ACCOUNT
			if row.get("custom_routing_number") and row.get("bank_ac_no") and primary_amt > 0:
				entries.append(
					{
						"type": "22" if row.get("custom_type_of_account") == "Checking" else "32",
						"routing_number": row.get("custom_routing_number"),
						"account_number": row.get("bank_ac_no"),
						"amount": primary_amt,
						"name": row.get("employee_name"),
					}
				)

			# SECOND ACCOUNT
			if (
				row.get("custom_second_routing_number")
				and row.get("custom_second_bank_ac_no")
				and second_amt > 0
			):
				entries.append(
					{
						"type": "22" if row.get("custom_second_type_of_account") == "Checking" else "32",
						"routing_number": row.get("custom_second_routing_number"),
						"account_number": row.get("custom_second_bank_ac_no"),
						"amount": second_amt,
						"name": row.get("employee_name"),
					}
				)

	if not entries:
		frappe.throw(_("No valid salary slips found for ACH generation."))

	# Add entries to ACH file
	ach_file.add_batch("PPD", entries, credits=True, debits=False)

	# Generate ACH file content
	ach_data = ach_file.render_to_string()

	# Save file in Frappe
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"ach_file_{frappe.generate_hash(length=12)}.txt",
			"content": ach_data,
			"is_private": 1,
			"attached_to_doctype": "Payroll Entry",
			"attached_to_name": payroll_entry,
		}
	)
	file.insert()

	frappe.msgprint(_("ACH File Generated Successfully"))

	# Return the file URL dynamically
	return file.file_url
