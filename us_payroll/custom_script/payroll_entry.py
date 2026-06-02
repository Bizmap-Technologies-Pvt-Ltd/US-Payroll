import frappe
import json
from frappe.utils import flt, getdate, add_days
import datetime
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	cint,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	rounded,
	today,
)


from dateutil.relativedelta import relativedelta
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import (
    DATE_FORMAT,
    add_days,
    add_to_date,
    cint,
    comma_and,
    date_diff,
    flt,
    get_link_to_form,
    getdate,
)
import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_month_details
from hrms.hr.doctype.leave_application.leave_application import get_leave_details


def validate(doc, method):
	insurance_deduction_limitation(doc)
	validate_do_not_include_in_total(doc)
	get_leave_balance(doc)
	calculate_holiday_hours(doc)
	calculate_working_hours(doc)

	for row in doc.employees: 
		if not row.custom_pto_hours:
			process_pto_leave_balance_and_carry_forward(doc)


def on_submit(doc, method):
	pass


def before_submit(doc,method):
	warning_msg(doc)

def before_save(doc, method):
	for employee in doc.employees:
		if employee.custom_total_working_hours and employee.custom_hourly_rate:
			total_amount = employee.custom_total_working_hours * employee.custom_hourly_rate
			employee.custom_total_amount = total_amount
		else:
			employee.custom_total_amount = 0

		if employee.custom_total_overtime_hours and employee.custom_overtime_hourly_rate:
			total_overtime_amount = employee.custom_total_overtime_hours * employee.custom_overtime_hourly_rate
			employee.custom_total_overtime_amount = total_overtime_amount
		else:
			employee.custom_total_overtime_amount = 0

def warning_msg(doc):
	for row in doc.employees:
		total_hours = float(row.custom_total_working_hours or 0)
		overtime = float(row.custom_total_overtime_hours or 0)
		comp_time = float(row.custom_comp_time or 0)
		pto = float(row.custom_pto_hours or 0)
		holiday = float(row.custom_holiday_hours or 0)
		base_amount = float(row.custom_base_amount or 0)
 
		if total_hours == 0 and overtime == 0 and comp_time == 0 and pto == 0 and holiday == 0 and base_amount == 0:
			frappe.throw(
				f"Row <b>{row.idx}</b> for employee <b>{row.employee_name}</b> "
				"has zero hours entered in all categories: "
				"<b>Hourly, Overtime, Comp Time, PTO, Holiday and Base Amount</b>. "
				"Please enter hours to proceed."
			)
			
def insurance_deduction_limitation(doc):
	if not doc.custom_deduct_insurance:
		fy_current = get_us_fiscal_year(today=doc.posting_date)
		current_fiscal_year = fy_current["fiscal_year"]
		fiscal_year_start = fy_current["fiscal_year_start"]
		fiscal_year_end = fy_current["fiscal_year_end"]

		if not current_fiscal_year:
			frappe.throw(_("Fiscal Year not found for posting date {0}").format(doc.posting_date))

		for d in doc.employees:  
			employee = d.employee
			emp_name = d.employee_name
			row = d.idx

			count = frappe.db.sql("""
				SELECT COUNT(pe.name)
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` child
					ON child.parent = pe.name
				WHERE pe.docstatus = 1
				  AND pe.custom_deduct_insurance = 0
				  AND child.employee = %s
				  AND pe.posting_date BETWEEN %s AND %s
			""", (employee, fiscal_year_start, fiscal_year_end))[0][0]

			if count >= 2:
				frappe.throw(_(f"Please remove employee <b>{emp_name}</b> from row <b>{row}</b>, as for this employee the insurance deduction has already been skipped twice in this fiscal year."))


def validate_do_not_include_in_total(doc):
	salary_components = frappe.get_all("Salary Component", filters={"custom_is_this_insurance_component": True}, fields=["name"])
	for sc in salary_components:
		sal_doc = frappe.get_doc("Salary Component", sc.name)
		if doc.custom_deduct_insurance and sal_doc.custom_is_this_insurance_component and sal_doc.do_not_include_in_total: 
			sal_doc.do_not_include_in_total = False
			frappe.db.set_value("Salary Component", sc.name, "do_not_include_in_total", 0)


