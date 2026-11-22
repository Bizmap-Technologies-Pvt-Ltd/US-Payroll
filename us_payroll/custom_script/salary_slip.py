import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url
from frappe.utils import flt, getdate


def after_insert(doc, method):
	calculate_leaves_taken(doc)
	set_insurance_component_name(doc)

	if doc.payroll_entry:
		payroll_entry = frappe.get_doc("Payroll Entry", doc.payroll_entry)
		for employee in payroll_entry.employees:
			if employee.employee == doc.employee:
				doc.custom_total_amount = employee.custom_total_amount
				doc.custom_total_overtime_amount = employee.custom_total_overtime_amount
				doc.custom_total_comp_time_amount = employee.custom_total_comp_time_amount
				doc.custom_total_pto_amount = employee.custom_pto_amount
				doc.custom_holiday_amount = employee.custom_holiday_amount
				doc.custom_balance_ct_leaves = employee.custom_available_ct
				doc.custom_balance_pto_leaves = employee.custom_available_pto
				doc.custom_total_accrual_pto = employee.custom_total_accrual_pto
				doc.custom_custom_total_overtime_hours = employee.custom_total_overtime_hours
				doc.custom_custom_overtime_hourly_rate = employee.custom_overtime_hourly_rate
				doc.custom_custom_total_working_hours = employee.custom_total_working_hours
				doc.custom_base_amount = employee.custom_base_amount
	doc.save()
	set_fit_add_flag(doc)
	tax_calulations_for_fit(doc)
	set_do_not_include_in_accounts(doc)


def before_save(doc, method):
	reflect_do_not_include(doc)
	set_insurance_componence_amount_to_zero(doc)


def before_submit(doc, method):
	reflect_do_not_include(doc)
	set_insurance_componence_amount_to_zero(doc)


def set_fit_add_flag(doc):
	for row in doc.deductions:
		if row.salary_component == "FIT" and row.amount == 0:
			doc.custom_fit_added_in_total_deduction = False
			break


def set_insurance_component_name(doc):
	sal_assignment_name = frappe.get_value(
		"Salary Structure Assignment", {"employee": doc.employee, "docstatus": 1}, "name"
	)

	if not sal_assignment_name:
		return {}

	sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
	for deduction_row in doc.deductions:
		for row in sal_assignment_doc.custom_employee_insurance_deduction:
			if (
				row.salary_component == deduction_row.salary_component
				and row.insurance_component  # <-- this is child table field
			):
				if row.tax_type == "Before Tax":
					deduction_row.component_name = f"{row.insurance_company}-{row.salary_component}-BT"

				if row.tax_type == "After Tax":
					deduction_row.component_name = f"{row.insurance_company}-{row.salary_component}-AT"


def get_insurance_flags_from_assignment(employee, salary_component):
	sal_assignment_name = frappe.get_value(
		"Salary Structure Assignment", {"employee": employee, "docstatus": 1}, "name"
	)
	if not sal_assignment_name:
		return {}

	sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
	for row in sal_assignment_doc.custom_employee_insurance_deduction:
		if row.salary_component == salary_component and row.is_this_employees_insurance_component:
			return {
				"is_pretax": row.is_this_pre_tax_component,
				"is_fit": row.is_this_income_tax_slab_component,
				"do_not_include": row.do_not_include_in_total,
			}

	return {}


def set_insurance_componence_amount_to_zero(doc):
	sal_assignment_name = frappe.get_value(
		"Salary Structure Assignment", {"employee": doc.employee, "docstatus": 1}, "name"
	)
	if not sal_assignment_name:
		return

	sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
	for deduction_row in doc.deductions:
		for assign_row in sal_assignment_doc.custom_employee_insurance_deduction:
			if (
				deduction_row.salary_component == assign_row.salary_component
				and assign_row.is_this_employees_insurance_component
				and assign_row.do_not_include_in_total
			):
				deduction_row.amount = 0


