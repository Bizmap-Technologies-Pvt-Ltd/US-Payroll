import datetime
import json
from typing import Any

import erpnext
import frappe
from dateutil.relativedelta import relativedelta
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import (
	DATE_FORMAT,
	add_days,
	add_months,
	add_to_date,
	cint,
	comma_and,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	now_datetime,
	rounded,
	today,
)
from hrms.hr.doctype.leave_application.leave_application import get_leave_details
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_month_details


def before_save(doc, method):
	for employee in doc.employees:
		if employee.custom_total_working_hours and employee.custom_hourly_rate:
			total_amount = employee.custom_total_working_hours * employee.custom_hourly_rate
			employee.custom_total_amount = total_amount
		else:
			employee.custom_total_amount = 0

		if employee.custom_total_overtime_hours and employee.custom_overtime_hourly_rate:
			total_overtime_amount = (
				employee.custom_total_overtime_hours * employee.custom_overtime_hourly_rate
			)
			employee.custom_total_overtime_amount = total_overtime_amount
		else:
			employee.custom_total_overtime_amount = 0


@frappe.whitelist()
def get_account_options():
	company = frappe.defaults.get_global_default("company")
	all_accounts = frappe.db.get_all(
		"Account",
		filters={"is_group": False, "account_type": ["in", ["Bank", "Cash"]], "company": company},
		fields=["name"],
	)
	options = []
	for ac in all_accounts:
		options.append(ac.get("name"))
	return options


@frappe.whitelist()
def calculate_employee_totals(
	doc: str,
	start_date: str,
	end_date: str,
):
	if isinstance(doc, str):
		payroll_entry = json.loads(doc)
	employee_totals = {}
	for employee_row in payroll_entry.get("employees", []):
		employee_id = employee_row.get("employee")
		if employee_id:
			attendance_records = frappe.get_all(
				"Attendance",
				filters={"employee": employee_id, "attendance_date": ["between", [start_date, end_date]]},
				fields=["custom_total_amount", "overtime_amount"],
			)

			total_custom_amount = sum(record.get("custom_total_amount", 0) for record in attendance_records)
			total_overtime_amount = sum(record.get("overtime_amount", 0) for record in attendance_records)
			employee_totals[employee_id] = {
				"custom_total_amount": total_custom_amount,
				"overtime_amount": total_overtime_amount,
			}
	return {"employee_totals": employee_totals}


@frappe.whitelist()
def get_bank_entry_against_payroll(doc_id: str):
	bank_entry_jv = frappe.db.sql(
		"""
		SELECT jv.name
		FROM `tabJournal Entry` jv
		JOIN `tabJournal Entry Account` acc ON jv.name = acc.parent
		WHERE jv.voucher_type = 'Bank Entry'
		AND acc.reference_type = 'Payroll Entry'
		AND acc.reference_name = %s
	""",
		(doc_id,),
		as_dict=True,
	)

	check_entry_jv = frappe.db.sql(
		"""
		SELECT jv.name
		FROM `tabJournal Entry` jv
		JOIN `tabJournal Entry Account` acc ON jv.name = acc.parent
		WHERE jv.voucher_type = 'Bank Entry'
		AND jv.custom_check_entry = 1
		AND acc.reference_type = 'Payroll Entry'
		AND acc.reference_name = %s
	""",
		(doc_id,),
		as_dict=True,
	)

	return {"bank_entry_jv": bank_entry_jv, "check_entry_jv": check_entry_jv}


@frappe.whitelist()
def get_global_defaults_values(doctype: str):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company": company}


@frappe.whitelist()
def render_html_for_holiday(
	start_date: str,
	end_date: str,
):
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	holiday_list = frappe.db.get_value(
		"Company", frappe.defaults.get_global_default("company"), "default_holiday_list"
	)
	if not holiday_list:
		return {"status": "error", "message": _("No holiday list found for the company.")}

	holidays = frappe.db.sql(
		"""
		SELECT holiday_date, description FROM `tabHoliday`
		WHERE parent=%(holiday_list)s AND holiday_date >= %(start_date)s AND holiday_date <= %(end_date)s
		ORDER BY holiday_date ASC
	""",
		{
			"holiday_list": holiday_list,
			"start_date": start_date,
			"end_date": end_date,
		},
		as_dict=True,
	)

	# **Filter out Saturdays and Sundays**
	filtered_holidays = [
		holiday
		for holiday in holidays
		if holiday.holiday_date.weekday() not in (5, 6)  # 5 = Saturday, 6 = Sunday
	]

	if filtered_holidays:
		return {"status": "success", "holidays": filtered_holidays}
	else:
		return {
			"status": "success",
			"message": "No holidays found in the given date range excluding weekends.",
		}