def get_leave_balance(payroll_doc):  
	for row in payroll_doc.employees:
		# ----------------Comp time calculation------------
		leave_allocation_data= frappe.db.get_values("Leave Allocation", {'employee' : row.employee,
																			'leave_type':'Comp Time',
																			'docstatus':1},  
																		['name','from_date','total_leaves_allocated'],as_dict=1)
	   
		from frappe.utils import get_url
		site_url = get_url()
		leave_allocation_url = f"{site_url}/app/leave-allocation"
		
		if row.custom_comp_time > 0 and not leave_allocation_data:
			frappe.throw(f"Please allocate CT Leaves for employee <b>{row.employee_name}</b> in row <b>{row.get('idx')}</b> <a href= '{leave_allocation_url}' > Leave Allocation </a>")       
	   
		total_comp_leaves_allocated = 0
		if leave_allocation_data:
			leave_allocation_data = leave_allocation_data[0]
			leave_allocation_doc_name = leave_allocation_data.get('name')
			leave_allocation_from_date = leave_allocation_data.get('from_date')
			total_comp_leaves_allocated = leave_allocation_data.get('total_leaves_allocated')	   
			leave_application_leave_details = get_leave_details(row.employee,leave_allocation_from_date)

		payrol_entry_data = frappe.db.sql("""
							SELECT SUM(pd.custom_comp_time) as total_cmp_leaves
							FROM `tabPayroll Employee Detail` pd
							LEFT JOIN `tabPayroll Entry` pe ON pd.parent = pe.name
							WHERE pe.docstatus = 1 AND pd.employee = %s
						""", (row.employee,),as_dict=True)

		total_cmp_leaves_from_payroll = 0
		if payrol_entry_data:
			payrol_entry_data = payrol_entry_data[0]
			total_cmp_leaves_from_payroll = payrol_entry_data.get('total_cmp_leaves') or 0
			if total_cmp_leaves_from_payroll:
				total_cmp_leaves_from_payroll = total_cmp_leaves_from_payroll
				
		if row.custom_comp_time and total_comp_leaves_allocated:
			custom_comp_time = row.custom_comp_time
			total_cmp_leaves = custom_comp_time + total_cmp_leaves_from_payroll
			leave_application_comp_leaves_taken = leave_application_leave_details["leave_allocation"]['Comp Time']["leaves_taken"]		
			total_ct_available_leaves = total_comp_leaves_allocated - total_cmp_leaves + leave_application_comp_leaves_taken
			if (total_cmp_leaves + leave_application_comp_leaves_taken) <= total_comp_leaves_allocated:
				row.custom_available_ct = total_ct_available_leaves
			
			if (total_cmp_leaves + leave_application_comp_leaves_taken) > total_comp_leaves_allocated:
				frappe.throw(f"Comp Time leaves cannot be more than allocated leaves for employee <b>{row.employee_name}</b> in row <b>{row.get('idx')}</b>.")

		elif not row.custom_comp_time and total_comp_leaves_allocated:
			row.custom_available_ct = total_comp_leaves_allocated - total_cmp_leaves_from_payroll
	   
		elif not row.custom_comp_time and not total_comp_leaves_allocated:
			pass

		else:
			pass


@frappe.whitelist()
def get_us_fiscal_year(today=None):
	if not today:
		today = now_datetime().date()
	else:
		today = getdate(today)

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
		"fiscal_year_end": fiscal_year_end
	}