def reflect_do_not_include(doc):
	sal_assignment_name = frappe.get_value(
		"Salary Structure Assignment", {"employee": doc.employee, "docstatus": 1}, "name"
	)
	if not sal_assignment_name:
		return

	sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
	for deduction_row in doc.deductions:
		for assign_row in sal_assignment_doc.custom_employee_insurance_deduction:
			if (
				deduction_row.salary_component == assign_row.salary_component
				and assign_row.is_this_employees_insurance_component
			):
				deduction_row.do_not_include_in_total = assign_row.do_not_include_in_total
				deduction_row.do_not_include_in_accounts = assign_row.do_not_include_in_accounts


def set_do_not_include_in_accounts(doc):
	sal_structure = doc.salary_structure
	sal_doc = frappe.get_doc("Salary Structure", sal_structure)

	for deduction_row in doc.deductions:
		for sal_row in sal_doc.deductions:
			if deduction_row.salary_component == sal_row.salary_component:
				deduction_row.do_not_include_in_accounts = sal_row.do_not_include_in_accounts


def calculate_leaves_taken(doc):
	if doc.employee:
		query = """
			SELECT pe.name AS payroll_entry,
				   ped.custom_available_pto,
				   ped.custom_available_ct,
				   ped.custom_comp_time,
				   ped.custom_pto_hours
			FROM `tabPayroll Entry` pe
			INNER JOIN `tabPayroll Employee Detail` ped
				ON ped.parent = pe.name
			WHERE ped.employee = %(employee)s
			  AND pe.docstatus = 1
			  AND pe.status != 'Failed'
			  AND pe.posting_date <= %(start_date)s
		"""

		past_data = frappe.db.sql(
			query,
			{
				"employee": doc.employee,
				"start_date": doc.start_date,
			},
			as_dict=True,
		)
		custom_used_ct_leaves = 0
		custom_used_pto_leaves = 0
		if past_data:
			if len(past_data) > 0:
				custom_used_ct_leaves = sum([_["custom_comp_time"] for _ in past_data])

			if len(past_data) > 0:
				custom_used_pto_leaves = sum([_["custom_pto_hours"] for _ in past_data])

			doc.custom_used_ct_leaves = custom_used_ct_leaves
			doc.custom_used_pto_leaves = custom_used_pto_leaves


def get_ytd(doc, year):
	row = frappe.db.sql(
		"""
		SELECT
			IFNULL(SUM(custom_ss_taxable_wages), 0) AS ss_ytd,
			IFNULL(SUM(custom_mc_taxable_wages), 0) AS mc_ytd
		FROM `tabSalary Slip`
		WHERE employee = %(employee)s
			AND company = %(company)s
			AND docstatus = 1
			AND YEAR(posting_date) = %(year)s
			AND posting_date <= %(posting_date)s
			AND name != %(name)s
		""",
		{
			"employee": doc.employee,
			"company": doc.company,
			"year": year,
			"posting_date": doc.posting_date,
			"name": doc.name or "",
		},
		as_dict=True,
	)[0]

	return flt(row.ss_ytd, 2), flt(row.mc_ytd, 2)


def set_fica_limits(doc, ss_wages=None, mc_wages=None):
	"""
	Calculate Social Security wage limits and
	Additional Medicare taxable wages.

	Call after FICA wages are calculated and
	before FICA tax components are evaluated.
	"""

	setup_doc = frappe.get_single("Client Setup")

	ss_cap = flt(setup_doc.social_security_wage_base)
	mc_threshold = flt(setup_doc.additional_medicare_tax_threshold)

	if ss_cap <= 0:
		frappe.throw(
			"Please configure Social Security Wage Base in Client Setup."
		)

	if mc_threshold <= 0:
		frappe.throw(
			"Please configure Additional Medicare Tax Threshold in Client Setup."
		)

	year = getdate(doc.posting_date).year

	if ss_wages is None or mc_wages is None:
	frappe.throw(
		"Social Security and Medicare wages must be calculated before applying FICA limits."
	)

	# Original FICA wages BEFORE applying the Social Security cap.
	# Pass these values explicitly when calling this function.
	ss_wages = flt(ss_wages, 2)
	mc_wages = flt(mc_wages, 2)

	# Previous YTD wages
	ss_ytd, mc_ytd = get_ytd(doc, year)

	# Social Security taxable wages
	remaining_wage_base = max(0, flt(ss_cap - ss_ytd, 2),)

	ss_taxable = flt(max(0, min(ss_wages, remaining_wage_base)),2,)

	doc.custom_ss_taxable_wages_ytd = ss_ytd
	doc.custom_ss_taxable_wages = ss_taxable

	# Medicare taxable wages (no wage cap)
	doc.custom_mc_taxable_wages = mc_wages
	doc.custom_medicare_taxable_wages_ytd = mc_ytd

	# Additional Medicare taxable wages
	additional_medicare_wages = flt(max(0, min(mc_wages, mc_ytd + mc_wages - mc_threshold,),),2,)
	doc.custom_additional_medicare_wages = additional_medicare_wages

