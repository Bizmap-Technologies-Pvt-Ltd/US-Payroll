# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class LeaveAllocationTool(Document):
	pass


@frappe.whitelist()
def get_employees(leave_type: str, from_date: str, to_date: str, department: str | None = None):
	filters = {"status": "Active"}

	if department:
		filters["department"] = department

	employees = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "department"])

	for emp in employees:
		if emp.department:
			dept_doc = frappe.get_doc("Department", emp.department)
			emp["department"] = dept_doc.name if dept_doc else None

		employee = emp.name

		last_submitted_pto_balance = 0
		last_submitted_ct_balance = 0

		# --- 🔹 Get last PTO balance ---
		if leave_type == "PTO":
			leave_alloc = frappe.db.get_value(
				"Leave Allocation",
				{
					"employee": employee,
					"leave_type": "PTO",
					"docstatus": 1,
					"from_date": [">=", from_date],
					"to_date": ["<=", to_date],
				},
				["name", "from_date", "to_date", "total_leaves_allocated", "modified"],
				as_dict=True,
			)

			total_leaves_allocated_pto = float(leave_alloc.total_leaves_allocated) if leave_alloc else 0

			past_pto = frappe.db.sql(
				"""
				SELECT pe.name AS payroll_entry, ped.custom_available_pto, ped.custom_pto_leaves_allocated
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
				WHERE ped.employee = %s
				  AND pe.docstatus = 1
				  AND pe.status != 'Failed'
				  AND pe.start_date >= %s
				  AND pe.start_date <= %s
				ORDER BY pe.start_date DESC
				LIMIT 1
				""",
				(employee, from_date, to_date),
				as_dict=True,
			)

			last_submitted_pto_balance = float(past_pto[0].custom_available_pto) if past_pto else 0
			emp["balanced_pto_leaves"] = last_submitted_pto_balance
			emp["total_leaves_allocated_pto"] = total_leaves_allocated_pto

		# --- 🔹 Get last Comp Time balance ---
		elif leave_type == "Comp Time":
			ct_leave_alloc = frappe.db.get_value(
				"Leave Allocation",
				{
					"employee": employee,
					"leave_type": "Comp Time",
					"docstatus": 1,
					"from_date": [">=", from_date],
					"to_date": ["<=", to_date],
				},
				["name", "from_date", "to_date", "total_leaves_allocated", "modified"],
				as_dict=True,
			)

			total_leaves_allocated_ct = float(ct_leave_alloc.total_leaves_allocated) if ct_leave_alloc else 0

			past_comp = frappe.db.sql(
				"""
				SELECT pe.name AS payroll_entry, ped.custom_available_ct
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
				WHERE ped.employee = %s
				  AND pe.docstatus = 1
				  AND pe.status != 'Failed'
				  AND pe.start_date >= %s
				  AND pe.start_date <= %s
				ORDER BY pe.start_date DESC
				LIMIT 1
				""",
				(employee, from_date, to_date),
				as_dict=True,
			)

			last_submitted_ct_balance = float(past_comp[0].custom_available_ct) if past_comp else 0
			emp["balanced_ct_leaves"] = last_submitted_ct_balance
			emp["total_leaves_allocated_ct"] = total_leaves_allocated_ct

	return employees


@frappe.whitelist(methods=["POST"])
def generate_leave_allocations(doc: str | dict[str, Any]):
	if isinstance(doc, str):
		doc = json.loads(doc)

	created = []
	skipped = []

	for row in doc.get("leave_allocation_details"):
		if not row.get("leave_type") or not row.get("employee"):
			frappe.throw(
				_(
					"Please select <b>Leave Type</b> for employee <b>{employee}</b> in row <b>{row}</b>"
				).format(
					employee=row.get("employee"),
					row=row.get("idx"),
				)
			)
			continue

		submitted_leave_allocation = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": row.get("employee"),
				"leave_type": row.get("leave_type"),
				"from_date": doc.get("from_date"),
				"to_date": doc.get("to_date"),
				"docstatus": 1,
			},
			"name",
		)
		if submitted_leave_allocation:
			skipped.append({"employee": row.get("employee"), "leave_type": row.get("leave_type")})

			leave_doc = frappe.get_doc("Leave Allocation", submitted_leave_allocation)
			# leave_doc.new_leaves_allocated = row.get("new_leaves_allocated") or 0
			leave_doc.new_leaves_allocated = row.get("total_leaves_allocated") or 0
			leave_doc.custom_allocation_change_reason = row.get("allocation_change_reason")
			leave_doc.submit()

		else:
			la = frappe.new_doc("Leave Allocation")
			la.employee = row.get("employee")
			la.employee_name = row.get("employee_name")
			la.leave_type = row.get("leave_type")
			la.from_date = doc.get("from_date")
			la.to_date = doc.get("to_date")
			# la.new_leaves_allocated = row.get("new_leaves_allocated") or 0
			la.new_leaves_allocated = row.get("total_leaves_allocated") or 0
			la.posting_date = nowdate()
			la.custom_transaction_date = nowdate()
			la.custom_allocation_change_reason = row.get("allocation_change_reason")

			la.insert(ignore_permissions=True)
			la.submit()

			created.append({"name": la.name, "employee": la.employee, "leave_type": la.leave_type})

	return {"created": created, "skipped": skipped}