@frappe.whitelist()
def process_pto_leave_balance_and_carry_forward(payroll_doc):
	fy_current = get_us_fiscal_year(today=payroll_doc.start_date)
	current_fiscal_year = fy_current["fiscal_year"]
	fiscal_year_start = fy_current["fiscal_year_start"]
	fiscal_year_end = fy_current["fiscal_year_end"]
	
	next_fy_start = add_days(fiscal_year_end, 1)
	fy_next = get_us_fiscal_year(today=next_fy_start)
	next_fiscal_year = fy_next["fiscal_year"]

	for row in payroll_doc.employees:
		employee = row.employee
		leave_alloc = frappe.db.get_value(
				"Leave Allocation",
				{
					"employee": employee,
					"leave_type": "PTO",
					"docstatus": 1,
					"from_date": [">=", fiscal_year_start],
					"to_date": ["<=", fiscal_year_end]
				},
				["name", "from_date", "to_date", "total_leaves_allocated", "modified"],
				as_dict=True
			)
		total_leaves_allocated_pto = flt(leave_alloc.total_leaves_allocated) if leave_alloc else 0
		emp = frappe.db.get_value("Employee", employee, ["custom_pto_hours"], as_dict=True)
		pto_rate = flt(emp.custom_pto_hours) if emp else 0

		# Get last payroll's cumulative accrual (if exists)
		last_accrual = frappe.db.sql("""
			SELECT ped.custom_total_accrual_pto
			FROM `tabPayroll Entry` pe
			INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
			WHERE ped.employee = %s
			  AND pe.docstatus = 1
			  AND pe.start_date >= %s
			  AND pe.start_date <= %s
			ORDER BY pe.start_date DESC
			LIMIT 1
		""", (employee, fiscal_year_start, fiscal_year_end), as_dict=True)

		prev_total_accrual = flt(last_accrual[0].custom_total_accrual_pto) if last_accrual else 0

		# Add current pto_rate to running total
		row.custom_total_accrual_pto = prev_total_accrual + pto_rate
	   
		past_pto = frappe.db.sql("""
			SELECT pe.name AS payroll_entry, ped.custom_available_pto, ped.custom_pto_leaves_allocated
			FROM `tabPayroll Entry` pe
			INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
			WHERE ped.employee = %s
			  AND pe.docstatus = 1
			  AND pe.start_date >= %s
			  AND pe.start_date <= %s
			ORDER BY pe.start_date DESC
			LIMIT 1
		""", (employee, fiscal_year_start, fiscal_year_end), as_dict=True)

		cumulative_pto = flt(past_pto[0].custom_available_pto) if past_pto else 0
		past_alloc_used = flt(past_pto[0].custom_pto_leaves_allocated) if past_pto and past_pto[0].custom_pto_leaves_allocated else 0

		new_pto_balance = cumulative_pto + pto_rate
		delta_allocation = (total_leaves_allocated_pto - past_alloc_used) if leave_alloc else 0

		row.custom_available_pto = new_pto_balance + delta_allocation
		row.custom_pto_leaves_allocated = total_leaves_allocated_pto

		# --------------------------------    CARRY FORWARD Logic  --------------------------------------------------
		# Check if this is the first payroll for the fiscal year for this employee
		first_payroll_in_fy = not frappe.db.exists(
			"Payroll Employee Detail",
			{
				"employee": employee,
				"parenttype": "Payroll Entry",
				"start_date": ["between", [fiscal_year_start, fiscal_year_end]]
			}
		)

		if first_payroll_in_fy:
			already_carry_forwarded = frappe.db.sql("""
				SELECT ped.name
				FROM `tabPayroll Employee Detail` ped
				INNER JOIN `tabPayroll Entry` pe ON pe.name = ped.parent
				WHERE ped.employee = %s
				  AND pe.docstatus = 1
				  AND pe.start_date BETWEEN %s AND %s
				  AND IFNULL(ped.custom_pto_carry_applied, 0) = 1
				LIMIT 1
			""", (employee, fiscal_year_start, fiscal_year_end), as_dict=True)

		# row.custom_pto_carry_applied = False
		if first_payroll_in_fy and not already_carry_forwarded:
			# Get the last payroll from previous fiscal year
			prev_payroll = frappe.db.sql("""
				SELECT pe.name, ped.custom_available_pto
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
				WHERE ped.employee = %s
				AND pe.docstatus = 1
				AND pe.start_date < %s
				ORDER BY pe.end_date DESC
				LIMIT 1
			""", (employee, fiscal_year_start), as_dict=True)

			leave_type = frappe.db.get_value(
				"Leave Type",
				{"name": "PTO"},
				["custom_is_accrual_rate", "custom_carry_forward_hours"],
				as_dict=True
			)

			if prev_payroll and leave_type and leave_type.custom_is_accrual_rate:
				carry_limit = flt(leave_type.custom_carry_forward_hours)
				prev_balance = flt(prev_payroll[0].custom_available_pto)
				carry_forward_amount = min(prev_balance, carry_limit)

				if carry_forward_amount > 0:
					row.custom_available_pto += carry_forward_amount 
					row.custom_carry_forward_pto = carry_forward_amount
					row.custom_pto_carry_applied = True

	return payroll_doc


