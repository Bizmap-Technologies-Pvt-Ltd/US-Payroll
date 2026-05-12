
import frappe
from datetime import datetime
import math

import sys
sys.path.insert(0, '/home/bizmap/frappe-bench/python-ach')
from ach.builder import AchFile

# import sys, os
# sys.path.insert(0, "/home/priya/workspace/bizmap_setup/frappe-bench-v16/python-ach")
# from ach.builder import AchFile


@frappe.whitelist()
def generate_ach_file(payroll_entry):
	ach_data = frappe.get_doc("ACH Report Details","ACH Report Details")
	settings = {
		'immediate_dest': ach_data.bank_routing_no,
		'immediate_org': ach_data.bank_account_no,
		'immediate_dest_name': ach_data.bank_name,
		'immediate_org_name': ach_data.bank_name,
		'company_id': ach_data.company_id,
	}

	ach_file = AchFile('A', settings)

	entries = []

	salary_slips = frappe.db.sql("""
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
			e.custom_second_account_allocation_,

			-- e.custom_third_bank_ac_no,
			-- e.custom_third_routing_number,
			-- e.custom_third_type_of_account,
			-- e.custom_third_account_allocation,

			e.custom_flat_bank_ac_no,
			e.custom_flat_routing_number,
			e.custom_flat_type_of_account,
			e.custom_flat_account_allocation,
			e.custom_flat_amount

		FROM `tabSalary Slip` ss
		LEFT JOIN `tabEmployee` e ON ss.employee = e.name
		WHERE ss.payroll_entry = %s
		AND e.custom_payment_method = 'Bank'
	""", (payroll_entry), as_dict=True)


	client_setup_doc = frappe.get_single("Client Setup")
	deduct_flat_amount_from_net_pay = client_setup_doc.deduct_flat_amount_from_net_pay

	if salary_slips and len(salary_slips) > 0:
		for row in salary_slips:
			net_pay = float(row.get("net_pay") or 0)

			if deduct_flat_amount_from_net_pay:
				flat_amount = row.get("custom_flat_amount") or 0
				net_pay = net_pay - flat_amount

			# allocations
			primary_pct = float(row.get("custom_account_allocation_") or 100)
			second_pct = float(row.get("custom_second_account_allocation_") or 0)
			# third_pct = float(row.get("custom_third_account_allocation") or 0)

			primary_amt = round(net_pay * primary_pct / 100, 2)
			second_amt = round(net_pay * second_pct / 100, 2)
			# third_amt = round(net_pay * third_pct / 100, 2)

			# PRIMARY ACCOUNT
			if row.get("custom_routing_number") and row.get("bank_ac_no") and primary_amt > 0:
				entries.append({
					"type": "22" if row.get('custom_type_of_account') == "Checking" else "32",
					"routing_number": row.get("custom_routing_number"),
					"account_number": row.get("bank_ac_no"),
					"amount": primary_amt,
					"name": row.get("employee_name")
				})

			# SECOND ACCOUNT
			if row.get("custom_second_routing_number") and row.get("custom_second_bank_ac_no") and second_amt > 0:
				entries.append({
					"type": "22" if row.get('custom_second_type_of_account') == "Checking" else "32",
					"routing_number": row.get("custom_second_routing_number"),
					"account_number": row.get("custom_second_bank_ac_no"),
					"amount": second_amt,
					"name": row.get("employee_name")
				})

			# # THIRD ACCOUNT
			# if row.get("custom_third_routing_number") and row.get("custom_third_bank_ac_no") and third_amt > 0:
			# 	entries.append({
			# 		"type": "22" if row.get('custom_third_type_of_account') == "Checking" else "32",
			# 		"routing_number": row.get("custom_third_routing_number"),
			# 		"account_number": row.get("custom_third_bank_ac_no"),
			# 		"amount": third_amt,
			# 		"name": row.get("employee_name")
			# 	})


			flat_amount = row.get("custom_flat_amount") or 0
			# FLAT ACCOUNT
			if deduct_flat_amount_from_net_pay and row.get("custom_flat_routing_number") and row.get("custom_flat_bank_ac_no") and flat_amount > 0:
				entries.append({
					"type": "22" if row.get('custom_flat_type_of_account') == "Checking" else "32",
					"routing_number": row.get("custom_flat_routing_number"),
					"account_number": row.get("custom_flat_bank_ac_no"),
					"amount": flat_amount,
					"name": row.get("employee_name")
				})

	if not entries:
		frappe.throw("No valid salary slips found for ACH generation.")

	# Add entries to ACH file
	ach_file.add_batch('PPD', entries, credits=True, debits=False)

	# Generate ACH file content
	ach_data = ach_file.render_to_string()

	# Save file in Frappe
	file = frappe.get_doc({
		"doctype": "File",
		"file_name": "ach_file.txt",
		"content": ach_data
	})
	file.insert()

	frappe.msgprint("ACH File Generated Successfully")

	# Return the file URL dynamically
	return file.file_url