@frappe.whitelist()
def get_submitted_check_stubs(doc_id: str):
	all_ss = frappe.db.get_all(
		"Salary Slip", filters={"payroll_entry": doc_id, "docstatus": 1}, fields=["name"]
	)

	submitted_entries = []
	for slip in all_ss:
		try:
			frappe.get_doc("Salary Slip", slip.get("name"))
			submitted_entries.append(slip.get("name"))

		except Exception:
			frappe.logger("us_payroll").exception("Unable to load submitted salary slip")

	return {"submitted_entries": submitted_entries}


@frappe.whitelist()
def get_employees_with_bank_payment(doc_id: str):
	employees = frappe.get_all("Payroll Employee Detail", filters={"parent": doc_id}, fields=["employee"])

	bank_employees = []
	for emp in employees:
		employee_doc = frappe.get_doc("Employee", emp["employee"])
		if employee_doc.custom_payment_method == "Bank":
			bank_employees.append(employee_doc.name)

	return bank_employees


@frappe.whitelist()
def get_salary_to_print(doc_id: str):
	salary_slip_list = frappe.db.sql(
		"""
		SELECT
			ss.name AS name,
			ss.employee AS employee_id,
			e.employee_name,
			e.custom_payment_method,
			ss.custom_check_no
		FROM
			`tabSalary Slip` ss
		LEFT JOIN
			`tabEmployee` e ON ss.employee = e.name
		WHERE
			ss.payroll_entry = %s AND e.custom_payment_method = 'Check'
			ORDER BY
			ss.custom_check_no DESC
	""",
		(doc_id,),
		as_dict=True,
	)

	return [salary_slip.get("name") for salary_slip in salary_slip_list]


@frappe.whitelist()
def get_salary_to_print_for_bank(doc_id: str):
	salary_slip_list = frappe.db.sql(
		"""
		SELECT
			ss.name AS name,
			ss.employee AS employee_id,
			e.employee_name,
			e.custom_payment_method
		FROM
			`tabSalary Slip` ss
		LEFT JOIN
			`tabEmployee` e ON ss.employee = e.name
		WHERE
			ss.payroll_entry = %s AND e.custom_payment_method = 'Bank'
	""",
		(doc_id,),
		as_dict=True,
	)
	return [salary_slip.get("name") for salary_slip in salary_slip_list]


@frappe.whitelist()
def get_check_stubs_for_void_condition(filters: str) -> list[list[Any]]:
	filters_dict: dict[str, Any] = json.loads(filters)

	all_slips = frappe.db.get_all(
		"Salary Slip",
		{
			"payroll_entry": filters_dict.get("payroll_entry"),
			"docstatus": ["in", [1]],
		},
		["name", "custom_check_no"],
	)

	valid_slips = [
		[slip.get("name"), slip.get("custom_check_no")] for slip in all_slips if slip.get("custom_check_no")
	]

	return valid_slips


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_check_to_void(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict[str, Any] | None = None,
):
	all_slips = frappe.db.get_all(
		"Salary Slip",
		{
			"payroll_entry": filters.get("payroll_entry"),
			"docstatus": ["in", [0, 1]],
		},
		["name", "custom_check_no", "employee_name"],
	)
	excluded_slips = tuple(slip.name for slip in all_slips) or ("",)

	entries = frappe.db.sql(
		"""
		SELECT name, custom_check_no, employee_name
		FROM `tabSalary Slip`
		WHERE docstatus = 1
		  AND payroll_entry = %(pe)s
		  AND (custom_check_no IS NOT NULL)
		  AND (
				name LIKE %(txt)s
				OR custom_check_no LIKE %(txt)s
			)
		  AND (%(has_excluded_slips)s = 0 OR name NOT IN %(excluded_slips)s)
		ORDER BY name
		LIMIT %(start)s, %(page_len)s
	""",
		{
			"pe": filters.get("payroll_entry"),
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
			"has_excluded_slips": int(bool(all_slips)),
			"excluded_slips": excluded_slips,
		},
	)

	return entries