def calculate_holiday_hours(doc):
	start_date = doc.get("start_date")
	end_date = doc.get("end_date")

	if not start_date or not end_date:
		frappe.throw("Please select both Start Date and End Date.")

	start_date = getdate(start_date)
	end_date = getdate(end_date)

	holiday_list = frappe.db.get_value("Company", frappe.defaults.get_global_default("company"), "default_holiday_list")

	if not holiday_list:
		frappe.throw("No holiday list found for the company.")

	holidays = frappe.db.sql("""
		SELECT holiday_date, description FROM `tabHoliday`
		WHERE parent=%s AND holiday_date BETWEEN %s AND %s
		ORDER BY holiday_date ASC
	""", (holiday_list, start_date, end_date), as_dict=True)

	# **Filter out Saturdays and Sundays**
	filtered_holidays = [
		holiday for holiday in holidays if holiday.holiday_date.weekday() not in (5, 6)  # 5 = Saturday, 6 = Sunday
	]

	total_holiday_hours = len(filtered_holidays) * 8  # Each holiday = 8 hours	
	if doc.get("employees"):
		for row in doc.get("employees"):
			if row.custom_holiday_hours and row.custom_holiday_hours != total_holiday_hours:
				setattr(row, "custom_holiday_amount", (row.custom_hourly_rate or 0) * row.custom_holiday_hours)
				continue			

			if total_holiday_hours and row.custom_holiday_hours == 0:
				setattr(row, "custom_holiday_amount", (row.custom_hourly_rate or 0) * row.custom_holiday_hours)
				continue

			setattr(row, "custom_holiday_hours", total_holiday_hours)
			setattr(row, "custom_holiday_amount", (row.custom_hourly_rate or 0) * total_holiday_hours)
	# doc.save(ignore_permissions=True)

def calculate_working_hours(doc):
	for row in doc.employees:
		if not row.custom_total_working_hours:

			total_hours, overtime_hours = frappe.db.sql("""
				SELECT SUM(working_hours - actual_overtime_duration), SUM(actual_overtime_duration)
				FROM `tabAttendance`
				WHERE employee = %s
				AND attendance_date BETWEEN %s AND %s
				AND status IN ('Present', 'Half Day', 'Work From Home')
				AND docstatus = 1
			""", (row.employee, doc.start_date, doc.end_date))[0]

			row.custom_total_working_hours = total_hours or 0
			row.custom_total_overtime_hours = overtime_hours or 0

@frappe.whitelist()
def get_account_options():
	company = frappe.defaults.get_global_default("company")
	all_accounts = frappe.db.get_all("Account", filters={'is_group': False,
				'account_type': ['in', ["Bank", "Cash"]],
				'company':company},
				fields=["name"])
	options = [] 
	for ac in all_accounts:
		options.append(ac.get("name"))
	return options


@frappe.whitelist()
def calculate_employee_totals(doc, start_date, end_date):
	if isinstance(doc, str):
		payroll_entry = json.loads(doc)
	employee_totals = {}
	for employee_row in payroll_entry.get('employees', []):
		employee_id = employee_row.get('employee')
		if employee_id:
			attendance_records = frappe.get_all('Attendance', filters={'employee': employee_id,
				'attendance_date': ['between', [start_date, end_date]]},
				fields=['custom_total_amount', 'overtime_amount'])

			total_custom_amount = sum(record.get('custom_total_amount', 0) for record in attendance_records)
			total_overtime_amount = sum(record.get('overtime_amount', 0) for record in attendance_records)
			employee_totals[employee_id] = {
				'custom_total_amount': total_custom_amount,
				'overtime_amount': total_overtime_amount
			}
	return {'employee_totals': employee_totals}

@frappe.whitelist()
def get_bank_entry_against_payroll(doc_id):
	bank_entry_jv = frappe.db.sql("""
		SELECT jv.name 
		FROM `tabJournal Entry` jv 
		JOIN `tabJournal Entry Account` acc ON jv.name = acc.parent 
		WHERE jv.voucher_type = 'Bank Entry' 
		AND acc.reference_type = 'Payroll Entry'
		AND acc.reference_name = %s
	""", (doc_id), as_dict=True)

	check_entry_jv = frappe.db.sql("""
		SELECT jv.name 
		FROM `tabJournal Entry` jv 
		JOIN `tabJournal Entry Account` acc ON jv.name = acc.parent 
		WHERE jv.voucher_type = 'Bank Entry' 
		AND jv.custom_check_entry = 1
		AND acc.reference_type = 'Payroll Entry'
		AND acc.reference_name = %s
	""", (doc_id), as_dict=True)

	return {"bank_entry_jv":bank_entry_jv, "check_entry_jv" : check_entry_jv}


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company":company}


