import json

import frappe
from frappe.utils import nowdate


def validate(doc, method):
	pass


def before_insert(doc, method):
	pass


def after_insert(doc, method):
	set_transaction_date(doc)


def set_transaction_date(doc):
	if not doc.custom_transaction_date:
		doc.custom_transaction_date = nowdate()


@frappe.whitelist()
def get_old_leave_allocation_amount(employee: str, amount: float):
	fy_info = get_us_fiscal_year()
	fiscal_year_start = fy_info["fiscal_year_start"]
	fiscal_year_end = fy_info["fiscal_year_end"]
	doc = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"from_date": ["between", [fiscal_year_start, fiscal_year_end]],
			"docstatus": 1,
		},
		fields=["name", "new_leaves_allocated"],
	)
	if doc:
		existing_amount = float(doc[0]["new_leaves_allocated"])
		if float(amount) != existing_amount:
			return {
				"status": "exists_different_amount",
				"existing_amount": existing_amount,
				"employee": employee,
				"new_amount": float(amount),
			}

		return {"status": "exists_same_amount", "employee": employee}

	return {"employee": employee, "amount": float(amount)}


@frappe.whitelist()
def update_allocated_leaves(
	employee: str,
	amount: float,
	reason: str,
	existing_amount: float,
):
	fy_info = get_us_fiscal_year()
	fiscal_year_start = fy_info["fiscal_year_start"]
	fiscal_year_end = fy_info["fiscal_year_end"]
	doc = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"from_date": ["between", [fiscal_year_start, fiscal_year_end]],
			"docstatus": 1,
		},
		fields=["name", "new_leaves_allocated"],
	)

	if doc:
		existing_amount = float(existing_amount)
		existing_doc = frappe.get_doc("Leave Allocation", doc[0].name)
		existing_doc.new_leaves_allocated = amount
		existing_doc.custom_allocation_change_reason = reason
		existing_doc.custom_previous_leaves_allocated = existing_amount
		existing_doc.save()
	return {"status": "updated", "existing_amount": existing_amount}


@frappe.whitelist()
def get_us_fiscal_year():
	from frappe.utils import getdate, now_datetime

	today = now_datetime().date()
	year = today.year
	if today.month < 10:
		start_year = year - 1
		end_year = year
	else:
		start_year = year
		end_year = year + 1

	fiscal_year_start = getdate(f"{start_year}-10-01")
	fiscal_year_end = getdate(f"{end_year}-09-30")
	return {
		"fiscal_year": f"{start_year}-{end_year}",
		"fiscal_year_start": fiscal_year_start,
		"fiscal_year_end": fiscal_year_end,
	}