@frappe.whitelist()
def tax_calulations_for_fit(doc: Document):
	settings_doc = frappe.get_doc("Client Setup", "Client Setup")
	total_weeks_of_the_year = settings_doc.total_weeks_of_the_year
	sal_structure = doc.salary_structure
	sal_doc = frappe.get_doc("Salary Structure", sal_structure)

	fit_component = False
	for row in sal_doc.deductions:
		if row.get("salary_component"):
			comp_doc = frappe.get_doc("Salary Component", row.get("salary_component"))
			if comp_doc.get("custom_is_this_fit_component"):
				fit_component = True

	sal_assignment_name = frappe.get_value(
		"Salary Structure Assignment", {"employee": doc.employee, "docstatus": 1}, "name"
	)
	if not sal_assignment_name:
		frappe.throw(f"No active Salary Structure Assignment found for employee {doc.employee}")

	sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
	income_tax_slab = sal_assignment_doc.income_tax_slab
	it_slab_doc = frappe.get_doc("Income Tax Slab", income_tax_slab)

	fit_amount = 0
	if fit_component and it_slab_doc:
		custom_adjusted_annual_wages = doc.custom_adjusted_annual_wages

		fit_amount = 0
		last_to_amount = 0
		for row in it_slab_doc.get("slabs"):
			from_amount = row.get("from_amount")
			to_amount = row.get("to_amount")
			percent_deduction = row.get("percent_deduction") / 100

			if (
				last_to_amount == 0
				and from_amount <= custom_adjusted_annual_wages
				and custom_adjusted_annual_wages <= to_amount
			):
				fit_amount = (custom_adjusted_annual_wages - from_amount) * percent_deduction
				last_to_amount = to_amount
				break

			if from_amount <= custom_adjusted_annual_wages and custom_adjusted_annual_wages >= to_amount:
				fit_amount += (to_amount - from_amount) * percent_deduction
				last_to_amount = to_amount
				continue

			if from_amount <= custom_adjusted_annual_wages and custom_adjusted_annual_wages >= last_to_amount:
				fit_amount += (custom_adjusted_annual_wages - last_to_amount) * percent_deduction
				last_to_amount = to_amount
				continue

	total_credit = frappe.get_value(
		"Employee", {"employee": doc.employee, "status": "Active"}, "custom_total_credit"
	)

	doc.custom_total_of_income_tax = fit_amount - total_credit
	if total_weeks_of_the_year:
		fit = (fit_amount - total_credit) / total_weeks_of_the_year
		if fit >= 0:
			doc.custom_income_tax_of_current_month = fit
		else:
			doc.custom_income_tax_of_current_month = 0

		for row in doc.deductions:
			if row.get("salary_component"):
				comp_doc = frappe.get_doc("Salary Component", row.get("salary_component"))
				if comp_doc.get("custom_is_this_fit_component"):
					fit_component = True

					fit = (fit_amount - total_credit) / total_weeks_of_the_year
					if fit >= 0:
						row.amount = fit

					else:
						row.amount = 0

		if not doc.custom_fit_added_in_total_deduction and fit > 0:
			doc.total_deduction = doc.total_deduction + fit
			doc.net_pay = doc.gross_pay - doc.total_deduction
			doc.custom_fit_added_in_total_deduction = True
	else:
		site_url = get_url()
		client_settings_url = f"{site_url}/desk/client-setup"
		frappe.throw(
			f"Please add <b>Total weeks of the year</b> in Client Setup. <a href= '{client_settings_url}' >Client Setup</a>"
		)
	doc.save()