@frappe.whitelist()
def render_html_for_holiday(start_date, end_date):
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	holiday_list = frappe.db.get_value("Company", frappe.defaults.get_global_default("company"), "default_holiday_list")
	if not holiday_list:
		return {"status": "error", "message": "No holiday list found for the company."}

	holidays = frappe.db.sql("""
		SELECT holiday_date, description FROM `tabHoliday`
		WHERE parent=%s AND holiday_date >= %s AND holiday_date <= %s
		ORDER BY holiday_date ASC
	""", (holiday_list, start_date, end_date), as_dict=True)

	# **Filter out Saturdays and Sundays**
	filtered_holidays = [
		holiday for holiday in holidays if holiday.holiday_date.weekday() not in (5, 6)  # 5 = Saturday, 6 = Sunday
	]

	if filtered_holidays:
		return {"status": "success", "holidays": filtered_holidays}
	else:
		return {"status": "success", "message": "No holidays found in the given date range excluding weekends."}


@frappe.whitelist()
def get_submitted_check_stubs(doc_id):
	all_ss = frappe.db.get_all("Salary Slip", filters={"payroll_entry": doc_id, "docstatus": 1}, fields=["name"])
	
	submitted_entries = []
	for slip in all_ss:		
		try:
			ss_doc = frappe.get_doc("Salary Slip", slip.get("name"))
			submitted_entries.append(slip.get("name"))

		except Exception as e:
			print(e, "e get_submitted_check_stubs")
			
	return {"submitted_entries": submitted_entries}


@frappe.whitelist()
def get_employees_with_bank_payment(doc_id):
	employees = frappe.get_all(
		"Payroll Employee Detail",
		filters={"parent": doc_id},
		fields=["employee"]
	)

	bank_employees = []
	for emp in employees:
		employee_doc = frappe.get_doc("Employee", emp["employee"])
		if employee_doc.custom_payment_method == "Bank":
			bank_employees.append(employee_doc.name)

	return bank_employees

@frappe.whitelist()
def get_salary_to_print(doc_id):
	salary_slip_list = frappe.db.sql("""
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
	""", (doc_id,), as_dict=True)  # Added a comma after doc_id for a single parameter tuple
	
	return [salary_slip.get("name") for salary_slip in salary_slip_list]

@frappe.whitelist()
def get_salary_to_print_for_bank(doc_id):
	salary_slip_list = frappe.db.sql("""
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
	""", (doc_id,), as_dict=True)  # Added a comma after doc_id for a single parameter tuple
	
	return [salary_slip.get("name") for salary_slip in salary_slip_list]

@frappe.whitelist()
def get_check_stubs_for_void_condition(filters):
	filters = json.loads(filters)

	all_slips = frappe.db.get_all("Salary Slip", {"payroll_entry": filters.get("payroll_entry"),"docstatus": ["in", [1]],},
								["name", "custom_check_no"])
	
	valid_slips = [[slip.get("name"), slip.get("custom_check_no")] for slip in all_slips if slip.get("custom_check_no")]
	return valid_slips if valid_slips else []


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_check_to_void(doctype, txt, searchfield, start, page_len, filters):
	all_slips = frappe.db.get_all(
		"Salary Slip",
		{
			"payroll_entry": filters.get("payroll_entry"),
			"docstatus": ["in", [0, 1]],
		},
		["name", "custom_check_no", "employee_name"]
	)

	entries = frappe.db.sql("""
		SELECT name, custom_check_no, employee_name
		FROM `tabSalary Slip`
		WHERE docstatus = 1
		  AND payroll_entry = %(pe)s
		  AND (custom_check_no IS NOT NULL)
		  AND (
				name LIKE %(txt)s
				OR custom_check_no LIKE %(txt)s
			)
		  {not_in_clause}
		ORDER BY name
		LIMIT %(start)s, %(page_len)s
	""".format(
		not_in_clause = f"AND name NOT IN %(all_slips)s" if all_slips else ""
	), {
		"pe": filters.get("payroll_entry"),
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len,
		"all_slips": tuple(all_slips) if all_slips else (),
	})

	return entries

