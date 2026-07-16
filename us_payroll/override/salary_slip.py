import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url
from hrms.payroll.doctype.salary_slip.salary_slip import _safe_eval
from hrms.payroll.utils import sanitize_expression


class SalarySlipMixin(Document):
	def validate(self):
		super().validate()

		self.set_check_no()
		self.set_standard_deduction()
		self.salary_calculations_for_fit()
		self.set_do_not_include_in_accounts()

	def on_cancel(self):
		super().on_cancel()

		if self.custom_check_no:
			check_doc = frappe.get_doc("Check", self.custom_check_no)
			check_doc.status = "Void/Cancelled"
			check_doc.reference = self.name
			check_doc.save()

	def eval_condition_and_formula(self, struct_row, data):
		formula = sanitize_expression(struct_row.formula)

		if struct_row.amount_based_on_formula and formula and formula.startswith("custom_formula"):
			condition = sanitize_expression(struct_row.condition)

			if condition and not _safe_eval(
				condition,
				self.whitelisted_globals,
				data,
			):
				return None

			sal_assignment_name = frappe.db.get_value(
				"Salary Structure Assignment",
				{
					"employee": self.employee,
					"salary_structure": self.salary_structure,
					"docstatus": 1,
				},
				"name",
			)

			if not sal_assignment_name:
				return 0.0

			sal_assignment_doc = frappe.get_doc(
				"Salary Structure Assignment",
				sal_assignment_name,
			)

			for row in sal_assignment_doc.custom_employee_insurance_deduction:
				if row.salary_component == struct_row.salary_component:
					return flt(row.amount)

			for row in sal_assignment_doc.custom_employee_earnings:
				if row.earning_component == struct_row.salary_component:
					return flt(row.amount)

			return 0.0

		return super().eval_condition_and_formula(struct_row, data)

	def compute_year_to_date(self):
		super().compute_year_to_date()

		period_start_date, period_end_date = self.get_year_to_date_period()

		deduction_sum = frappe.get_list(
			"Salary Slip",
			fields=[{"SUM": "total_deduction", "as": "total_deduction_sum"}],
			filters={
				"employee": self.employee,
				"start_date": [">=", period_start_date],
				"end_date": ["<", period_end_date],
				"name": ["!=", self.name],
				"docstatus": 1,
			},
		)

		total_deduction_sum = (
			flt(deduction_sum[0].total_deduction_sum)
			if deduction_sum and deduction_sum[0].total_deduction_sum
			else 0.0
		)

		self.custom_deduction_year_to_date = total_deduction_sum + flt(self.total_deduction)

	def set_check_no(self):
		doc = self
		# Step 1: Get previous value of custom_check_no
		previous_doc = (
			frappe.get_doc(doc.doctype, doc.name) if frappe.db.exists(doc.doctype, doc.name) else None
		)

		# Step 2: If previous check exists and is different from current check, reset status to "Available"
		if (
			previous_doc
			and previous_doc.custom_check_no
			and previous_doc.custom_check_no != doc.custom_check_no
		):
			check_doc = frappe.get_doc("Check", previous_doc.custom_check_no)
			if check_doc.status != "Available":
				check_doc.status = "Available"
				check_doc.reference = None
				check_doc.save()

		# Step 3: If new check is set, mark it as "Issued"
		if doc.custom_check_no:
			check_doc = frappe.get_doc("Check", doc.custom_check_no)
			if check_doc.status != "Issued":
				check_doc.status = "Issued"
				check_doc.reference = doc.name  # Set reference to the Salary Slip name
				check_doc.save()

		# Step 4: If no check is set, payroll_entry exists, and employee wants payment by check → Assign available check
		if not doc.custom_check_no and doc.payroll_entry:
			employee_payment_method = frappe.db.get_value("Employee", doc.employee, "custom_payment_method")

			if employee_payment_method == "Check":
				latest_check = frappe.get_all(
					"Check",
					filters={"status": "Available"},
					fields=["name", "check_number"],
					order_by="check_number ASC",
					limit_page_length=1,
				)
				if latest_check:
					latest_check_name = latest_check[0].get("name")

					# Assign latest available check
					doc.custom_check_no = latest_check_name

					# Update the check status and reference
					check_doc = frappe.get_doc("Check", latest_check_name)
					check_doc.status = "Issued"
					check_doc.reference = doc.name
					check_doc.save()

	def salary_calculations_for_fit(self):
		doc = self
		settings_doc = frappe.get_doc("Client Setup", "Client Setup")
		total_weeks_of_the_year = settings_doc.total_weeks_of_the_year

		# --- 1. Non-taxable earnings (from Earnings table) ---
		total_non_taxable_earnings = 0
		for row in doc.earnings:
			if not row.is_tax_applicable:
				total_non_taxable_earnings += flt(row.amount)

		doc.custom_total_non_taxable_earnings = total_non_taxable_earnings

		# --- 2. Pre-tax deductions (from Deductions table) ---
		total_pretax = 0
		total_fica = 0
		for row in doc.deductions:
			if row.salary_component:
				# For insurance components
				flags = self.get_insurance_flags_from_assignment(doc.employee, row.salary_component)
				if flags.get("is_pretax") and not flags.get("do_not_include"):
					total_pretax += flt(row.amount)

				# For tax components
				comp_doc = frappe.get_doc("Salary Component", row.salary_component)
				if (
					comp_doc.custom_is_this_pretax_component
					and not comp_doc.custom_is_this_insurance_component
					and not comp_doc.get("do_not_include_in_total")
				):
					total_pretax += flt(row.amount)

				if comp_doc.custom_is_this_fica_component:
					total_fica += flt(row.amount)

		doc.custom_total_pretax = total_pretax
		doc.custom_total_fica_deductions = total_fica

		# --- 3. Apply formulas ---
		non_taxable_deductions = total_pretax + total_non_taxable_earnings
		taxable_wages = flt(doc.gross_pay) - non_taxable_deductions

		if total_weeks_of_the_year:
			annualized_wages = taxable_wages * total_weeks_of_the_year
		else:
			site_url = get_url()
			client_settings_url = f"{site_url}/desk/client-setup"
			frappe.throw(
				_(
					"Please add <b>Total weeks of the year</b> in Client Setup. "
					"<a href='{0}'>Client Setup</a>"
				).format(client_settings_url)
			)

		doc.custom_annualized_wages = annualized_wages
		adjusted_annual_wages = flt(doc.custom_annualized_wages) - flt(doc.custom_standard_deduction)

		doc.custom_non_taxable_deductions = non_taxable_deductions
		doc.custom_taxable_wages = taxable_wages
		doc.custom_adjusted_annual_wages = adjusted_annual_wages
		# doc.custom_ss_taxable_wages = taxable_wages + (doc.gross_pay * 0.06)
		# doc.custom_mc_taxable_wages = taxable_wages + (doc.gross_pay * 0.06)
		doc.custom_ss_taxable_wages = doc.custom_taxable_wages + doc.custom_total_fica_deductions
		doc.custom_mc_taxable_wages = doc.custom_taxable_wages + doc.custom_total_fica_deductions

	def get_insurance_flags_from_assignment(self, employee, salary_component):
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

	def set_standard_deduction(self):
		doc = self
		sal_assignment_name = frappe.get_value(
			"Salary Structure Assignment", {"employee": doc.employee, "docstatus": 1}, "name"
		)
		if not sal_assignment_name:
			frappe.throw(
				_("No active Salary Structure Assignment found for employee {0}.").format(doc.employee)
			)

		sal_assignment_doc = frappe.get_doc("Salary Structure Assignment", sal_assignment_name)
		income_tax_slab = sal_assignment_doc.income_tax_slab

		if not income_tax_slab:
			frappe.throw(
				_(
					"Please set an Income Tax Slab in the active Salary Structure "
					"Assignment for employee {0}."
				).format(self.employee)
			)

		it_slab_doc = frappe.get_doc("Income Tax Slab", income_tax_slab)
		it_filing_jointly = it_slab_doc.custom_married_filing_jointly
		if not it_filing_jointly:
			doc.custom_standard_deduction = 8600
		else:
			doc.custom_standard_deduction = 12900

	def set_do_not_include_in_accounts(self):
		doc = self
		sal_structure = doc.salary_structure
		sal_doc = frappe.get_doc("Salary Structure", sal_structure)

		for deduction_row in doc.deductions:
			for sal_row in sal_doc.deductions:
				if deduction_row.salary_component == sal_row.salary_component:
					deduction_row.do_not_include_in_accounts = sal_row.do_not_include_in_accounts