@frappe.whitelist(methods=["POST"])
def assign_new_check_no(
	source_name: str,
	payroll_entry: str,
	new_check_required: str | None = None,
	reason: str | None = None,
	target_doc: str | None = None,
):
	new_check_required = int(new_check_required) if isinstance(new_check_required, str) else False
	payroll_entry_doc = frappe.get_doc("Payroll Entry", payroll_entry)

	if new_check_required:
		payroll_entry_doc.custom_new_check_required = True
		payroll_entry_doc.save(ignore_permissions=True)

	all_checks = frappe.get_all(
		"Check", filters={"status": "Available"}, fields=["name", "check_number", "status"], order_by="name"
	)

	# If no new check required, just void the existing one
	if not new_check_required:
		cheque_no = frappe.db.get_value("Salary Slip", {"name": source_name}, "custom_check_no")
		check_doc = frappe.get_doc("Check", cheque_no)
		check_doc.status = "Void/Cancelled"
		check_doc.save(ignore_permissions=True)
		return {"check_voided": True}

	if not all_checks and new_check_required:
		frappe.throw(_("No check available."))

	# Pick the first available check
	new_check_no = all_checks[0].get("name")

	# Get the old check number from the slip
	old_check_no = frappe.db.get_value("Salary Slip", {"name": source_name}, "custom_check_no")

	# Void the old check
	if old_check_no:
		old_check_doc = frappe.get_doc("Check", old_check_no)
		old_check_doc.status = "Void/Cancelled"
		old_check_doc.reference = source_name
		old_check_doc.reason_for_cancellation = reason
		old_check_doc.save(ignore_permissions=True)

	# Assign new check to the existing slip
	frappe.db.set_value("Salary Slip", source_name, "custom_check_no", new_check_no)

	from frappe.utils import get_url

	site_url = get_url()
	check_url = f"{site_url}/app/check/{old_check_no}"

	reason_of_new_check_no = f"New check {new_check_no} assigned, old check <a href= '{check_url}'><b>{old_check_no}</b></a> voided."

	emp_name = frappe.db.get_value("Salary Slip", {"name": source_name}, "employee_name")
	# Mark the new check as issued
	new_check_doc = frappe.get_doc("Check", new_check_no)
	new_check_doc.status = "Issued"
	new_check_doc.reference = source_name
	new_check_doc.reason = reason_of_new_check_no
	new_check_doc.save(ignore_permissions=True)

	return {"updated_slip": source_name, "new_check_no": new_check_no, "emp_name": emp_name}


@frappe.whitelist()
def get_department_working_hours(employee: str):
	"""
	Fetch the custom working hours for the employee's department.
	Returns 0 if the department name is not set for the employee
	or if the working hours are 0.
	"""
	if not employee:
		return {"error": _("Employee is required")}

	employee_doc = frappe.get_doc("Employee", employee)
	department_name = getattr(employee_doc, "department", None)
	if not department_name:
		return {"working_hours": 0}

	try:
		# Fetch the department document from the department doctype
		department_doc = frappe.get_doc("Department", department_name)
		working_hours = getattr(department_doc, "custom_working_hours", None)
		if not working_hours or working_hours == 0:
			return {"working_hours": 0}

		return {"working_hours": working_hours}

	except frappe.DoesNotExistError:
		return 0

	except Exception as e:
		return {"error": f"Unexpected error: {e!s}"}


@frappe.whitelist()
def toggle_insurance_components(deduct_insurance: int):
	set_to = 0 if int(deduct_insurance) else 1

	# --- Update Salary Components ---
	comps = frappe.db.get_list(
		"Salary Component", filters={"custom_is_this_insurance_component": 1}, fields=["name"]
	)
	for comp in comps:
		frappe.db.set_value("Salary Component", comp.name, "do_not_include_in_total", set_to)

	# --- Update Employee Insurance Deduction child rows in ALL SSA ---
	ssas = frappe.db.get_list("Salary Structure Assignment", fields=["name"])
	for ssa in ssas:
		children = frappe.db.get_list(
			"Employee Insurance Deduction",
			filters={
				"parent": ssa.name,
				"parenttype": "Salary Structure Assignment",
				"parentfield": "custom_employee_insurance_deduction",
			},
			fields=["name"],
		)
		for row in children:
			frappe.db.set_value("Employee Insurance Deduction", row.name, "do_not_include_in_total", set_to)

	return {"updated_components": len(comps), "updated_ssa": len(ssas)}