# ==============================================below is the testing code===============================================
import sys
sys.path.insert(0, '/home/suraj/frappe-bench/pyACH')
from pyach.ACHRecordTypes import ACHFile, BatchHeader, Entry
import frappe
import os

@frappe.whitelist()
def generate_ach_filess(payroll_entry):
	try:
		# Fetch salary slips from the database
		salary_slips = frappe.db.sql("""
			SELECT 
				ss.name AS salary_slip,
				ss.employee AS employee_id,
				e.employee_name,
				ss.net_pay,
				ss.posting_date,
				e.bank_ac_no,
				e.custom_type_of_account,
				e.custom_payment_method,
				e.custom_routing_number
			FROM 
				`tabSalary Slip` ss
			LEFT JOIN 
				`tabEmployee` e ON ss.employee = e.name
			WHERE 
				ss.payroll_entry = %s AND e.custom_payment_method = 'Bank'
		""", (payroll_entry), as_dict=True)

		if not salary_slips:
			frappe.throw("No salary slips found for this payroll entry.")

		# ✅ Initialize ACH File
		ach_file = ACHFile()
		ach_file.destination_routing_number = '123456789'
		ach_file.origin_id = '987654321'
		ach_file.file_id_modifier = 'A'
		ach_file.destination_name = 'Destination Bank'
		ach_file.origin_name = 'Origin Bank'

		# ✅ Create file header before saving
		ach_file.create_header()

		# ✅ Create an ACH Batch
		batch = BatchHeader(
			company_name='Your Company Name',
			discretionary_data='Payroll',
			company_identification_number='123456789',
			entry_class_code='PPD',
			entry_description='Payroll Payment',
			dfi_number='12345678',
			batch_number=ach_file.get_next_batch_number(),
			id_store=ach_file.id_store
		)

		# ✅ Add Entries from Salary Slips
		for slip in salary_slips:
			routing_number = slip.get("custom_routing_number")
			account_number = slip.get("bank_ac_no")
			employee_id = slip.get("employee_id")
			employee_name = slip.get("employee_name")
			net_pay = int(slip.get("net_pay", 0) * 100)  # Convert to cents

			if not routing_number or not account_number:
				frappe.log_error(
					f"Missing routing number or account number for employee: {employee_id}",
					"ACH Generation Error"
				)
				continue

			# ✅ Add Entry to Batch
			batch.add_entry(
				transaction_code='22',  # Checking account credit
				routing_number=routing_number[:8],
				account_number=account_number,
				amount=net_pay,
				identification_number=employee_id,
				receiver_name=employee_name,
				discretionary_data=''
			)

		# ✅ Finalize batch and add to ACH file
		batch.finalize()
		ach_file.batch_records.append(batch)

		# ✅ Generate and save the file
		file_path = frappe.utils.get_files_path(f'ACH_{payroll_entry}.txt')
		ach_file.save(file_path)

		# ✅ Return file URL
		return {'file_url': f'/private/files/ACH_{payroll_entry}.txt'}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'ACH File Generation Error')
		frappe.throw(f'Error generating ACH file: {str(e)}')