@frappe.whitelist()
def assign_new_check_no(source_name, payroll_entry, new_check_required=None, reason=None, target_doc=None):
    new_check_required = int(new_check_required) if isinstance(new_check_required, str) else False
    payroll_entry_doc = frappe.get_doc("Payroll Entry", payroll_entry)

    if new_check_required:
        frappe.db.set_value("Payroll Entry", payroll_entry_doc, 'custom_new_check_required', True)
        frappe.db.commit()

    all_checks = frappe.get_all(
        "Check",
        filters={"status": "Available"},
        fields=["name", "check_number", "status"],
        order_by="name"
    )

    # If no new check required, just void the existing one
    if not new_check_required:
        cheque_no = frappe.db.get_value("Salary Slip", {"name": source_name}, "custom_check_no")
        frappe.db.set_value("Check", cheque_no, "status", "Void/Cancelled")
        return {'check_voided': True}

    if not all_checks and new_check_required:
        frappe.throw("No check available.")

    # Pick the first available check
    new_check_no = all_checks[0].get('name')

    # Get the old check number from the slip
    old_check_no = frappe.db.get_value("Salary Slip", {"name": source_name}, "custom_check_no")

    # Void the old check
    if old_check_no:
        frappe.db.set_value("Check", old_check_no, "status", "Void/Cancelled")
        frappe.db.set_value("Check", old_check_no, "reference", source_name)
        frappe.db.set_value("Check", old_check_no, "reason_for_cancellation", reason)

    # Assign new check to the existing slip
    frappe.db.set_value("Salary Slip", source_name, "custom_check_no", new_check_no)

    from frappe.utils import get_url

    site_url = get_url()
    check_url = f"{site_url}/app/check/{old_check_no}"

    reason_of_new_check_no = f"New check {new_check_no} assigned, old check <a href= '{check_url}'><b>{old_check_no}</b></a> voided."

    emp_name = frappe.db.get_value("Salary Slip", {"name": source_name}, "employee_name")
    # Mark the new check as issued
    frappe.db.set_value("Check", new_check_no, "status", "Issued")
    frappe.db.set_value("Check", new_check_no, "reference", source_name)
    frappe.db.set_value("Check", new_check_no, "reason", reason_of_new_check_no)

    frappe.db.commit()
    return {"updated_slip": source_name, "new_check_no": new_check_no, "emp_name": emp_name}

@frappe.whitelist()
def get_department_working_hours(employee):
	"""
	Fetch the custom working hours for the employee's department.
	Returns 0 if the department name is not set for the employee
	or if the working hours are 0.
	"""
	if not employee:
		return {"error": "Employee is required"}

	employee_doc = frappe.get_doc("Employee", employee)
	department_name = getattr(employee_doc, 'department', None)
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
		return {"error": f"Unexpected error: {str(e)}"}

@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date=None, company=None):
    """Returns dict of start and end dates for given payroll frequency based on start_date"""

    if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
        fiscal_year = get_fiscal_year(start_date, company=company)[0]
        month = "%02d" % getdate(start_date).month
        m = get_month_details(fiscal_year, month)
        if payroll_frequency == "Bimonthly":
            if getdate(start_date).day <= 15:
                start_date = m["month_start_date"]
                end_date = m["month_mid_end_date"]
            else:
                start_date = m["month_mid_start_date"]
                end_date = m["month_end_date"]
        else:
            start_date = m["month_start_date"]
            end_date = m["month_end_date"]

    if payroll_frequency == "Weekly":
        end_date = add_days(start_date, 6)
        
    if payroll_frequency == "Bi-Weekly":
        end_date = add_days(start_date, 13)
    
        
    if payroll_frequency == "Fortnightly":
        end_date = add_days(start_date, 13)

    if payroll_frequency == "Daily":
        end_date = start_date

    return frappe._dict({"start_date": start_date, "end_date": end_date})



@frappe.whitelist()
def get_end_date(start_date, frequency):
	start_date = getdate(start_date)
	frequency = frequency.lower() if frequency else "monthly"
	kwargs = get_frequency_kwargs(frequency) if frequency != "bimonthly" else get_frequency_kwargs("monthly")

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency != "bimonthly":
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date="")

def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		"monthly": {"months": 1},
		"fortnightly": {"days": 14},
		"weekly": {"days": 7},
		"daily": {"days": 1},
        "bi-weekly": {"days": 14},
	}
	return frequency_dict.get(frequency_name)
	