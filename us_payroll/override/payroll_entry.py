# # Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# import json
# from dateutil.relativedelta import relativedelta
# import frappe
# from frappe import _
# from frappe.desk.reportview import get_match_cond
# from frappe.model.document import Document
# from frappe.query_builder.functions import Coalesce, Count
# from frappe.utils import (
# 	DATE_FORMAT,
# 	add_days,
# 	add_to_date,
# 	cint,
# 	comma_and,
# 	date_diff,
# 	flt,
# 	get_link_to_form,
# 	getdate,
# )
# import erpnext
# from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
# 	get_accounting_dimensions,
# )
# from erpnext.accounts.utils import get_fiscal_year
# from frappe.utils import get_url
# from collections import defaultdict
# from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry

# class OverridePayrollEntry(PayrollEntry):
# 	def onload(self):
# 		if not self.docstatus == 1 or self.salary_slips_submitted:
# 			return

# 		# check if salary slips were manually submitted
# 		entries = frappe.db.count("Salary Slip", {"payroll_entry": self.name, "docstatus": 1}, ["name"])
# 		if cint(entries) == len(self.employees):
# 			self.set_onload("submitted_ss", True)

# 	def validate(self):
# 		self.number_of_employees = len(self.employees)
# 		self.set_status()

# 	def set_status(self, status=None, update=False):
# 		if not status:
# 			status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

# 		if update:
# 			self.db_set("status", status)
# 		else:
# 			self.status = status

# 	def before_submit(self):
# 		self.validate_existing_salary_slips()
# 		self.validate_payroll_payable_account()
# 		if self.get_employees_with_unmarked_attendance():
# 			frappe.throw(_("Cannot submit. Attendance is not marked for some employees."))

# 	def on_submit(self):
# 		self.set_status(update=True, status="Submitted")
# 		self.create_salary_slips()


# 	def validate_existing_salary_slips(self):
# 		if not self.employees:
# 			return

# 		existing_salary_slips = []
# 		SalarySlip = frappe.qb.DocType("Salary Slip")

# 		existing_salary_slips = (
# 			frappe.qb.from_(SalarySlip)
# 			.select(SalarySlip.employee, SalarySlip.name)
# 			.where(
# 				(SalarySlip.employee.isin([emp.employee for emp in self.employees]))
# 				& (SalarySlip.start_date == self.start_date)
# 				& (SalarySlip.end_date == self.end_date)
# 				& (SalarySlip.docstatus != 2)
# 			)
# 		).run(as_dict=True)

# 		if len(existing_salary_slips):
# 			msg = _("Salary Slip already exists for {0} for the given dates").format(
# 				comma_and([frappe.bold(d.employee) for d in existing_salary_slips])
# 			)
# 			msg += "<br><br>"
# 			msg += _("Reference: {0}").format(
# 				comma_and([get_link_to_form("Salary Slip", d.name) for d in existing_salary_slips])
# 			)
# 			frappe.throw(
# 				msg,
# 				title=_("Duplicate Entry"),
# 			)

	
# 	@frappe.whitelist()
# 	def has_bank_entries(self) -> dict[str, bool]:
# 		je = frappe.qb.DocType("Journal Entry")
# 		jea = frappe.qb.DocType("Journal Entry Account")

# 		bank_entries = (
# 			frappe.qb.from_(je)
# 			.inner_join(jea)
# 			.on(je.name == jea.parent)
# 			.select(je.name)
# 			.where(
# 				(je.voucher_type == "Bank Entry")
# 				& (jea.reference_name == self.name)
# 				& (jea.reference_type == "Payroll Entry")
# 			)
# 		).run(as_dict=True)

# 		return {
# 			"has_bank_entries": bool(bank_entries),
# 			"has_bank_entries_for_withheld_salaries": not any(
# 				employee.is_salary_withheld for employee in self.employees
# 			),
# 		}
		
# 	def validate_payroll_payable_account(self):
# 		if frappe.db.get_value("Account", self.payroll_payable_account, "account_type"):
# 			frappe.throw(
# 				_(
# 					"Account type cannot be set for payroll payable account {0}, please remove and try again"
# 				).format(frappe.bold(get_link_to_form("Account", self.payroll_payable_account)))
# 			)

# 	def on_cancel(self):
# 		self.ignore_linked_doctypes = ("GL Entry", "Salary Slip", "Journal Entry")

# 		self.delete_linked_salary_slips()
# 		self.cancel_linked_journal_entries()

# 		# reset flags & update status
# 		self.db_set("salary_slips_created", 0)
# 		self.db_set("salary_slips_submitted", 0)
# 		self.set_status(update=True, status="Cancelled")
# 		self.db_set("error_message", "")

# 	def cancel(self):
# 		if len(self.get_linked_salary_slips()) > 50:
# 			msg = _("Payroll Entry cancellation is queued. It may take a few minutes")
# 			msg += "<br>"
# 			msg += _(
# 				"In case of any error during this background process, the system will add a comment about the error on this Payroll Entry and revert to the Submitted status"
# 			)
# 			frappe.msgprint(
# 				msg,
# 				indicator="blue",
# 				title=_("Cancellation Queued"),
# 			)
# 			self.queue_action("cancel", timeout=3000)
# 		else:
# 			self._cancel()


# 	def delete_linked_salary_slips(self):
# 		salary_slips = self.get_linked_salary_slips()

# 		# cancel & delete salary slips
# 		for salary_slip in salary_slips:
# 			if salary_slip.docstatus == 1:
# 				frappe.get_doc("Salary Slip", salary_slip.name).cancel()
# 			frappe.delete_doc("Salary Slip", salary_slip.name)

# 	def cancel_linked_journal_entries(self):
# 		journal_entries = frappe.get_all(
# 			"Journal Entry Account",
# 			{"reference_type": self.doctype, "reference_name": self.name, "docstatus": 1},
# 			pluck="parent",
# 			distinct=True,
# 		)

# 		# cancel Journal Entries
# 		for je in journal_entries:
# 			frappe.get_doc("Journal Entry", je).cancel()

# 	def get_linked_salary_slips(self):
# 		return frappe.get_all("Salary Slip", {"payroll_entry": self.name}, ["name", "docstatus"])

# 	def make_filters(self):
# 		filters = frappe._dict(
# 			company=self.company,
# 			branch=self.branch,
# 			department=self.department,
# 			designation=self.designation,
# 			grade=self.grade,
# 			currency=self.currency,
# 			start_date=self.start_date,
# 			end_date=self.end_date,
# 			payroll_payable_account=self.payroll_payable_account,
# 			salary_slip_based_on_timesheet=self.salary_slip_based_on_timesheet,
# 		)

# 		if not self.salary_slip_based_on_timesheet:
# 			filters.update(dict(payroll_frequency=self.payroll_frequency))

# 		return filters

# 	@frappe.whitelist()
# 	def fill_employee_details(self):
# 		filters = self.make_filters()
# 		employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)

# 		# Replace 'payroll_payable_account' with 'custom_payroll_payable_account'
# 		for employee in employees:
# 			employee['custom_payroll_payable_account'] = employee.pop('payroll_payable_account')

# 		self.set("employees", [])

# 		if not employees:
# 			error_msg = _(
# 				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
# 			).format(
# 				frappe.bold(self.company),
# 				frappe.bold(self.currency),
# 				frappe.bold(self.payroll_payable_account),
# 			)
# 			if self.branch:
# 				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
# 			if self.department:
# 				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
# 			if self.designation:
# 				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
# 			if self.start_date:
# 				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
# 			if self.end_date:
# 				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
# 			frappe.throw(error_msg, title=_("No employees found"))

# 		self.set("employees", employees)
# 		self.number_of_employees = len(self.employees)

# 		return self.get_employees_with_unmarked_attendance()


# 	@frappe.whitelist()
# 	def create_salary_slips(self):
# 		"""
# 		Creates salary slip for selected employees if already not created
# 		"""
# 		add_check_employees = []
# 		for row in self.employees:
# 			employee_payment_method = frappe.db.get_value("Employee", row.employee, "custom_payment_method")
# 			if employee_payment_method == "Check":
# 				add_check_employees.append(row.employee)

# 		available_check = frappe.get_all(
# 				"Check",
# 				filters={"status": "Available"},
# 				fields=["name", "check_number"],
# 				order_by="check_number ASC",
# 			)
# 			# if not available_check:
#    #              frappe.throw("No check available.")

# 		available_check = available_check[::-1]

# 		if len(available_check) < len(add_check_employees):
# 			frappe.throw("Number of available checks are less than the required.")

# 		else:
# 			self.check_permission("write")
# 			employees = [emp.employee for emp in self.employees]

# 			if employees:
# 				args = frappe._dict(
# 					{
# 						"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
# 						"payroll_frequency": self.payroll_frequency,
# 						"start_date": self.start_date,
# 						"end_date": self.end_date,
# 						"company": self.company,
# 						"posting_date": self.posting_date,
# 						"deduct_tax_for_unclaimed_employee_benefits": 0,
# 						"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
# 						"payroll_entry": self.name,
# 						"exchange_rate": self.exchange_rate,
# 						"currency": self.currency,
# 					}
# 				)
# 				if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
# 					self.db_set("status", "Queued")
# 					frappe.enqueue(
# 						create_salary_slips_for_employees,
# 						timeout=3000,
# 						employees=employees,
# 						args=args,
# 						publish_progress=False,
# 					)
# 					frappe.msgprint(
# 						_("Salary Slip creation is queued. It may take a few minutes"),
# 						alert=True,
# 						indicator="blue",
# 					)
# 				else:
# 					create_salary_slips_for_employees(employees, args, publish_progress=False)
# 					# since this method is called via frm.call this doc needs to be updated manually
# 					self.reload()


# 	def get_sal_slip_list(self, ss_status, as_dict=False):
# 		"""
# 		Returns list of salary slips based on selected criteria
# 		"""

# 		ss = frappe.qb.DocType("Salary Slip")
# 		ss_list = (
# 			frappe.qb.from_(ss)
# 			.select(ss.name, ss.salary_structure)
# 			.where(
# 				(ss.docstatus == ss_status)
# 				& (ss.start_date >= self.start_date)
# 				& (ss.end_date <= self.end_date)
# 				& (ss.payroll_entry == self.name)
# 				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
# 				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
# 			)
# 		).run(as_dict=as_dict)

# 		return ss_list

# 	@frappe.whitelist()
# 	def submit_salary_slips(self):
# 		self.check_permission("write")
# 		salary_slips = self.get_sal_slip_list(ss_status=0)

# 		if len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry:
# 			self.db_set("status", "Queued")
# 			frappe.enqueue(
# 				submit_salary_slips_for_employees,
# 				timeout=3000,
# 				payroll_entry=self,
# 				salary_slips=salary_slips,
# 				publish_progress=False,
# 			)
# 			frappe.msgprint(
# 				_("Salary Slip submission is queued. It may take a few minutes"),
# 				alert=True,
# 				indicator="blue",
# 			)
# 		else:
# 			submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

# 	def email_salary_slip(self, submitted_ss):
# 		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
# 			for ss in submitted_ss:
# 				ss.email_salary_slip()


# # # # ----------------------below is working in case of expense and  2 liability accounts-----------------
# # 	def get_salary_component_accounts(self, salary_component, fund, department=None):
# # 		print(salary_component, fund, department, "salary_component, fund, department =======")
# # 		comp_doc = frappe.get_doc("Salary Component", salary_component)
# # 		filters = {"parent": salary_component, "custom_fund": fund}  # default

# # 		if comp_doc.type == "Earning":
# # 			# Check for department match
# # 			for row in comp_doc.accounts:
# # 				acc_doc = frappe.get_doc("Account", row.get("account"))
# # 				dept = acc_doc.custom_department_number

# # 				if department and department == dept:
# # 					filters = {
# # 						"parent": salary_component,
# # 						"custom_fund": fund,
# # 						"custom_department_name": department,
# # 					}
# # 					break  # stop at first department match

# # 			account = None

# # 			if department:
# # 				# Use existing logic if department is provided
# # 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
			
# # 			else:
# # 				# Fund-only case: pick first matching row from the child table
# # 				for row in comp_doc.accounts:
# # 					if row.get("custom_fund") == fund:
# # 						account = row.get("account")
# # 						break

# # 		if comp_doc.type == "Deduction":
# # 			# Check for department match
# # 			for row in comp_doc.accounts:
# # 				acc_doc = frappe.get_doc("Account", row.get("account"))
# # 				dept = acc_doc.custom_department_number

# # 				if department and department == dept:
# # 					filters = {
# # 						"parent": salary_component,
# # 						"custom_fund": fund,
# # 						"custom_department_name": department,
# # 					}
# # 					print(filters, "department match")
# # 					break  # stop at first department match

# # 			account = None

# # 			if department:
# # 				# Use existing logic if department is provided
# # 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
			
# # 			if fund:
# # 				# Fund-only case: pick first matching row from the child table
# # 				for row in comp_doc.accounts:
# # 					if row.get("custom_fund") == fund:
# # 						account = row.get("account")
# # 						break
# # 		if not account:
# # 			frappe.throw(
# # 				_("Please set account in Salary Component {0}").format(
# # 					get_link_to_form("Salary Component", salary_component)
# # 				)
# # 			)


# # 		print(account, "account =======")

# # 		return account


# # # ----------------------below is working in case of expense and liability----------------
# # 	def get_salary_component_account(self, salary_component, fund, department=None):
# # 		print(salary_component, fund, department, "salary_component, fund, department 222222222=======")
# # 		comp_doc = frappe.get_doc("Salary Component", salary_component)
# # 		filters = {"parent": salary_component, "custom_fund": fund}
# # 		account = None

# # 		if comp_doc.type in ["Earning", "Deduction"]:
# # 			for row in comp_doc.accounts:
# # 				acc_doc = frappe.get_doc("Account", row.get("account"))
# # 				dept = acc_doc.custom_department_number

# # 				if department and department == dept:
# # 					filters = {
# # 						"parent": salary_component,
# # 						"custom_fund": fund,
# # 						"custom_department_name": department,
# # 					}
# # 					break

# # 			if department:
# # 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
# # 			else:
# # 				for row in comp_doc.accounts:
# # 					if row.get("custom_fund") == fund:
# # 						account = row.get("account")
# # 						break

# # 			if comp_doc.type == "Deduction" and comp_doc.do_not_include_in_total and comp_doc.custom_is_employer_component:
# # 				fund_account = None
# # 				dept_account = None
# # 				for row in comp_doc.accounts:
# # 					acc_doc = frappe.get_doc("Account", row.get("account"))
# # 					dept = acc_doc.custom_department_number

# # 					if acc_doc.root_type == "Liability" and row.get("custom_fund") == fund:
# # 						fund_account = row.get("account")

# # 					elif acc_doc.root_type == "Expense" and department == dept:
# # 						dept_account = row.get("account")

# # 				if not fund_account:
# # 					frappe.throw(_("Please set Liability account in Salary Component {0}").format(
# # 						get_link_to_form("Salary Component", salary_component)
# # 					))

# # 				if not dept_account:
# # 					frappe.throw(_("Please set Expense account in Salary Component {0}").format(
# # 						get_link_to_form("Salary Component", salary_component)
# # 					))

# # 				return {"fund_account": fund_account, "dept_account": dept_account}
# # 		if not account:
# # 			frappe.throw(_("Please set account in Salary Component {0}").format(
# # 				get_link_to_form("Salary Component", salary_component)
# # 			))

# # 		print(account, "account22222222222222 =======")

# # 		return account


# 	def get_insurance_details_from_ssa(self, employee, salary_component):
# 		ssa = frappe.db.get_value(
# 			"Salary Structure Assignment",
# 			{
# 				"employee": employee,
# 				"docstatus": 1
# 			},
# 			"name"
# 		)

# 		if not ssa:
# 			return None, None   # ✅ ALWAYS return tuple

# 		print(employee,ssa,salary_component,"employee,ssa,salary_component 0000000000000" )

# 		result = frappe.db.get_value(
# 			"Employee Insurance Deduction",
# 			{
# 				"parent": ssa,
# 				"salary_component": salary_component
# 			},
# 			["insurance_company", "category"]
# 		)

# 		if not result:
# 			return None, None   # ✅ ALWAYS return tuple

# 		print(result,"resultsssssssssssssssssssssssssssssssssssssssssssssssss" )

# 		return result


# 	# def get_insurance_provider_account(
# 	# 	self,
# 	# 	provider,
# 	# 	salary_component,
# 	# 	fund,
# 	# 	department=None
# 	# ):
# 	# 	provider_doc = frappe.get_cached_doc("Insurance Provider", provider)
# 	# 	comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 	# 	for row in provider_doc.accounts:
# 	# 		if row.custom_fund != fund:
# 	# 			continue

# 	# 		acc_doc = frappe.get_cached_doc("Account", row.account)
# 	# 		dept = acc_doc.custom_department_number

# 	# 		# 🔹 Employee Insurance → Liability
# 	# 		if comp_doc.custom_is_this_insurance_component:
# 	# 			if acc_doc.root_type == "Liability":
# 	# 				return row.account

# 	# 		# 🔹 Employer Insurance → Expense
# 	# 		if comp_doc.custom_is_this_employers_insurance_component:
# 	# 			if acc_doc.root_type == "Expense":
# 	# 				if department and department == dept:
# 	# 					return row.account

# 	# 	frappe.throw(
# 	# 		_("Please set proper Insurance account in Insurance Provider {0}")
# 	# 		.format(provider)
# 	# 	)

# 	def get_insurance_provider_account(
# 		self,
# 		provider,
# 		salary_component,
# 		fund,
# 		department=None
# 	):
# 		provider_doc = frappe.get_cached_doc("Insurance Provider", provider)
# 		comp_doc = frappe.get_cached_doc("Salary Component", salary_component)
# 		filters = {"parent": salary_component, "custom_fund": fund}
# 		for row in provider_doc.accounts:
# 			if row.custom_fund != fund:
# 				continue

# 			acc_doc = frappe.get_cached_doc("Account", row.account)
# 			dept = acc_doc.custom_department_number

# 			if department and department == dept:
# 				filters = {
# 					"parent": "Insurance Provider",
# 					"custom_fund": fund,
# 					"custom_department_name": department,
# 				}
# 				print(filters, "department match")
# 				break  # stop at first department match

# 		account = None

# 		if department:
# 			# Use existing logic if department is provided
# 			account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
		
# 		if fund:
# 			# Fund-only case: pick first matching row from the child table
# 			for row in provider_doc.accounts:
# 				if row.get("custom_fund") == fund:
# 					account = row.get("account")
# 					break

# 		if not account:		
# 			frappe.throw(
# 				_("Please set proper Insurance account in Insurance Provider {0}")
# 				.format(provider)
# 			)

# 		return account



# 	def get_er_insurance_account(
# 		self,
# 		provider,
# 		salary_component,
# 		fund,
# 		department=None
# 	):
# 		provider_doc = frappe.get_cached_doc("Insurance Provider", provider)
# 		comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 		if comp_doc.do_not_include_in_total and comp_doc.custom_is_employer_component:
# 			fund_account = None
# 			dept_account = None
# 			for row in provider_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.get("account"))
# 				dept = acc_doc.custom_department_number

# 				if acc_doc.root_type == "Liability" and row.get("custom_fund") == fund:
# 					fund_account = row.get("account")

# 				elif acc_doc.root_type == "Expense" and department == dept:
# 					dept_account = row.get("account")

# 			if not fund_account:
# 				frappe.throw(_("Please set Liability account in Insurance Provider {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				))

# 			if not dept_account:
# 				frappe.throw(_("Please set Expense account in Insurance Provider {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				))

# 			return {"fund_account": fund_account, "dept_account": dept_account}



# 	# # ----------------------below is working in case of expense and  2 liability accounts-----------------
# 	def get_salary_component_accounts(self, salary_component, fund, department=None, employee=None):
# 		print(salary_component, fund, employee, department, "salary_component, fund, employee=None, department=None /////////////////")
# 		comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 		# 🔹 INSURANCE OVERRIDE (Employee or Employer)
# 		if comp_doc.type == "Deduction" and (
# 			comp_doc.custom_is_this_insurance_component
# 			or comp_doc.custom_is_this_employers_insurance_component
# 		):
# 			provider, category = self.get_insurance_details_from_ssa(
# 				employee, salary_component
# 			)

# 			print(provider, category, "provider, category ==============")

# 			if provider:
# 				return self.get_insurance_provider_account(
# 					provider, salary_component, fund, department
# 				)

# 		# 🔹 EXISTING LOGIC (UNCHANGED)
# 		filters = {"parent": salary_component, "custom_fund": fund}  # default

# 		if comp_doc.type == "Earning":
# 			# Check for department match
# 			for row in comp_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.get("account"))
# 				dept = acc_doc.custom_department_number

# 				if department and department == dept:
# 					filters = {
# 						"parent": salary_component,
# 						"custom_fund": fund,
# 						"custom_department_name": department,
# 					}
# 					break  # stop at first department match

# 			account = None

# 			if department:
# 				# Use existing logic if department is provided
# 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
			
# 			else:
# 				# Fund-only case: pick first matching row from the child table
# 				for row in comp_doc.accounts:
# 					if row.get("custom_fund") == fund:
# 						account = row.get("account")
# 						break

# 		if comp_doc.type == "Deduction":
# 			# Check for department match
# 			for row in comp_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.get("account"))
# 				dept = acc_doc.custom_department_number

# 				if department and department == dept:
# 					filters = {
# 						"parent": salary_component,
# 						"custom_fund": fund,
# 						"custom_department_name": department,
# 					}
# 					print(filters, "department match")
# 					break  # stop at first department match

# 			account = None

# 			if department:
# 				# Use existing logic if department is provided
# 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
			
# 			if fund:
# 				# Fund-only case: pick first matching row from the child table
# 				for row in comp_doc.accounts:
# 					if row.get("custom_fund") == fund:
# 						account = row.get("account")
# 						break
# 		if not account:
# 			frappe.throw(
# 				_("Please set account in Salary Component {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				)
# 			)


# 		print(account, "account =======")

# 		return account


# # ----------------------below is working in case of expense and liability----------------
# 	def get_salary_component_account(self, salary_component, fund, department=None, employee=None):
# 		print(salary_component, fund, employee, department, "salary_component, fund, employee=None, department=None /////////////////")
# 		comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 		# 🔹 INSURANCE OVERRIDE (Employee or Employer)
# 		if comp_doc.type == "Deduction" and (
# 			comp_doc.custom_is_this_insurance_component
# 			or comp_doc.custom_is_this_employers_insurance_component
# 		):
# 			provider, category = self.get_insurance_details_from_ssa(
# 				employee, salary_component
# 			)

# 			print(provider, category, "provider, category ==============")

# 			if provider:
# 				return self.get_er_insurance_account(
# 					provider, salary_component, fund, department
# 				)

# 		# 🔹 EXISTING LOGIC (UNCHANGED)
# 		filters = {"parent": salary_component, "custom_fund": fund}
# 		account = None

# 		if comp_doc.type in ["Earning", "Deduction"]:
# 			for row in comp_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.get("account"))
# 				dept = acc_doc.custom_department_number

# 				if department and department == dept:
# 					filters = {
# 						"parent": salary_component,
# 						"custom_fund": fund,
# 						"custom_department_name": department,
# 					}
# 					break

# 			if department:
# 				account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
# 			else:
# 				for row in comp_doc.accounts:
# 					if row.get("custom_fund") == fund:
# 						account = row.get("account")
# 						break

# 			if comp_doc.type == "Deduction" and comp_doc.do_not_include_in_total and comp_doc.custom_is_employer_component:
# 				fund_account = None
# 				dept_account = None
# 				for row in comp_doc.accounts:
# 					acc_doc = frappe.get_doc("Account", row.get("account"))
# 					dept = acc_doc.custom_department_number

# 					if acc_doc.root_type == "Liability" and row.get("custom_fund") == fund:
# 						fund_account = row.get("account")

# 					elif acc_doc.root_type == "Expense" and department == dept:
# 						dept_account = row.get("account")

# 				if not fund_account:
# 					frappe.throw(_("Please set Liability account in Salary Component {0}").format(
# 						get_link_to_form("Salary Component", salary_component)
# 					))

# 				if not dept_account:
# 					frappe.throw(_("Please set Expense account in Salary Component {0}").format(
# 						get_link_to_form("Salary Component", salary_component)
# 					))

# 				return {"fund_account": fund_account, "dept_account": dept_account}
# 		if not account:
# 			frappe.throw(_("Please set account in Salary Component {0}").format(
# 				get_link_to_form("Salary Component", salary_component)
# 			))

# 		print(account, "account22222222222222 =======")

# 		return account


# 	# def get_salary_component_account(self, salary_component, fund, department=None, employee=None):
# 	# 	print(salary_component, fund, employee, department, "salary_component, fund, employee=None, department=None /////////////////")
# 	# 	comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 	# 	# 🔹 INSURANCE OVERRIDE (Employee or Employer)
# 	# 	if comp_doc.type == "Deduction" and (
# 	# 		comp_doc.custom_is_this_insurance_component
# 	# 		or comp_doc.custom_is_this_employers_insurance_component
# 	# 	):
# 	# 		provider, category = self.get_insurance_details_from_ssa(
# 	# 			employee, salary_component
# 	# 		)

# 	# 		print(provider, category, "provider, category ==============")

# 	# 		if provider:
# 	# 			return self.get_insurance_provider_account(
# 	# 				provider, salary_component, fund, department
# 	# 			)

# 	# 	# 🔹 EXISTING LOGIC (UNCHANGED)
# 	# 	filters = {"parent": salary_component, "custom_fund": fund}
# 	# 	account = None

# 	# 	if comp_doc.type in ["Earning", "Deduction"]:
# 	# 		for row in comp_doc.accounts:
# 	# 			acc_doc = frappe.get_cached_doc("Account", row.get("account"))
# 	# 			dept = acc_doc.custom_department_number

# 	# 			if department and department == dept:
# 	# 				filters = {
# 	# 					"parent": salary_component,
# 	# 					"custom_fund": fund,
# 	# 					"custom_department_name": department,
# 	# 				}
# 	# 				break

# 	# 		if department:
# 	# 			account = frappe.db.get_value(
# 	# 				"Salary Component Account", filters, "account", cache=True
# 	# 			)
# 	# 		else:
# 	# 			for row in comp_doc.accounts:
# 	# 				if row.get("custom_fund") == fund:
# 	# 					account = row.get("account")
# 	# 					break

# 	# 		# Employer contribution (ER Expense + Liability)
# 	# 		if (
# 	# 			comp_doc.type == "Deduction"
# 	# 			and comp_doc.do_not_include_in_total
# 	# 			and comp_doc.custom_is_employer_component
# 	# 		):
# 	# 			fund_account = None
# 	# 			dept_account = None

# 	# 			for row in comp_doc.accounts:
# 	# 				acc_doc = frappe.get_cached_doc("Account", row.get("account"))
# 	# 				dept = acc_doc.custom_department_number

# 	# 				if acc_doc.root_type == "Liability" and row.get("custom_fund") == fund:
# 	# 					fund_account = row.get("account")

# 	# 				elif acc_doc.root_type == "Expense" and department == dept:
# 	# 					dept_account = row.get("account")

# 	# 			if not fund_account or not dept_account:
# 	# 				frappe.throw(
# 	# 					_("Please set Expense and Liability accounts in Salary Component {0}")
# 	# 					.format(get_link_to_form("Salary Component", salary_component))
# 	# 				)

# 	# 			return {
# 	# 				"fund_account": fund_account,
# 	# 				"dept_account": dept_account
# 	# 			}

# 	# 	if not account:
# 	# 		frappe.throw(
# 	# 			_("Please set account in Salary Component {0}")
# 	# 			.format(get_link_to_form("Salary Component", salary_component))
# 	# 		)

# 	# 	return account


# 	# def get_salary_component_accounts(self, salary_component, fund, department=None, employee=None):
# 	# 	print(salary_component, fund, employee, department, "salary_component, fund, employee=None, department=None sss///////////////")
# 	# 	comp_doc = frappe.get_cached_doc("Salary Component", salary_component)

# 	# 	# 🔹 INSURANCE OVERRIDE (merged ER + EE)
# 	# 	if comp_doc.type == "Deduction" and (
# 	# 		comp_doc.custom_is_this_insurance_component
# 	# 		or comp_doc.custom_is_this_employers_insurance_component
# 	# 	):
# 	# 		provider, category = self.get_insurance_details_from_ssa(
# 	# 			employee, salary_component
# 	# 		)

# 	# 		if provider:
# 	# 			return self.get_insurance_provider_account(
# 	# 				provider, salary_component, fund, department
# 	# 			)

# 	# 	# 🔹 EXISTING LOGIC (UNCHANGED)
# 	# 	filters = {"parent": salary_component, "custom_fund": fund}
# 	# 	account = None

# 	# 	for row in comp_doc.accounts:
# 	# 		acc_doc = frappe.get_cached_doc("Account", row.get("account"))
# 	# 		dept = acc_doc.custom_department_number

# 	# 		if department and department == dept:
# 	# 			filters = {
# 	# 				"parent": salary_component,
# 	# 				"custom_fund": fund,
# 	# 				"custom_department_name": department,
# 	# 			}
# 	# 			break

# 	# 	if department:
# 	# 		account = frappe.db.get_value(
# 	# 			"Salary Component Account", filters, "account", cache=True
# 	# 		)
# 	# 	else:
# 	# 		for row in comp_doc.accounts:
# 	# 			if row.get("custom_fund") == fund:
# 	# 				account = row.get("account")
# 	# 				break

# 	# 	if not account:
# 	# 		frappe.throw(
# 	# 			_("Please set account in Salary Component {0}")
# 	# 			.format(get_link_to_form("Salary Component", salary_component))
# 	# 		)

# 	# 	return account


# 	def get_salary_components(self, component_type):
# 		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

# 		if salary_slips:
# 			ss = frappe.qb.DocType("Salary Slip")
# 			ssd = frappe.qb.DocType("Salary Detail")
# 			salary_components = (
# 				frappe.qb.from_(ss)
# 				.join(ssd)
# 				.on(ss.name == ssd.parent)
# 				.select(
# 					ssd.salary_component,
# 					ssd.amount,
# 					ssd.parentfield,
# 					ssd.additional_salary,
# 					ss.salary_structure,
# 					ss.employee,
# 				)
# 				.where((ssd.parentfield == component_type) & (ss.name.isin([d.name for d in salary_slips])))
# 			).run(as_dict=True)

# 			return salary_components


# 	def get_salary_component_total(
# 		self,
# 		component_type=None,
# 		employee_wise_accounting_enabled=False
# 	):

# 		salary_components = self.get_salary_components(component_type)
# 		if salary_components:
# 			component_dict = {}
# 			for item in salary_components:
# 				if not self.should_add_component_to_accrual_jv(component_type, item):
# 					continue

# 				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
# 					item.employee, item.salary_structure
# 				)
			
# 				employee_advance = self.get_advance_deduction(component_type, item)
# 				for cost_center, percentage in employee_cost_centers.items():
					
# 					amount_against_cost_center = flt(item.amount) * percentage / 100

# 					if employee_advance:
# 						self.add_advance_deduction_entry(
# 							item, amount_against_cost_center, cost_center, employee_advance
# 						)

# 						print(component_dict.get(key, 0),"component_dict.get(key, 0)0000000000000000000000")
# 					else:

# 						fund = [_.custom_fund for _ in self.employees if _.employee == item.employee][0]
# 						employee = [_.employee for _ in self.employees if _.employee == item.employee][0]

# 						emp_department = [_.custom_department_name for _ in self.employees if _.employee == item.employee][0]


# 						# key = (item.salary_component, cost_center, fund, employee)

# 						if emp_department:
# 							key = (item.salary_component, cost_center, fund, emp_department, employee)
# 						else:
# 							key = (item.salary_component, cost_center, fund, None, employee)

# 						print(component_dict.get(key, 0),"component_dict.get(key, 0)-----------------------")
# 						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center
						

# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							component_type, item.employee, amount_against_cost_center
# 						)
# 			print(component_dict,"===component_dict")
# 			account_details = self.get_account(component_dict=component_dict)

# 			print(account_details,"===account_detailssssssssssssssssssssssssssssss")
# 			return account_details


# 	def get_employer_expense(
# 		self,
# 		component_type=None,
# 		employee_wise_accounting_enabled=False,
# 		employer_expense = False
# 	):

# 		salary_components = self.get_salary_components(component_type)

# 		if salary_components:
# 			component_dict = {}
# 			for item in salary_components:
# 				if not self.should_add_component_to_accrual_jv(component_type, item):
# 					continue

# 				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
# 					item.employee, item.salary_structure
# 				)
			
# 				employee_advance = self.get_advance_deduction(component_type, item)
# 				for cost_center, percentage in employee_cost_centers.items():
					
# 					amount_against_cost_center = flt(item.amount) * percentage / 100

# 					if employee_advance:
# 						self.add_advance_deduction_entry(
# 							item, amount_against_cost_center, cost_center, employee_advance
# 						)

# 					else:
# 						fund = [_.custom_fund for _ in self.employees if _.employee == item.employee][0]
# 						employee = [_.employee for _ in self.employees if _.employee == item.employee][0]

# 						emp_department = [_.custom_department_name for _ in self.employees if _.employee == item.employee][0]

# 						# key = (item.salary_component, cost_center, fund, employee)

# 						if emp_department:
# 							key = (item.salary_component, cost_center, fund, emp_department, employee)
# 						else:
# 							key = (item.salary_component, cost_center, fund, None, employee)

# 						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center
						
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							component_type, item.employee, amount_against_cost_center
# 						)

# 			print(component_dict,"F22")
# 			employer_expense_account_details = self.get_employer_expense_account(component_dict=component_dict)
			
# 			print(employer_expense_account_details,"===employer_expense_account_details")
# 			return employer_expense_account_details

# 	def should_add_component_to_accrual_jv(self, component_type: str, item: dict) -> bool:
# 		add_component_to_accrual_jv = True
# 		if component_type == "earnings":
# 			is_flexible_benefit, custom_only_tax_impact = frappe.get_cached_value(
# 				"Salary Component", item["salary_component"], ["is_flexible_benefit", "custom_only_tax_impact"]
# 			)
# 			if cint(is_flexible_benefit) and cint(custom_only_tax_impact):
# 				add_component_to_accrual_jv = False

# 		return add_component_to_accrual_jv

# 	def get_advance_deduction(self, component_type: str, item: dict) -> str | None:
# 		if component_type == "deductions" and item.additional_salary:
# 			ref_doctype, ref_docname = frappe.db.get_value(
# 				"Additional Salary",
# 				item.additional_salary,
# 				["ref_doctype", "ref_docname"],
# 			)

# 			if ref_doctype == "Employee Advance":
# 				return ref_docname
# 		return

# 	def add_advance_deduction_entry(
# 		self,
# 		item: dict,
# 		amount: float,
# 		cost_center: str,
# 		employee_advance: str,
# 	) -> None:
# 		self._advance_deduction_entries.append(
# 			{
# 				"employee": item.employee,
# 				"account": self.get_salary_component_account(item.salary_component),
# 				"amount": amount,
# 				"cost_center": cost_center,
# 				"reference_type": "Employee Advance",
# 				"reference_name": employee_advance,
# 			}
# 		)

# 	def set_accounting_entries_for_advance_deductions(
# 		self,
# 		accounts: list,
# 		currencies: list,
# 		company_currency: str,
# 		accounting_dimensions: list,
# 		precision: int,
# 		payable_amount: float,
# 	):
# 		for entry in self._advance_deduction_entries:
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				entry.get("account"),
# 				entry.get("cost_center"),
# 				entry.get("amount"),
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="credit",
# 				accounts=accounts,
# 				party=entry.get("employee"),
# 				reference_type="Employee Advance",
# 				reference_name=entry.get("reference_name"),
# 				is_advance="Yes",
# 			)

# 		return payable_amount

# 	def set_employee_based_payroll_payable_entries(
# 		self, component_type, employee, amount, salary_structure=None
# 	):

# 		print(amount, "call in set_employee_based_payroll_payable_entries------------")
# 		employee_details = self.employee_based_payroll_payable_entries.setdefault(employee, {})

# 		employee_details.setdefault(component_type, 0)
# 		employee_details[component_type] += amount

# 		# frappe.throw("======================")

# 		if salary_structure and "salary_structure" not in employee_details:
# 			employee_details["salary_structure"] = salary_structure

# 	def get_payroll_cost_centers_for_employee(self, employee, salary_structure):
# 		if not hasattr(self, "employee_cost_centers"):
# 			self.employee_cost_centers = {}

# 		if not self.employee_cost_centers.get(employee):
# 			SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
# 			EmployeeCostCenter = frappe.qb.DocType("Employee Cost Center")

# 			cost_centers = dict(
# 				(
# 					frappe.qb.from_(SalaryStructureAssignment)
# 					.join(EmployeeCostCenter)
# 					.on(SalaryStructureAssignment.name == EmployeeCostCenter.parent)
# 					.select(EmployeeCostCenter.cost_center, EmployeeCostCenter.percentage)
# 					.where(
# 						(SalaryStructureAssignment.employee == employee)
# 						& (SalaryStructureAssignment.docstatus == 1)
# 						& (SalaryStructureAssignment.salary_structure == salary_structure)
# 					)
# 				).run(as_list=True)
# 			)

# 			if not cost_centers:
# 				default_cost_center, department = frappe.get_cached_value(
# 					"Employee", employee, ["payroll_cost_center", "department"]
# 				)

# 				if not default_cost_center and department:
# 					default_cost_center = frappe.get_cached_value("Department", department, "payroll_cost_center")

# 				if not default_cost_center:
# 					default_cost_center = self.cost_center

# 				cost_centers = {default_cost_center: 100}

# 			self.employee_cost_centers.setdefault(employee, cost_centers)

# 		return self.employee_cost_centers.get(employee, {})

# # --------------------------------------below is working function in case of ER + EE amounts-----------------------------
# 	def get_account(self, component_dict=None, employee=None):
# 		print(component_dict, employee, "component_dict,employee111111 emprnexpense account with er+ee amnt*************************")
# 		account_dict = {}
# 		account_map = {}  # Maps (component, fund, department) to account

# 		# First pass: resolve accounts for all components
# 		for key in component_dict:
# 			component, cost_center, fund, department, employee = key
# 			account = self.get_salary_component_accounts(component, fund, department, employee)
# 			print(account, "account ------------------------------------------------------")
# 			account_map[key] = account

# 		# Second pass: aggregate amounts with deduction logic
# 		for key, amount in component_dict.items():
# 			component, cost_center, fund, department, employee = key
# 			comp_doc = frappe.get_doc("Salary Component", component)
# 			account = account_map[key]

# 			# Deduction logic: check for matching account with opposite do_not_include_in_total
# 			if comp_doc.type == "Deduction":
# 				for other_key, other_account in account_map.items():
# 					if other_key == key:
# 						continue

# 					other_component, _, other_fund, other_department, _ = other_key
# 					if other_fund != fund or other_department != department:
# 						continue

# 					other_doc = frappe.get_doc("Salary Component", other_component)
# 					if other_doc.type == "Deduction" and other_account == account:
# 						if comp_doc.do_not_include_in_total != other_doc.do_not_include_in_total:
# 							# Merge amounts under same accounting key
# 							key = other_key if other_doc.do_not_include_in_total is False else key
# 							break

# 			# Build accounting key
# 			if department:
# 				accounting_key = (account, cost_center, fund, department, employee)
# 			else:
# 				accounting_key = (account, cost_center, fund, employee)

# 			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

# 		print(account_dict, "account_dict 4444444444 er+ee amnt ************")

# 		return account_dict
	

# # --------------------------------------below is working function in case of ER + EE, ER expense separate amounts-----------------------------
# 	def get_employer_expense_account(self, component_dict=None, employee=None):
# 		print(component_dict, employee, "component_dict,employee111111 emprnexpense account*************************")
# 		account_dict = {}
# 		account_map = {}

# 		# First pass: resolve accounts
# 		for key in component_dict:
# 			component, cost_center, fund, department, employee = key
# 			account = self.get_salary_component_account(component, fund, department, employee)
# 			print(account, "account ----------------------------------tttttttttttttttttttttt")
# 			account_map[key] = account

# 		# Second pass: aggregate
# 		for key, amount in component_dict.items():
# 			component, cost_center, fund, department, employee = key
# 			comp_doc = frappe.get_doc("Salary Component", component)
# 			account_info = account_map[key]

# 			if isinstance(account_info, dict):
# 				# Deduction with do_not_include_in_total = True
# 				fund_account = account_info["fund_account"]
# 				dept_account = account_info["dept_account"]

# 				# # Normalize keys to always include department (even if None)
# 				# fund_key = (fund_account, cost_center, fund, department, employee)
# 				# account_dict[fund_key] = account_dict.get(fund_key, 0) + amount

# 				# Dept account gets only ER
# 				if comp_doc.type == "Deduction" and comp_doc.do_not_include_in_total:
# 					dept_key = (dept_account, cost_center, fund, department, employee)
# 					account_dict[dept_key] = account_dict.get(dept_key, 0) + amount

# 		print(account_dict, "account_dict44444444 get_employer_expense_account*************************")

# 		return account_dict



# 	def make_accrual_jv_entry(self, submitted_salary_slips):
# 		print("call in make_accrual_jv_entry---------------------------------------------")
# 		self.check_permission("write")
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)
# 		self.employee_based_payroll_payable_entries = {}
# 		self._advance_deduction_entries = []

# 		earnings = (
# 			self.get_salary_component_total(
# 				component_type="earnings",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled			)
# 			or {}
# 		)

# 		deductions = (
# 			self.get_salary_component_total(
# 				component_type="deductions",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled			)
# 			or {}
# 		)


# 		employer_expense = (
# 			self.get_employer_expense(
# 				component_type="deductions",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
# 				employer_expense = True
# 			)
# 			or {}
# 		)

# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")



# 		if earnings or deductions:
# 			accounts = []
# 			currencies = []
# 			payable_amount = 0
# 			accounting_dimensions = get_accounting_dimensions() or []
# 			company_currency = erpnext.get_company_currency(self.company)

# 			print(earnings,"============ererer")
# 			print(deductions,"============dddd")
# 			print(employer_expense,"============eeeeeeeeeeeeeeee")


# 			for emp in self.employees:
# 				payable_amount = 0
# 				# _earnings = {k:v for k,v in earnings.items() if k[-2] == emp.custom_fund and k[-1] == emp.employee}
# 				# _deductions = {k:v for k,v in deductions.items() if k[-2] == emp.custom_fund and k[-1] == emp.employee}

# 				_earnings = filter_salary_components(earnings, emp)
# 				_deductions = filter_salary_components(deductions, emp)
# 				_employer_expense = filter_salary_components(employer_expense, emp)
				
# 				print(_earnings,"============_earnings")
# 				print(_deductions,"============_deductions")
# 				print(_employer_expense,"============_employer_expense")

# 				# frappe.throw("pppppppppppppppppppppppppppppppp")

# 				payable_amount = self.get_payable_amount_for_earnings_and_deductions(
# 					accounts,
# 					_earnings,
# 					_deductions,
# 					_employer_expense,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 				)

# 				payable_amount = self.set_accounting_entries_for_advance_deductions(
# 					accounts,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 				)

# 				self.set_payable_amount_against_payroll_payable_account(
# 					accounts,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 					# self.payroll_payable_account,
# 					emp.custom_payroll_payable_account,
# 					employee_wise_accounting_enabled,
# 				)

# 				for ac in accounts:
# 					if "reference_name" in ac and "employee" not in ac:
# 						ac['employee'] = emp.employee
# 						break
			
# 			grouped_accounts = {"bank": [], "check": []}
# 			temp_group = []
# 			current_employee = None

# 			for entry in accounts:
# 				if "employee" in entry:
# 					if temp_group:
# 						current_employee = entry["employee"]
# 						payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method") or "Bank"
# 						if payment_method == "Bank":
# 							temp_group.append(entry)
# 							grouped_accounts["bank"].extend(temp_group)
# 						else:
# 							temp_group.append(entry)
# 							grouped_accounts["check"].append(temp_group)
# 						temp_group = []
					
# 				else:
# 					temp_group.append(entry)


# 			#============================================for bank type entries ======================			
# 			bank_accounts = grouped_accounts["bank"]
# 			bank_type_employees = list(set([_.get('employee') for _ in bank_accounts]))
# 			bank_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in bank_type_employees]

# 			if bank_accounts:

# 				for slip in bank_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", slip.name)
					
# 					cheque_no = slip_doc.custom_check_no or "PY Bank Entry"
				
# 				self.queue_journal_entry(
# 					bank_accounts,
# 					currencies,
# 					None,
# 					voucher_type="Journal Entry",
# 					custom_check_entry=False,
# 					cheque_date = "",
# 					cheque_no = cheque_no,
# 					user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
# 						self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					submitted_salary_slips=bank_salary_slips,
# 				)

# 			#==========================for check entries===========================
# 			check_accounts = grouped_accounts["check"]

# 			if check_accounts:

# 				check_type_employees = []

# 				for ch_acc in check_accounts:
# 					# check_type_employees = []
# 					emp =""
# 					for c_a in ch_acc:

# 						emp = c_a.get("employee")

# 						if emp and emp not in check_type_employees:
# 							check_type_employees.append(c_a.get("employee"))

# 					check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 					cur_salary_slip = [sal_slip for sal_slip in check_salary_slips if sal_slip.employee == emp]
# 					if cur_salary_slip:
# 						cur_salary_slip = cur_salary_slip[0]
					
# 					cheque_no = cur_salary_slip.custom_check_no or "PY Bank Entry"
					

# 					# frappe.throw("pppppppppppppppppppppppppppppppp")
# 					self.queue_journal_entry(
# 						ch_acc,
# 						currencies,
# 						None,
# 						voucher_type="Journal Entry",
# 						custom_check_entry=False,
# 						cheque_date = "",
# 						user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
# 							self.start_date, self.end_date
# 						),
# 						submit_journal_entry=True,
# 						submitted_salary_slips=check_salary_slips,
# 						cheque_no = cheque_no,
# 					)

		


# 	def create_payment_entries_by_method(self):
# 		bank_employees = []
# 		check_employees = []

# 		for emp_row in self.employees:
# 			custom_method = frappe.db.get_value("Employee", emp_row.employee, "custom_payment_method")
# 			if custom_method == "Bank":
# 				bank_employees.append(emp_row.employee)
# 			elif custom_method == "Check":
# 				check_employees.append(emp_row.employee)

# 		# Handle bank employees with one JV
# 		if bank_employees:
# 			self.create_bank_entry_for_employees(bank_employees)

# 		# Handle check employees with separate JVs
# 		for emp in check_employees:
# 			self.create_check_entry_for_employee(emp)



# 	def queue_journal_entry(
# 		self,
# 		accounts,
# 		currencies,
# 		payroll_payable_account=None,
# 		voucher_type="Journal Entry",
# 		custom_check_entry=False,
# 		cheque_date="",
# 		user_remark="",
# 		submitted_salary_slips=None,
# 		submit_journal_entry=False,
# 		cheque_no=None,
# 	):
# 		frappe.enqueue(
# 			"us_payroll.override.payroll_entry.enqueue_make_journal_entry",
# 			queue="long",
# 			timeout=1800,
# 			docname=self.name,
# 			accounts=accounts,
# 			currencies=currencies,
# 			payroll_payable_account=payroll_payable_account,
# 			voucher_type=voucher_type,
# 			custom_check_entry=custom_check_entry,
# 			cheque_date=cheque_date,
# 			user_remark=user_remark,
# 			submitted_salary_slips=submitted_salary_slips,
# 			submit_journal_entry=submit_journal_entry,
# 			cheque_no=cheque_no,
# 		)

# 		frappe.msgprint(
# 			_("Journal Entry creation has started in background."),
# 			alert=True,
# 			indicator="blue",
# 		)

# 	def make_journal_entry(
# 		self,
# 		accounts,
# 		currencies,
# 		payroll_payable_account=None,
# 		voucher_type="Journal Entry",
# 		custom_check_entry=False,
# 		cheque_date = "",
# 		user_remark="",
# 		submitted_salary_slips: list = None,
# 		submit_journal_entry=False,
# 		cheque_no = None,
# 	):

# 		print("call in make_journal_entry=============")		

# 		if voucher_type == "Journal Entry":

# 			payable_amount = 0
# 			payable_amount_dict = {}
# 			for acc in accounts:

# 				if not acc.get("fund"):
# 					acc_doc = frappe.get_doc("Account",{"name":acc.get("account")})
# 					acc['fund'] = acc_doc.custom_fund

# 				if "reference_name" in acc:
# 					payable_amount = acc.get("credit_in_account_currency")
# 					payable_amount_dict[(acc['fund'], acc['employee'])] = payable_amount
# 					# payable_amount_dict[acc['fund']] = payable_amount

# 			fund_account_mapping = {}


# 			bank_employees = []
# 			check_employees = []

# 			# payroll's account from Fund Setting
# 			for row in self.employees:	

# 				fund_value = row.custom_fund
# 				employee = row.employee
				
# 				if not (fund_value, row.employee) in payable_amount_dict:
# 					continue

# 				fund_setting_accounts = frappe.get_all("Payroll Accounts Config", 
# 								filters={"parent": "Fund Settings", "fund":fund_value}, 
# 								fields=["fund", "due_to_account", "due_from_account"])


# 				if fund_setting_accounts:
					
# 					due_from_account = fund_setting_accounts[0].get("due_from_account")
# 					due_to_account = fund_setting_accounts[0].get("due_to_account")

# 					acc_doc = frappe.get_doc("Account",{"name":due_from_account})
# 					due_from_account_name = f"{acc_doc.account_name} fund {fund_value}"

# 					if due_from_account and due_to_account:
# 						accounts.append({
# 							'account': due_from_account, 
# 							'custom_account_number': due_from_account_name, 
# 							'exchange_rate': 1.0, 
# 							# 'cost_center': 'Main - RL', 
# 							'cost_center': '',
# 							'project': None, 
# 							# 'debit_in_account_currency': payable_amount_dict[fund_value], 
# 							'debit_in_account_currency': payable_amount_dict[(fund_value, row.employee)], 
# 							'fund': fund_value
# 						})

# 						accounts.append({
# 							'account': due_to_account, 
# 							'exchange_rate': 1.0, 
# 							# 'cost_center': 'Main - RL', 
# 							'cost_center': '', 
# 							'project': None, 
# 							# 'credit_in_account_currency': payable_amount_dict[fund_value], 
# 							'credit_in_account_currency': payable_amount_dict[(fund_value, row.employee)],
# 							'fund': fund_value
# 						})


# 				else:				
# 					site_url = get_url()
# 					fund_settings_url = f"{site_url}/app/fund-settings/Fund%20Settings"

# 					frappe.throw(f"Please add Payroll Accounts for fund <b>{fund_value}</b> in <b>Payroll Accounts Config</b> table in <a href= '{fund_settings_url}' >Fund Settings</a>")

# 		# frappe.throw("[pppppppppppppppppppppppp")

# 		multi_currency = 0
# 		if len(currencies) > 1:
# 			multi_currency = 1

# 		journal_entry = frappe.new_doc("Journal Entry")
# 		journal_entry.voucher_type = voucher_type
# 		journal_entry.user_remark = user_remark
# 		journal_entry.company = self.company
# 		journal_entry.posting_date = self.posting_date
# 		journal_entry.cheque_date = self.posting_date
		
# 		if cheque_no:
# 			journal_entry.cheque_no = cheque_no
		
# 		journal_entry.custom_is_inter_fund_transaction = False
# 		# journal_entry.cheque_date = cheque_date
# 		journal_entry.custom_check_entry = custom_check_entry

# 		journal_entry.set("accounts", accounts)
# 		journal_entry.multi_currency = multi_currency

# 		journal_entry.save(ignore_permissions=True)
		
# 		if voucher_type == "Journal Entry":
# 			journal_entry.title = journal_entry.name

# 		if voucher_type == "Bank Entry":
# 			journal_entry.title = journal_entry.name


# 		journal_entry.save(ignore_permissions=True)

# 		try:
# 			if submit_journal_entry:
# 				journal_entry.submit()

# 			if submitted_salary_slips:
# 				self.update_salary_slip_status(submitted_salary_slips, jv_name=journal_entry.name)

# 		except Exception as e:
# 			if type(e) in (str, list, tuple):
# 				frappe.msgprint(e)

# 			self.log_error("Journal Entry creation against Salary Slip failed")
# 			raise

# 	def get_payable_amount_for_earnings_and_deductions(
# 		self,
# 		accounts,
# 		earnings,
# 		deductions,
# 		employer_expense,
# 		currencies,
# 		company_currency,
# 		accounting_dimensions,
# 		precision,
# 		payable_amount,
# 	):
# 		# Earnings
# 		for acc_cc, amount in earnings.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="debit",
# 				accounts=accounts,
# 			)

# 		print(payable_amount, "payable_amount ======== earningsssssssssssss")

# 		# Deductions
# 		for acc_cc, amount in deductions.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="credit",
# 				accounts=accounts,
# 			)


# 		print(payable_amount, "payable_amount ======== deductionssssssssssssssss")


# 		# Employer Expense
# 		for acc_cc, amount in employer_expense.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="debit",
# 				accounts=accounts,
# 			)

# 		print(payable_amount, "payable_amount ======== employer_expenseeeeeeeeeeeeee")

# 		# frappe.throw("pppppppppppppppppppppppppppppppp")

# 		return payable_amount

# 	def set_payable_amount_against_payroll_payable_account(
# 		self,
# 		accounts,
# 		currencies,
# 		company_currency,
# 		accounting_dimensions,
# 		precision,
# 		payable_amount,
# 		payroll_payable_account,
# 		employee_wise_accounting_enabled,
# 	):
# 		# Payable amount
# 		if employee_wise_accounting_enabled:
# 			"""
# 			employee_based_payroll_payable_entries = {
# 							'HREMP00004': {
# 											'earnings': 83332.0,
# 											'deductions': 2000.0
# 							},
# 							'HREMP00005': {
# 											'earnings': 50000.0,
# 											'deductions': 2000.0
# 							}
# 			}
# 			"""
# 			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
# 				payable_amount = employee_details.get("earnings", 0) - employee_details.get("deductions", 0)

# 				payable_amount = self.get_accounting_entries_and_payable_amount(
# 					payroll_payable_account,
# 					self.cost_center,
# 					payable_amount,
# 					currencies,
# 					company_currency,
# 					0,
# 					accounting_dimensions,
# 					precision,
# 					entry_type="payable",
# 					party=employee,
# 					accounts=accounts,
# 				)
# 		else:
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				payroll_payable_account,
# 				self.cost_center,
# 				payable_amount,
# 				currencies,
# 				company_currency,
# 				0,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="payable",
# 				accounts=accounts,
# 			)

# 	def get_accounting_entries_and_payable_amount(
# 		self,
# 		account,
# 		cost_center,
# 		amount,
# 		currencies,
# 		company_currency,
# 		payable_amount,
# 		accounting_dimensions,
# 		precision,
# 		entry_type="credit",
# 		party=None,
# 		accounts=None,
# 		reference_type=None,
# 		reference_name=None,
# 		is_advance=None,
# 	):

# 		exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
# 			account, amount, company_currency, currencies
# 		)

# 		row = {
# 			"account": account,
# 			"exchange_rate": flt(exchange_rate),
# 			"cost_center": cost_center,
# 			"project": self.project,
# 		}

# 		if entry_type == "debit":
# 			payable_amount += flt(amount, precision)
# 			row.update(
# 				{
# 					"debit_in_account_currency": flt(amt, precision),
# 				}
# 			)
# 		elif entry_type == "credit":
# 			payable_amount -= flt(amount, precision)
# 			row.update(
# 				{
# 					"credit_in_account_currency": flt(amt, precision),
# 				}
# 			)
# 		else:
# 			row.update(
# 				{
# 					"credit_in_account_currency": flt(amt, precision),
# 					"reference_type": self.doctype,
# 					"reference_name": self.name,
# 				}
# 			)

# 		if party:
# 			row.update(
# 				{
# 					"party_type": "Employee",
# 					"party": party,
# 				}
# 			)

# 		if reference_type:
# 			row.update(
# 				{
# 					"reference_type": reference_type,
# 					"reference_name": reference_name,
# 					"is_advance": is_advance,
# 				}
# 			)

# 		self.update_accounting_dimensions(
# 			row,
# 			accounting_dimensions,
# 		)

# 		if amt:
# 			accounts.append(row)

# 		return payable_amount

# 	def update_accounting_dimensions(self, row, accounting_dimensions):
# 		for dimension in accounting_dimensions:
# 			row.update({dimension: self.get(dimension)})

# 		return row

# 	def get_amount_and_exchange_rate_for_journal_entry(
# 		self, account, amount, company_currency, currencies
# 	):
# 		conversion_rate = 1
# 		exchange_rate = self.exchange_rate
# 		account_currency = frappe.db.get_value("Account", account, "account_currency")

# 		if account_currency not in currencies:
# 			currencies.append(account_currency)

# 		if account_currency == company_currency:
# 			conversion_rate = self.exchange_rate
# 			exchange_rate = 1

# 		amount = flt(amount) * flt(conversion_rate)

# 		return exchange_rate, amount


# 	def get_amount_and_exchange_rate_for_bank_entry(
# 		self, account, employee_amount_mapping, company_currency, currencies
# 	):
# 		# Dictionary to store exchange rate and amount for each employee
# 		employee_exchange_rate_amount = {}

# 		account_currency = frappe.db.get_value("Account", account, "account_currency")

# 		if account_currency not in currencies:
# 			currencies.append(account_currency)

# 		for employee, amount in employee_amount_mapping.items():
# 			# Initialize conversion_rate and exchange_rate
# 			conversion_rate = 1
# 			exchange_rate = self.exchange_rate

# 			if account_currency == company_currency:
# 				conversion_rate = self.exchange_rate
# 				exchange_rate = 1

# 			# Calculate the amount for this employee
# 			employee_amount = flt(amount) * flt(conversion_rate)

# 			# Store the exchange rate and calculated amount for the employee
# 			# employee_exchange_rate_amount[employee] = {
# 			# 	'exchange_rate': exchange_rate,
# 			# 	'amount': employee_amount
# 			# }

# 			employee_exchange_rate_amount[employee] = employee_amount
			

			

# 		return exchange_rate, employee_exchange_rate_amount



# 	# @frappe.whitelist()
# 	# def make_bank_entry(self):
# 	# 	print("call in make bank entry ====================")
# 	# 	self.check_permission("write")
# 	# 	self.employee_based_payroll_payable_entries = {}
# 	# 	employee_wise_accounting_enabled = frappe.db.get_single_value(
# 	# 		"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 	# 	)

# 	# 	print(employee_wise_accounting_enabled,"employee_wise_accounting_enabled in make bank entry 000000000000000000000")

# 	# 	employee_totals = {}

# 	# 	salary_slips = self.get_salary_slip_details()

# 	# 	print(salary_slips,"salary_slips in make bank entry 11111111111111")

# 	# 	for salary_detail in salary_slips:
# 	# 		employee = salary_detail.employee

# 	# 		if employee not in employee_totals:
# 	# 			employee_totals[employee] = 0

# 	# 		if salary_detail.parentfield == "earnings":
# 	# 			(
# 	# 				is_flexible_benefit,
# 	# 				custom_only_tax_impact,
# 	# 				create_separate_je,
# 	# 				statistical_component,
# 	# 			) = frappe.db.get_value(
# 	# 				"Salary Component",
# 	# 				salary_detail.salary_component,
# 	# 				(
# 	# 					"is_flexible_benefit",
# 	# 					"custom_only_tax_impact",
# 	# 					"custom_create_separate_payment_entry_against_benefit_claim",
# 	# 					"statistical_component",
# 	# 				),
# 	# 				cache=True,
# 	# 			)

# 	# 			if custom_only_tax_impact != 1 and statistical_component != 1:
# 	# 				if is_flexible_benefit == 1 and create_separate_je == 1:

# 	# 					self.set_accounting_entries_for_bank_entry(
# 	# 						salary_detail.amount, salary_detail.salary_component
# 	# 					)
# 	# 				else:
# 	# 					if employee_wise_accounting_enabled:
# 	# 						self.set_employee_based_payroll_payable_entries(
# 	# 							"earnings",
# 	# 							salary_detail.employee,
# 	# 							salary_detail.amount,
# 	# 							salary_detail.salary_structure,
# 	# 						)
# 	# 					employee_totals[employee] += salary_detail.amount

# 	# 		if salary_detail.parentfield == "deductions":
# 	# 			statistical_component = frappe.db.get_value(
# 	# 				"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 	# 			)

# 	# 			if not statistical_component:
# 	# 				if employee_wise_accounting_enabled:
# 	# 					print(employee_wise_accounting_enabled,"employee_wise_accounting_enabled in make bank entry 22222222222")
# 	# 					self.set_employee_based_payroll_payable_entries(
# 	# 						"deductions",
# 	# 						salary_detail.employee,
# 	# 						salary_detail.amount,
# 	# 						salary_detail.salary_structure,
# 	# 					)
# 	# 				employee_totals[employee] -= salary_detail.amount

# 	# 	total_salary_slip_amount = sum(employee_totals.values())
# 	# 	print(total_salary_slip_amount,"total_salary_slip_amount in make bank entry 33333333333333")
# 	# 	if total_salary_slip_amount > 0:
# 	# 		self.set_accounting_entries_for_bank_entry(employee_totals, "salary")


# 	# @frappe.whitelist()
# 	# def make_bank_entry(self):
# 	# 	print("call in make bank entry ====================")
# 	# 	self.check_permission("write")
# 	# 	self.employee_based_payroll_payable_entries = {}
# 	# 	employee_wise_accounting_enabled = frappe.db.get_single_value(
# 	# 		"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 	# 	)

# 	# 	employee_totals = {}
# 	# 	employer_totals = {}

# 	# 	salary_slips = self.get_salary_slip_details()

# 	# 	print(salary_slips,"salary_slips in make bank entry 11111111111111")

# 	# 	for salary_detail in salary_slips:
# 	# 		employee = salary_detail.employee

# 	# 		if employee not in employee_totals:
# 	# 			employee_totals[employee] = 0

# 	# 		if employee not in employer_totals:
# 	# 			employer_totals[employee] = 0

# 	# 		if salary_detail.parentfield == "earnings":
# 	# 			(
# 	# 				is_flexible_benefit,
# 	# 				custom_only_tax_impact,
# 	# 				create_separate_je,
# 	# 				statistical_component,
# 	# 			) = frappe.db.get_value(
# 	# 				"Salary Component",
# 	# 				salary_detail.salary_component,
# 	# 				(
# 	# 					"is_flexible_benefit",
# 	# 					"custom_only_tax_impact",
# 	# 					"custom_create_separate_payment_entry_against_benefit_claim",
# 	# 					"statistical_component",
# 	# 				),
# 	# 				cache=True,
# 	# 			)

# 	# 			if custom_only_tax_impact != 1 and statistical_component != 1:
# 	# 				if is_flexible_benefit == 1 and create_separate_je == 1:
# 	# 					print(salary_detail.amount,"salary_detail.amount111111111")

# 	# 					self.set_accounting_entries_for_bank_entry(
# 	# 						salary_detail.amount, salary_detail.salary_component
# 	# 					)
# 	# 				else:
# 	# 					if employee_wise_accounting_enabled:
# 	# 						self.set_employee_based_payroll_payable_entries(
# 	# 							"earnings",
# 	# 							salary_detail.employee,
# 	# 							salary_detail.amount,
# 	# 							salary_detail.salary_structure,
# 	# 						)
# 	# 					employee_totals[employee] += salary_detail.amount

# 	# 				print(employee_totals,"employee_totals in make bank entry 0000000")

# 	# 		if salary_detail.parentfield == "deductions":
# 	# 			statistical_component = frappe.db.get_value(
# 	# 				"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 	# 			)

# 	# 			if not statistical_component:
# 	# 				if employee_wise_accounting_enabled:
# 	# 					self.set_employee_based_payroll_payable_entries(
# 	# 						"deductions",
# 	# 						salary_detail.employee,
# 	# 						salary_detail.amount,
# 	# 						salary_detail.salary_structure,
# 	# 					)
# 	# 				employee_totals[employee] -= salary_detail.amount

# 	# 				comp_doc = frappe.get_doc("Salary Component", salary_detail.salary_component)
# 	# 				if comp_doc.do_not_include_in_total:
# 	# 					employer_totals[employee] += salary_detail.amount


# 	# 	total_salary_slip_amount = sum(employee_totals.values())
# 	# 	print(total_salary_slip_amount,"total_salary_slip_amount in make bank entry 33333333333333")

# 	# 	employer_salary_slip_amount = sum(employer_totals.values())

# 	# 	print(employer_salary_slip_amount,"employer_salary_slip_amount in make bank entry 444444444444")

# 	# 	salary_slip_amount_totals = total_salary_slip_amount + employer_salary_slip_amount

# 	# 	print(salary_slip_amount_totals,"salary_slip_amount_totals in make bank entry 44444444444444")

# 	# 	if salary_slip_amount_totals > 0:
# 	# 		self.set_accounting_entries_for_bank_entry(salary_slip_amount_totals, "salary")


# 	@frappe.whitelist()
# 	def make_bank_entry(self):
# 		print("call in make bank entry ====================")
# 		self.check_permission("write")
# 		self.employee_based_payroll_payable_entries = {}
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)

# 		employee_totals = {}
# 		total_net_salary = {}

# 		salary_slips = self.get_salary_slip_details()
# 		for salary_detail in salary_slips:
# 			employee = salary_detail.employee

# 			if employee not in employee_totals:
# 				employee_totals[employee] = 0

# 			if employee not in total_net_salary:
# 				total_net_salary[employee] = 0

# 			if salary_detail.parentfield == "earnings":
# 				(
# 					is_flexible_benefit,
# 					custom_only_tax_impact,
# 					create_separate_je,
# 					statistical_component,
# 				) = frappe.db.get_value(
# 					"Salary Component",
# 					salary_detail.salary_component,
# 					(
# 						"is_flexible_benefit",
# 						"custom_only_tax_impact",
# 						"custom_create_separate_payment_entry_against_benefit_claim",
# 						"statistical_component",
# 					),
# 					cache=True,
# 				)

# 				if custom_only_tax_impact != 1 and statistical_component != 1:
# 					if is_flexible_benefit == 1 and create_separate_je == 1:
# 						self.set_accounting_entries_for_bank_entry(
# 							salary_detail.amount, salary_detail.salary_component
# 						)
# 					else:
# 						if employee_wise_accounting_enabled:
# 							self.set_employee_based_payroll_payable_entries(
# 								"earnings",
# 								salary_detail.employee,
# 								salary_detail.amount,
# 								salary_detail.salary_structure,
# 							)
						
# 						total_net_salary[employee] += salary_detail.amount
# 			if salary_detail.parentfield == "deductions":
# 				statistical_component = frappe.db.get_value(
# 					"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 				)

# 				if not statistical_component:
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							"deductions",
# 							salary_detail.employee,
# 							salary_detail.amount,
# 							salary_detail.salary_structure,
# 						)
# 					total_net_salary[employee] -= salary_detail.amount

# 					comp_doc = frappe.get_doc("Salary Component", salary_detail.salary_component)
# 					if comp_doc.do_not_include_in_total:
# 						total_net_salary[employee] += salary_detail.amount

# 		total_salary_slip_amount = sum(total_net_salary.values())
# 		employer_salary_slip_amount = sum(total_net_salary.values())
# 		salary_slip_amount_totals = total_salary_slip_amount + employer_salary_slip_amount
# 		if salary_slip_amount_totals > 0:
# 			self.set_accounting_entries_for_bank_entry(total_net_salary, "salary")

# 	# @frappe.whitelist()
# 	# def make_check_entry(self):
# 	# 	self.check_permission("write")
# 	# 	self.employee_based_payroll_payable_entries = {}
# 	# 	employee_wise_accounting_enabled = frappe.db.get_single_value(
# 	# 		"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 	# 	)

# 	# 	employee_totals = {}

# 	# 	salary_slips = self.get_salary_slip_details()

# 	# 	for salary_detail in salary_slips:
# 	# 		employee = salary_detail.employee

# 	# 		if employee not in employee_totals:
# 	# 			employee_totals[employee] = 0

# 	# 		if salary_detail.parentfield == "earnings":
# 	# 			(
# 	# 				is_flexible_benefit,
# 	# 				custom_only_tax_impact,
# 	# 				create_separate_je,
# 	# 				statistical_component,
# 	# 			) = frappe.db.get_value(
# 	# 				"Salary Component",
# 	# 				salary_detail.salary_component,
# 	# 				(
# 	# 					"is_flexible_benefit",
# 	# 					"custom_only_tax_impact",
# 	# 					"custom_create_separate_payment_entry_against_benefit_claim",
# 	# 					"statistical_component",
# 	# 				),
# 	# 				cache=True,
# 	# 			)

# 	# 			if custom_only_tax_impact != 1 and statistical_component != 1:
# 	# 				if is_flexible_benefit == 1 and create_separate_je == 1:
# 	# 					self.set_accounting_entries_for_bank_entry(
# 	# 						salary_detail.amount, salary_detail.salary_component
# 	# 					)
# 	# 				else:
# 	# 					if employee_wise_accounting_enabled:
# 	# 						self.set_employee_based_payroll_payable_entries(
# 	# 							"earnings",
# 	# 							salary_detail.employee,
# 	# 							salary_detail.amount,
# 	# 							salary_detail.salary_structure,
# 	# 						)
# 	# 					employee_totals[employee] += salary_detail.amount

# 	# 		if salary_detail.parentfield == "deductions":
# 	# 			statistical_component = frappe.db.get_value(
# 	# 				"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 	# 			)

# 	# 			if not statistical_component:
# 	# 				if employee_wise_accounting_enabled:
# 	# 					self.set_employee_based_payroll_payable_entries(
# 	# 						"deductions",
# 	# 						salary_detail.employee,
# 	# 						salary_detail.amount,
# 	# 						salary_detail.salary_structure,
# 	# 					)
# 	# 				employee_totals[employee] -= salary_detail.amount

# 	# 	total_salary_slip_amount = sum(employee_totals.values())

# 	# 	if total_salary_slip_amount > 0:
# 	# 		self.set_accounting_entries_for_check_entry(employee_totals, "salary")


# 	@frappe.whitelist()
# 	def make_check_entry(self):
# 		print("call in make make_check_entry entry ====================")
# 		self.check_permission("write")
# 		self.employee_based_payroll_payable_entries = {}
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)

# 		employee_totals = {}
# 		total_net_salary = {}

# 		salary_slips = self.get_salary_slip_details()
# 		for salary_detail in salary_slips:
# 			employee = salary_detail.employee

# 			if employee not in employee_totals:
# 				employee_totals[employee] = 0

# 			if employee not in total_net_salary:
# 				total_net_salary[employee] = 0

# 			if salary_detail.parentfield == "earnings":
# 				(
# 					is_flexible_benefit,
# 					custom_only_tax_impact,
# 					create_separate_je,
# 					statistical_component,
# 				) = frappe.db.get_value(
# 					"Salary Component",
# 					salary_detail.salary_component,
# 					(
# 						"is_flexible_benefit",
# 						"custom_only_tax_impact",
# 						"custom_create_separate_payment_entry_against_benefit_claim",
# 						"statistical_component",
# 					),
# 					cache=True,
# 				)

# 				if custom_only_tax_impact != 1 and statistical_component != 1:
# 					if is_flexible_benefit == 1 and create_separate_je == 1:
# 						self.set_accounting_entries_for_bank_entry(
# 							salary_detail.amount, salary_detail.salary_component
# 						)
# 					else:
# 						if employee_wise_accounting_enabled:
# 							self.set_employee_based_payroll_payable_entries(
# 								"earnings",
# 								salary_detail.employee,
# 								salary_detail.amount,
# 								salary_detail.salary_structure,
# 							)
# 						total_net_salary[employee] += salary_detail.amount
# 			if salary_detail.parentfield == "deductions":
# 				statistical_component = frappe.db.get_value(
# 					"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 				)

# 				if not statistical_component:
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							"deductions",
# 							salary_detail.employee,
# 							salary_detail.amount,
# 							salary_detail.salary_structure,
# 						)
# 					total_net_salary[employee] -= salary_detail.amount

# 					comp_doc = frappe.get_doc("Salary Component", salary_detail.salary_component)
# 					if comp_doc.do_not_include_in_total:
# 						total_net_salary[employee] += salary_detail.amount

# 		total_salary_slip_amount = sum(total_net_salary.values())
# 		employer_salary_slip_amount = sum(total_net_salary.values())
# 		salary_slip_amount_totals = total_salary_slip_amount + employer_salary_slip_amount
# 		if salary_slip_amount_totals > 0:
# 			self.set_accounting_entries_for_check_entry(total_net_salary, "salary")


# 	def get_salary_slip_details(self):
# 		SalarySlip = frappe.qb.DocType("Salary Slip")
# 		SalaryDetail = frappe.qb.DocType("Salary Detail")

# 		return (
# 			frappe.qb.from_(SalarySlip)
# 			.join(SalaryDetail)
# 			.on(SalarySlip.name == SalaryDetail.parent)
# 			.select(
# 				SalarySlip.name,
# 				SalarySlip.employee,
# 				SalarySlip.salary_structure,
# 				SalaryDetail.salary_component,
# 				SalaryDetail.amount,
# 				SalaryDetail.parentfield,
# 			)
# 			.where(
# 				(SalarySlip.docstatus == 1)
# 				& (SalarySlip.start_date >= self.start_date)
# 				& (SalarySlip.end_date <= self.end_date)
# 				& (SalarySlip.payroll_entry == self.name)
# 			)
# 		).run(as_dict=True)


# 	def set_accounting_entries_for_bank_entry(self, je_payment_amount, user_remark):
# 		print(je_payment_amount, " je_payment_amount, set_accounting_entries_for_bank_entry in make bank entry -------------------")
# 		payroll_payable_account = self.payroll_payable_account
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

# 		accounts = []
# 		currencies = []
# 		company_currency = erpnext.get_company_currency(self.company)
# 		accounting_dimensions = get_accounting_dimensions() or []

# 		# Payroll Bank Cash Accounts Config from Fund Setting	
# 		for row in self.employees:

# 			fund_value = row.custom_fund
# 			employee = row.employee

# 			common_account_for_bank_entry = frappe.get_all("Payroll Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "due_from_account"])

# 			for common_acc in common_account_for_bank_entry:
# 				common_account = common_acc.get("due_from_account")

# 				acc_doc = frappe.get_doc("Account",{"name":common_account})
# 				due_from_account_name = f"{acc_doc.account_name} fund {fund_value}"

# 				common_fund = acc_doc.custom_fund

# 				common_cash_account_for_bank_entry = frappe.get_value("Payroll Bank Cash Accounts Config", 
# 					{"parent": "Fund Settings", "fund": common_fund}, 
# 					"account")

# 			fund_setting_accounts_for_bank_entry = frappe.get_all("Payroll Bank Cash Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "account"])

# 			if fund_setting_accounts_for_bank_entry:				
# 				bank_cash_account = fund_setting_accounts_for_bank_entry[0].get("account")
# 				if bank_cash_account:
# 					exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 						bank_cash_account, je_payment_amount, company_currency, currencies
# 					)
				
# 					for emp,amount in emplyee_amount_mapping.items():
# 						if emp == row.employee:
# 							emp_amount = amount
					
# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": bank_cash_account,
# 										"bank_account": self.bank_account,
# 										"credit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"employee":row.employee
# 									},
# 									accounting_dimensions,
# 								)
# 							)

# 					if self.employee_based_payroll_payable_entries:
# 						for employee, employee_details in self.employee_based_payroll_payable_entries.items():
# 							je_payment_amount = employee_details.get("earnings", 0) - (
# 								employee_details.get("deductions", 0)
# 							)
							
# 							exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 								bank_cash_account, je_payment_amount, company_currency, currencies
# 							)

# 							cost_centers = self.get_payroll_cost_centers_for_employee(
# 								employee, employee_details.get("salary_structure")
# 							)

# 							for cost_center, percentage in cost_centers.items():
# 								for emp,amount in emplyee_amount_mapping.items():
# 									if emp == row.employee:
# 										emp_amount = amount
# 										amount_against_cost_center = flt(emp_amount) * percentage / 100
# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": row.custom_payroll_payable_account,
# 													"debit_in_account_currency": flt(amount_against_cost_center, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"reference_type": self.doctype,
# 													"reference_name": self.name,
# 													"party_type": "Employee",
# 													"party": employee,
# 													"cost_center": cost_center,
# 													# "fund": fund
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": common_account,
# 													"custom_account_number": due_from_account_name,
# 													"bank_account": self.bank_account,
# 													"credit_in_account_currency": flt(emp_amount, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"cost_center": self.cost_center,
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": common_cash_account_for_bank_entry,
# 													"bank_account": self.bank_account,
# 													"debit_in_account_currency": flt(emp_amount, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"cost_center": self.cost_center,
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 					else:
# 						exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 							bank_cash_account, je_payment_amount, company_currency, currencies
# 						)

# 						for emp,amount in emplyee_amount_mapping.items():
# 							if emp == row.employee:
# 								emp_amount = amount
								
# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": row.custom_payroll_payable_account,
# 											"debit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"reference_type": self.doctype,
# 											"reference_name": self.name,
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)

# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": common_account,
# 											"custom_account_number": due_from_account_name,
# 											"bank_account": self.bank_account,
# 											"credit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)

# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": common_cash_account_for_bank_entry,
# 											"bank_account": self.bank_account,
# 											"debit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)			

# 			else:				
# 				site_url = get_url()
# 				fund_settings_url = f"{site_url}/app/fund-settings/Fund%20Settings"
# 				frappe.throw(f"Please add Payroll Bank/Cash Accounts for fund <b>{fund_value}</b> in <b>Payroll Bank Cash Accounts Config</b> table in <a href= '{fund_settings_url}' >Fund Settings</a>")

# 		# -------------------------------------------------------------------------------------------------

# 		grouped_accounts = {"bank": [], "check": []}
# 		temp_group = []
# 		current_employee = None

# 		for entry in accounts:			
# 			current_employee = entry["employee"]
# 			payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method")
# 			if payment_method == "Bank":
# 				grouped_accounts["bank"].append(entry)
# 			else:
# 				temp_group.append(entry)
# 				grouped_accounts["check"].append(entry)
					
# 		#for bank type entry 
# 		bank_accounts = grouped_accounts["bank"]
# 		if bank_accounts:
# 			# # Default cheque_no for Bank Entry
# 			cheque_no = "PY Bank Entry"

# 			self.queue_journal_entry(
# 				bank_accounts,
# 				currencies,
# 				voucher_type="Bank Entry",
# 				custom_check_entry=False,
# 				cheque_date = self.posting_date,
# 				user_remark=_("Payment of {0} from {1} to {2}").format(
# 					user_remark, self.start_date, self.end_date
# 				),
# 				submit_journal_entry=True,
# 				cheque_no = cheque_no,
# 			)

# 		#for check type entryes -------------------------------------------------------------
# 		submitted_salary_slips = frappe.db.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["name"])	

# 		check_accounts = grouped_accounts["check"]
# 		if check_accounts:
# 			grouped_by_employee = defaultdict(list)
# 			for entry in check_accounts:
# 				grouped_by_employee[entry['employee']].append(entry)
			
# 			grouped_by_employee = dict(grouped_by_employee)
# 			check_type_employees = []
# 			for emp, ch_acc in grouped_by_employee.items():
# 				if emp and emp not in check_type_employees:
# 						check_type_employees.append(emp)

# 				# check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 				check_salary_slip_check_no = []
# 				current_salary_slip = []
# 				for sl in submitted_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", sl.get("name"))

# 					if slip_doc.employee in check_type_employees and slip_doc.employee == emp:

# 						check_salary_slip_check_no.append(slip_doc.custom_check_no)				

# 				if check_salary_slip_check_no:
# 					check_salary_slip_check_no = check_salary_slip_check_no[0]
				
# 				cheque_no = check_salary_slip_check_no or "PY Bank Entry"
# 				self.queue_journal_entry(
# 					ch_acc,
# 					currencies,
# 					voucher_type="Bank Entry",
# 					custom_check_entry=False,
# 					cheque_date = self.posting_date,
# 					user_remark=_("Payment of {0} from {1} to {2}").format(
# 						user_remark, self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					cheque_no = cheque_no,
# 				)

# 	def set_accounting_entries_for_check_entry(self, je_payment_amount, user_remark):
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
# 		accounts = []
# 		currencies = []
# 		company_currency = erpnext.get_company_currency(self.company)
# 		accounting_dimensions = get_accounting_dimensions() or []

# 		# Payroll Bank Cash Accounts Config from Fund Setting
# 		for row in self.employees:
# 			fund_value = row.custom_fund
# 			employee = row.employee
# 			common_account_for_bank_entry = frappe.get_all("Payroll Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "due_to_account"])

# 			for common_acc in common_account_for_bank_entry:
# 				common_account = common_acc.get("due_to_account")

# 				acc_doc = frappe.get_doc("Account",{"name":common_account})
# 				due_to_account_name = f"{acc_doc.account_name} fund {fund_value}"

# 				common_fund = acc_doc.custom_fund

# 				common_cash_account_for_bank_entry = frappe.get_value("Payroll Bank Cash Accounts Config", 
# 					{"parent": "Fund Settings", "fund": common_fund}, 
# 					"account")

# 			fund_setting_accounts_for_bank_entry = frappe.get_all("Payroll Bank Cash Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "account"])

# 			if fund_setting_accounts_for_bank_entry:				
# 				bank_cash_account = fund_setting_accounts_for_bank_entry[0].get("account")
# 				if bank_cash_account:
# 					exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 						bank_cash_account, je_payment_amount, company_currency, currencies
# 					)
				
# 					for emp,amount in emplyee_amount_mapping.items():
# 						if emp == row.employee:
# 							emp_amount = amount

# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": common_account,
# 										"custom_account_number": due_to_account_name,
# 										"bank_account": self.bank_account,
# 										"debit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"reference_type" : 'Payroll Entry',
# 										"reference_name" : self.name,
# 										"employee":row.employee

# 									},
# 									accounting_dimensions,
# 								)
# 							)

# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": common_cash_account_for_bank_entry,
# 										"bank_account": self.bank_account,
# 										"credit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"employee":row.employee
# 									},
# 									accounting_dimensions,
# 								)
# 							)			

# 			else:				
# 				site_url = get_url()
# 				fund_settings_url = f"{site_url}/app/fund-settings/Fund%20Settings"

# 				frappe.throw(f"Please add Payroll Bank/Cash Accounts for fund <b>{fund_value}</b> in <b>Payroll Bank Cash Accounts Config</b> table in <a href= '{fund_settings_url}' >Fund Settings</a>")			

# 		# -------------------------------------------------------------------------------------------------
# 		grouped_accounts = {"bank": [], "check": []}
# 		temp_group = []
# 		current_employee = None

# 		for entry in accounts:			
# 			current_employee = entry["employee"]
# 			payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method")
# 			if payment_method == "Bank":
# 				grouped_accounts["bank"].append(entry)
# 			else:
# 				temp_group.append(entry)
# 				grouped_accounts["check"].append(entry)
		
# 		#for bank type entry 
# 		bank_accounts = grouped_accounts["bank"]
# 		if bank_accounts:
# 			# # Default cheque_no for Bank Entry
# 			cheque_no = "PY Bank Entry"

# 			self.queue_journal_entry(
# 				bank_accounts,
# 				currencies,
# 				voucher_type="Bank Entry",
# 				custom_check_entry=True,
# 				cheque_date = self.posting_date,
# 				user_remark=_("Payment of {0} from {1} to {2}").format(
# 					user_remark, self.start_date, self.end_date
# 				),
# 				submit_journal_entry=True,
# 				cheque_no = cheque_no,
# 			)

# 		##for check type entryes --------------------------------------------------------------------------------

# 		submitted_salary_slips = frappe.db.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["name"])
# 		check_accounts = grouped_accounts["check"]
# 		if check_accounts:
# 			grouped_by_employee = defaultdict(list)
# 			for entry in check_accounts:
# 				grouped_by_employee[entry['employee']].append(entry)
			
# 			grouped_by_employee = dict(grouped_by_employee)
# 			check_type_employees = []

# 			for emp, ch_acc in grouped_by_employee.items():
# 				if emp and emp not in check_type_employees:
# 						check_type_employees.append(emp)

# 				# check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 				check_salary_slip_check_no = []
# 				current_salary_slip = []
# 				for sl in submitted_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", sl.get("name"))
# 					if slip_doc.employee in check_type_employees and slip_doc.employee == emp:

# 						# check_salary_slips.append(sl.get("name"))

# 						check_salary_slip_check_no.append(slip_doc.custom_check_no)				

# 				if check_salary_slip_check_no:
# 					check_salary_slip_check_no = check_salary_slip_check_no[0]
				
# 				cheque_no = check_salary_slip_check_no or "PY Bank Entry"

# 				self.queue_journal_entry(
# 					ch_acc,
# 					currencies,
# 					voucher_type="Bank Entry",
# 					custom_check_entry=True,
# 					cheque_date = self.posting_date,
# 					user_remark=_("Payment of {0} from {1} to {2}").format(
# 						user_remark, self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					cheque_no = cheque_no,
# 				)


# 	def update_salary_slip_status(self, submitted_salary_slips, jv_name=None):
# 		SalarySlip = frappe.qb.DocType("Salary Slip")
# 		(
# 			frappe.qb.update(SalarySlip)
# 			.set(SalarySlip.journal_entry, jv_name)
# 			.where(SalarySlip.name.isin([salary_slip.name for salary_slip in submitted_salary_slips]))
# 		).run()

# 	def set_start_end_dates(self):
# 		self.update(
# 			get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company)
# 		)

# 	@frappe.whitelist()
# 	def get_employees_with_unmarked_attendance(self) -> list[dict] | None:
# 		if not self.validate_attendance:
# 			return

# 		unmarked_attendance = []
# 		employee_details = self.get_employee_and_attendance_details()
# 		default_holiday_list = frappe.db.get_value(
# 			"Company", self.company, "default_holiday_list", cache=True
# 		)

# 		for emp in self.employees:
# 			details = next((record for record in employee_details if record.name == emp.employee), None)
# 			if not details:
# 				continue

# 			start_date, end_date = self.get_payroll_dates_for_employee(details)
# 			holidays = self.get_holidays_count(
# 				details.holiday_list or default_holiday_list, start_date, end_date
# 			)
# 			payroll_days = date_diff(end_date, start_date) + 1
# 			unmarked_days = payroll_days - (holidays + details.attendance_count)

# 			if unmarked_days > 0:
# 				unmarked_attendance.append(
# 					{"employee": emp.employee, "employee_name": emp.employee_name, "unmarked_days": unmarked_days}
# 				)

# 		return unmarked_attendance

# 	def get_employee_and_attendance_details(self) -> list[dict]:
# 		"""Returns a list of employee and attendance details like
# 		[
# 				{
# 						"name": "HREMP00001",
# 						"date_of_joining": "2019-01-01",
# 						"relieving_date": "2022-01-01",
# 						"holiday_list": "Holiday List Company",
# 						"attendance_count": 22
# 				}
# 		]
# 		"""
# 		employees = [emp.employee for emp in self.employees]

# 		Employee = frappe.qb.DocType("Employee")
# 		Attendance = frappe.qb.DocType("Attendance")

# 		return (
# 			frappe.qb.from_(Employee)
# 			.left_join(Attendance)
# 			.on(
# 				(Employee.name == Attendance.employee)
# 				& (Attendance.attendance_date.between(self.start_date, self.end_date))
# 				& (Attendance.docstatus == 1)
# 			)
# 			.select(
# 				Employee.name,
# 				Employee.date_of_joining,
# 				Employee.relieving_date,
# 				Employee.holiday_list,
# 				Count(Attendance.name).as_("attendance_count"),
# 			)
# 			.where(Employee.name.isin(employees))
# 			.groupby(Employee.name)
# 		).run(as_dict=True)

# 	def get_payroll_dates_for_employee(self, employee_details: dict) -> tuple[str, str]:
# 		start_date = self.start_date
# 		if employee_details.date_of_joining > getdate(self.start_date):
# 			start_date = employee_details.date_of_joining

# 		end_date = self.end_date
# 		if employee_details.relieving_date and employee_details.relieving_date < getdate(self.end_date):
# 			end_date = employee_details.relieving_date

# 		return start_date, end_date

# 	def get_holidays_count(self, holiday_list: str, start_date: str, end_date: str) -> float:
# 		"""Returns number of holidays between start and end dates in the holiday list"""
# 		if not hasattr(self, "_holidays_between_dates"):
# 			self._holidays_between_dates = {}

# 		key = f"{start_date}-{end_date}-{holiday_list}"
# 		if key in self._holidays_between_dates:
# 			return self._holidays_between_dates[key]

# 		holidays = frappe.db.get_all(
# 			"Holiday",
# 			filters={"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])},
# 			fields=["COUNT(*) as holidays_count"],
# 		)[0]

# 		if holidays:
# 			self._holidays_between_dates[key] = holidays.holidays_count

# 		return self._holidays_between_dates.get(key) or 0


# 	def create_bank_entry_for_employees(self, employees):
# 		frappe.msgprint(_("Creating one Bank JV for Bank employees: {0}").format(", ".join(employees)))
# 		self.employees = [row for row in self.employees if row.employee in employees]
# 		self.make_bank_entry()

# 	def create_check_entry_for_employee(self, employee):
# 		frappe.msgprint(_("Creating Check JV for {0}").format(employee))
# 		self.employees = [row for row in self.employees if row.employee == employee]
# 		self.make_check_entry()

	

# def get_salary_structure(
# 	company: str, currency: str, salary_slip_based_on_timesheet: int, payroll_frequency: str
# ) -> list[str]:
# 	SalaryStructure = frappe.qb.DocType("Salary Structure")

# 	query = (
# 		frappe.qb.from_(SalaryStructure)
# 		.select(SalaryStructure.name)
# 		.where(
# 			(SalaryStructure.docstatus == 1)
# 			& (SalaryStructure.is_active == "Yes")
# 			& (SalaryStructure.company == company)
# 			& (SalaryStructure.currency == currency)
# 			& (SalaryStructure.salary_slip_based_on_timesheet == salary_slip_based_on_timesheet)
# 		)
# 	)

# 	if not salary_slip_based_on_timesheet:
# 		query = query.where(SalaryStructure.payroll_frequency == payroll_frequency)

# 	return query.run(pluck=True)


# def get_filtered_employees(
# 	sal_struct,
# 	filters,
# 	searchfield=None,
# 	search_string=None,
# 	fields=None,
# 	as_dict=False,
# 	limit=None,
# 	offset=None,
# 	ignore_match_conditions=False,
# ) -> list:
# 	SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
# 	Employee = frappe.qb.DocType("Employee")

# 	# query = (
# 	# 	frappe.qb.from_(Employee)
# 	# 	.join(SalaryStructureAssignment)
# 	# 	.on(Employee.name == SalaryStructureAssignment.employee)
# 	# 	.where(
# 	# 		(SalaryStructureAssignment.docstatus == 1)
# 	# 		& (Employee.status != "Inactive")
# 	# 		& (Employee.company == filters.company)
# 	# 		& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
# 	# 		& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
# 	# 		& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
# 	# 		# & (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
# 	# 		& (filters.end_date >= SalaryStructureAssignment.from_date)
# 	# 	)
# 	# )

# 	query = (
# 		frappe.qb.from_(Employee)
# 		.join(SalaryStructureAssignment)
# 		.on(Employee.name == SalaryStructureAssignment.employee)
# 		.where(
# 			(SalaryStructureAssignment.docstatus == 1)
# 			& (Employee.status != "Inactive")
# 			& (Employee.status != "Suspended")
# 			& (Employee.status != "Left")
# 			& (Employee.status != "Retired")
# 			& (Employee.status != "Terminated")
# 			& (Employee.status != "Resigned")
# 			& (Employee.company == filters.company)
# 			& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
# 			& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
# 			& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
# 			& (filters.end_date >= SalaryStructureAssignment.from_date)
# 		)
# 		.select(
# 			SalaryStructureAssignment.payroll_payable_account,  # Select the payroll_payable_account
# 			# Employee.name,
# 			# SalaryStructureAssignment.salary_structure,
# 			# SalaryStructureAssignment.from_date
# 		)
# 	)

# 	query = set_fields_to_select(query, fields)
# 	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
# 	query = set_filter_conditions(query, filters, qb_object=Employee)

# 	if not ignore_match_conditions:
# 		query = set_match_conditions(query=query, qb_object=Employee)

# 	if limit:
# 		query = query.limit(limit)

# 	if offset:
# 		query = query.offset(offset)

# 	return query.run(as_dict=as_dict)


# def set_fields_to_select(query, fields: list[str] = None):
# 	default_fields = ["employee", "employee_name", "department", "designation"]

# 	if fields:
# 		query = query.select(*fields).distinct()
# 	else:
# 		query = query.select(*default_fields).distinct()

# 	return query


# def set_searchfield(query, searchfield, search_string, qb_object):
# 	if searchfield:
# 		query = query.where(
# 			(qb_object[searchfield].like("%" + search_string + "%"))
# 			| (qb_object.employee_name.like("%" + search_string + "%"))
# 		)

# 	return query


# def set_filter_conditions(query, filters, qb_object):
# 	"""Append optional filters to employee query"""
# 	if filters.get("employees"):
# 		query = query.where(qb_object.name.notin(filters.get("employees")))

# 	for fltr_key in ["branch", "department", "designation", "grade"]:
# 		if filters.get(fltr_key):
# 			query = query.where(qb_object[fltr_key] == filters[fltr_key])

# 	return query


# def set_match_conditions(query, qb_object):
# 	match_conditions = get_match_cond("Employee", as_condition=False)

# 	for cond in match_conditions:
# 		if isinstance(cond, dict):
# 			for key, value in cond.items():
# 				if isinstance(value, list):
# 					query = query.where(qb_object[key].isin(value))
# 				else:
# 					query = query.where(qb_object[key] == value)

# 	return query


# def remove_payrolled_employees(emp_list, start_date, end_date):
# 	SalarySlip = frappe.qb.DocType("Salary Slip")

# 	employees_with_payroll = (
# 		frappe.qb.from_(SalarySlip)
# 		.select(SalarySlip.employee)
# 		.where(
# 			(SalarySlip.docstatus == 1)
# 			& (SalarySlip.start_date == start_date)
# 			& (SalarySlip.end_date == end_date)
# 		)
# 	).run(pluck=True)

# 	return [emp_list[emp] for emp in emp_list if emp not in employees_with_payroll]


# @frappe.whitelist()
# def get_start_end_dates(payroll_frequency, start_date=None, company=None):
#     """Returns dict of start and end dates for given payroll frequency based on start_date"""

#     if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
#         fiscal_year = get_fiscal_year(start_date, company=company)[0]
#         month = "%02d" % getdate(start_date).month
#         m = get_month_details(fiscal_year, month)
#         if payroll_frequency == "Bimonthly":
#             if getdate(start_date).day <= 15:
#                 start_date = m["month_start_date"]
#                 end_date = m["month_mid_end_date"]
#             else:
#                 start_date = m["month_mid_start_date"]
#                 end_date = m["month_end_date"]
#         else:
#             start_date = m["month_start_date"]
#             end_date = m["month_end_date"]

#     if payroll_frequency == "Weekly":
#         end_date = add_days(start_date, 6)
		
#     if payroll_frequency == "Bi-Weekly":
#         end_date = add_days(start_date, 13)
	
		
#     if payroll_frequency == "Fortnightly":
#         end_date = add_days(start_date, 13)

#     if payroll_frequency == "Daily":
#         end_date = start_date

#     return frappe._dict({"start_date": start_date, "end_date": end_date})



# @frappe.whitelist()
# def get_end_date(start_date, frequency):
# 	print(frequency,"--------------------")
# 	start_date = getdate(start_date)
# 	frequency = frequency.lower() if frequency else "monthly"
# 	kwargs = get_frequency_kwargs(frequency) if frequency != "bimonthly" else get_frequency_kwargs("monthly")

# 	# weekly, fortnightly and daily intervals have fixed days so no problems
# 	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
# 	if frequency != "bimonthly":
# 		return dict(end_date=end_date.strftime(DATE_FORMAT))

# 	else:
# 		return dict(end_date="")

# def get_frequency_kwargs(frequency_name):
# 	frequency_dict = {
# 		"monthly": {"months": 1},
# 		"fortnightly": {"days": 14},
# 		"weekly": {"days": 7},
# 		"daily": {"days": 1},
#         "bi-weekly": {"days": 14},
# 	}
# 	return frequency_dict.get(frequency_name)


# def get_month_details(year, month):
# 	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
# 	if ysd:
# 		import calendar
# 		import datetime

# 		diff_mnt = cint(month) - cint(ysd.month)
# 		if diff_mnt < 0:
# 			diff_mnt = 12 - int(ysd.month) + cint(month)
# 		msd = ysd + relativedelta(months=diff_mnt)  # month start date
# 		month_days = cint(calendar.monthrange(cint(msd.year), cint(month))[1])  # days in month
# 		mid_start = datetime.date(msd.year, cint(month), 16)  # month mid start date
# 		mid_end = datetime.date(msd.year, cint(month), 15)  # month mid end date
# 		med = datetime.date(msd.year, cint(month), month_days)  # month end date
# 		return frappe._dict(
# 			{
# 				"year": msd.year,
# 				"month_start_date": msd,
# 				"month_end_date": med,
# 				"month_mid_start_date": mid_start,
# 				"month_mid_end_date": mid_end,
# 				"month_days": month_days,
# 			}
# 		)
# 	else:
# 		frappe.throw(_("Fiscal Year {0} not found").format(year))


# def get_payroll_entry_bank_entries(payroll_entry_name):
# 	je = frappe.qb.DocType("Journal Entry")
# 	jea = frappe.qb.DocType("Journal Entry Account")

# 	journal_entries = (
# 		frappe.qb.from_(je)
# 		.from_(jea)
# 		.select(je.name)
# 		.where(
# 			(je.name == jea.parent)
# 			& (je.voucher_type == "Bank Entry")
# 			& (jea.reference_name == payroll_entry_name)
# 			& (jea.reference_type == "Payroll Entry")
# 		)
# 	).run(as_dict=True)

# 	return journal_entries


# @frappe.whitelist()
# def payroll_entry_has_bank_entries(name: str):
# 	response = {}
# 	bank_entries = get_payroll_entry_bank_entries(name)
# 	response["submitted"] = 1 if bank_entries else 0

# 	return response


# def log_payroll_failure(process, payroll_entry, error):
# 	error_log = frappe.log_error(
# 		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
# 	)
# 	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

# 	try:
# 		if isinstance(message_log, str):
# 			error_message = json.loads(message_log).get("message")
# 		else:
# 			error_message = message_log.get("message")
# 	except Exception:
# 		error_message = message_log

# 	error_message += "\n" + _("Check Error Log {0} for more details.").format(
# 		get_link_to_form("Error Log", error_log.name)
# 	)

# 	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})


# def create_salary_slips_for_employees(employees, args, publish_progress=True):
# 	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)

# 	try:
# 		salary_slips_exist_for = get_existing_salary_slips(employees, args)
# 		count = 0

# 		employees = list(set(employees) - set(salary_slips_exist_for))
# 		for emp in employees:
# 			args.update({"doctype": "Salary Slip", "employee": emp})
# 			frappe.get_doc(args).insert()

# 			count += 1
# 			if publish_progress:
# 				frappe.publish_progress(
# 					count * 100 / len(employees),
# 					title=_("Creating Salary Slips..."),
# 				)

# 		payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})

# 		if salary_slips_exist_for:
# 			frappe.msgprint(
# 				_(
# 					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
# 				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
# 				title=_("Message"),
# 				indicator="orange",
# 			)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("creation", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_creation", user=frappe.session.user)


# def show_payroll_submission_status(submitted, unsubmitted, payroll_entry):
# 	if not submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_(
# 				"No salary slip found to submit for the above selected criteria OR salary slip already submitted"
# 			)
# 		)
# 	elif submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_("Salary Slips submitted for period from {0} to {1}").format(
# 				payroll_entry.start_date, payroll_entry.end_date
# 			)
# 		)
# 	elif unsubmitted:
# 		frappe.msgprint(
# 			_("Could not submit some Salary Slips: {}").format(
# 				", ".join(get_link_to_form("Salary Slip", entry) for entry in unsubmitted)
# 			)
# 		)


# def get_existing_salary_slips(employees, args):
# 	SalarySlip = frappe.qb.DocType("Salary Slip")

# 	return (
# 		frappe.qb.from_(SalarySlip)
# 		.select(SalarySlip.employee)
# 		.distinct()
# 		.where(
# 			(SalarySlip.docstatus != 2)
# 			& (SalarySlip.company == args.company)
# 			& (SalarySlip.payroll_entry == args.payroll_entry)
# 			& (SalarySlip.start_date >= args.start_date)
# 			& (SalarySlip.end_date <= args.end_date)
# 			& (SalarySlip.employee.isin(employees))
# 		)
# 	).run(pluck=True)


# def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
# 	try:
# 		submitted = []
# 		unsubmitted = []
# 		frappe.flags.via_payroll_entry = True
# 		count = 0

# 		for entry in salary_slips:
# 			salary_slip = frappe.get_doc("Salary Slip", entry[0])
# 			if salary_slip.net_pay < 0:
# 				unsubmitted.append(entry[0])
# 			else:
# 				try:
# 					salary_slip.submit()
# 					submitted.append(salary_slip)
# 				except frappe.ValidationError:
# 					unsubmitted.append(entry[0])

# 			count += 1
# 			if publish_progress:
# 				frappe.publish_progress(count * 100 / len(salary_slips), title=_("Submitting Salary Slips..."))

# 		if submitted:
# 			payroll_entry.make_accrual_jv_entry(submitted)
# 			payroll_entry.email_salary_slip(submitted)
# 			payroll_entry.db_set({"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""})

# 		show_payroll_submission_status(submitted, unsubmitted, payroll_entry)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("submission", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_submission", user=frappe.session.user)

# 	frappe.flags.via_payroll_entry = False


# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
# 	return frappe.db.sql(
# 		"""
# 		select name from `tabPayroll Entry`
# 		where `{key}` LIKE %(txt)s
# 		and name not in
# 			(select reference_name from `tabJournal Entry Account`
# 				where reference_type="Payroll Entry")
# 		order by name limit %(start)s, %(page_len)s""".format(
# 			key=searchfield
# 		),
# 		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
# 	)


# def get_employee_list(
# 	filters: frappe._dict,
# 	searchfield=None,
# 	search_string=None,
# 	fields: list[str] = None,
# 	as_dict=True,
# 	limit=None,
# 	offset=None,
# 	ignore_match_conditions=False,
# ) -> list:
# 	sal_struct = get_salary_structure(
# 		filters.company,
# 		filters.currency,
# 		filters.salary_slip_based_on_timesheet,
# 		filters.payroll_frequency,
# 	)

# 	if not sal_struct:
# 		return []

# 	emp_list = get_filtered_employees(
# 		sal_struct,
# 		filters,
# 		searchfield,
# 		search_string,
# 		fields,
# 		as_dict=as_dict,
# 		limit=limit,
# 		offset=offset,
# 		ignore_match_conditions=ignore_match_conditions,
# 	)

# 	if as_dict:
# 		employees_to_check = {emp.employee: emp for emp in emp_list}
# 	else:
# 		employees_to_check = {emp[0]: emp for emp in emp_list}

# 	return remove_payrolled_employees(employees_to_check, filters.start_date, filters.end_date)



# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def employee_query(doctype, txt, searchfield, start, page_len, filters):
# 	doctype = "Employee"
# 	filters = frappe._dict(filters)

# 	if not filters.payroll_frequency:
# 		frappe.throw(_("Select Payroll Frequency."))

# 	employee_list = get_employee_list(
# 		filters,
# 		searchfield=searchfield,
# 		search_string=txt,
# 		fields=["name", "employee_name"],
# 		as_dict=False,
# 		limit=page_len,
# 		offset=start,
# 	)

# 	return employee_list


# def filter_salary_components(components, emp):
# 	filtered = {}
# 	for k, v in components.items():
# 		# last element is always employee
# 		if k[-1] != emp.employee:
# 			continue  

# 		fund = k[2]

# 		if len(k) == 5:
# 			department = k[3]
# 			if fund == emp.custom_fund and department == emp.custom_department_name:
# 				filtered[k] = v

# 		elif len(k) == 4:
# 			if fund == emp.custom_fund:
# 				filtered[k] = v
# 	return filtered



# def enqueue_make_journal_entry(
# 	docname,
# 	accounts,
# 	currencies,
# 	payroll_payable_account=None,
# 	voucher_type="Journal Entry",
# 	custom_check_entry=False,
# 	cheque_date="",
# 	user_remark="",
# 	submitted_salary_slips=None,
# 	submit_journal_entry=False,
# 	cheque_no=None,
# ):
# 	"""
# 	Background job with realtime progress (no custom fields)
# 	"""

# 	try:
# 		frappe.publish_progress(
# 			0,
# 			title=_("Queued"),
# 			description=_("Waiting for worker"),
# 		)

# 		doc = frappe.get_doc("Payroll Entry", docname)

# 		frappe.publish_progress(
# 			20,
# 			title=_("Processing"),
# 			description=_("Preparing Journal Entry"),
# 		)

# 		# MAIN LOGIC
# 		frappe.publish_progress(
# 			50,
# 			title=_("Processing"),
# 			description=_("Creating Journal Entry"),
# 		)

# 		doc.make_journal_entry(
# 			accounts=accounts,
# 			currencies=currencies,
# 			payroll_payable_account=payroll_payable_account,
# 			voucher_type=voucher_type,
# 			custom_check_entry=custom_check_entry,
# 			cheque_date=cheque_date,
# 			user_remark=user_remark,
# 			submitted_salary_slips=submitted_salary_slips,
# 			submit_journal_entry=submit_journal_entry,
# 			cheque_no=cheque_no,
# 		)

# 		frappe.publish_progress(
# 			100,
# 			title=_("Completed"),
# 			description=_("Journal Entry created successfully"),
# 		)

# 	except Exception:
# 		frappe.publish_progress(
# 			100,
# 			title=_("Failed"),
# 			description=_("Error occurred. Check Error Log"),
# 		)

# 		frappe.log_error(
# 			frappe.get_traceback(),
# 			"Payroll Journal Entry Background Job Failed",
# 		)
# 		raise


# # ================================= below is working logic by removing fund and dept ============================================================
# # Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# import json
# from dateutil.relativedelta import relativedelta
# import frappe
# from frappe import _
# from frappe.desk.reportview import get_match_cond
# from frappe.model.document import Document
# from frappe.query_builder.functions import Coalesce, Count
# from frappe.utils import (
# 	DATE_FORMAT,
# 	add_days,
# 	add_to_date,
# 	cint,
# 	comma_and,
# 	date_diff,
# 	flt,
# 	get_link_to_form,
# 	getdate,
# )
# import erpnext
# from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
# 	get_accounting_dimensions,
# )
# from erpnext.accounts.utils import get_fiscal_year
# from frappe.utils import get_url
# from collections import defaultdict
# import time
# import logging
# from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
# logger = frappe.logger("payroll_jv", allow_site=True)

# class OverridePayrollEntry(PayrollEntry):
# 	def onload(self):
# 		if not self.docstatus == 1 or self.salary_slips_submitted:
# 			return

# 		# check if salary slips were manually submitted
# 		entries = frappe.db.count("Salary Slip", {"payroll_entry": self.name, "docstatus": 1}, ["name"])
# 		if cint(entries) == len(self.employees):
# 			self.set_onload("submitted_ss", True)

# 	def validate(self):
# 		self.number_of_employees = len(self.employees)
# 		self.set_status()

# 	def set_status(self, status=None, update=False):
# 		if not status:
# 			status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

# 		if update:
# 			self.db_set("status", status)
# 		else:
# 			self.status = status

# 	def before_submit(self):
# 		self.validate_existing_salary_slips()
# 		self.validate_payroll_payable_account()
# 		if self.get_employees_with_unmarked_attendance():
# 			frappe.throw(_("Cannot submit. Attendance is not marked for some employees."))

# 	def on_submit(self):
# 		self.set_status(update=True, status="Submitted")
# 		self.create_salary_slips()


# 	def validate_existing_salary_slips(self):
# 		if not self.employees:
# 			return

# 		existing_salary_slips = []
# 		SalarySlip = frappe.qb.DocType("Salary Slip")

# 		existing_salary_slips = (
# 			frappe.qb.from_(SalarySlip)
# 			.select(SalarySlip.employee, SalarySlip.name)
# 			.where(
# 				(SalarySlip.employee.isin([emp.employee for emp in self.employees]))
# 				& (SalarySlip.start_date == self.start_date)
# 				& (SalarySlip.end_date == self.end_date)
# 				& (SalarySlip.docstatus != 2)
# 			)
# 		).run(as_dict=True)

# 		if len(existing_salary_slips):
# 			msg = _("Salary Slip already exists for {0} for the given dates").format(
# 				comma_and([frappe.bold(d.employee) for d in existing_salary_slips])
# 			)
# 			msg += "<br><br>"
# 			msg += _("Reference: {0}").format(
# 				comma_and([get_link_to_form("Salary Slip", d.name) for d in existing_salary_slips])
# 			)
# 			frappe.throw(
# 				msg,
# 				title=_("Duplicate Entry"),
# 			)

	
# 	@frappe.whitelist()
# 	def has_bank_entries(self) -> dict[str, bool]:
# 		je = frappe.qb.DocType("Journal Entry")
# 		jea = frappe.qb.DocType("Journal Entry Account")

# 		bank_entries = (
# 			frappe.qb.from_(je)
# 			.inner_join(jea)
# 			.on(je.name == jea.parent)
# 			.select(je.name)
# 			.where(
# 				(je.voucher_type == "Bank Entry")
# 				& (jea.reference_name == self.name)
# 				& (jea.reference_type == "Payroll Entry")
# 			)
# 		).run(as_dict=True)

# 		return {
# 			"has_bank_entries": bool(bank_entries),
# 			"has_bank_entries_for_withheld_salaries": not any(
# 				employee.is_salary_withheld for employee in self.employees
# 			),
# 		}
		
# 	def validate_payroll_payable_account(self):
# 		if frappe.db.get_value("Account", self.payroll_payable_account, "account_type"):
# 			frappe.throw(
# 				_(
# 					"Account type cannot be set for payroll payable account {0}, please remove and try again"
# 				).format(frappe.bold(get_link_to_form("Account", self.payroll_payable_account)))
# 			)

# 	def on_cancel(self):
# 		self.ignore_linked_doctypes = ("GL Entry", "Salary Slip", "Journal Entry")

# 		self.delete_linked_salary_slips()
# 		self.cancel_linked_journal_entries()

# 		# reset flags & update status
# 		self.db_set("salary_slips_created", 0)
# 		self.db_set("salary_slips_submitted", 0)
# 		self.set_status(update=True, status="Cancelled")
# 		self.db_set("error_message", "")

# 	def cancel(self):
# 		if len(self.get_linked_salary_slips()) > 50:
# 			msg = _("Payroll Entry cancellation is queued. It may take a few minutes")
# 			msg += "<br>"
# 			msg += _(
# 				"In case of any error during this background process, the system will add a comment about the error on this Payroll Entry and revert to the Submitted status"
# 			)
# 			frappe.msgprint(
# 				msg,
# 				indicator="blue",
# 				title=_("Cancellation Queued"),
# 			)
# 			self.queue_action("cancel", timeout=3000)
# 		else:
# 			self._cancel()

# 	def delete_linked_salary_slips(self):
# 		salary_slips = self.get_linked_salary_slips()

# 		# cancel & delete salary slips
# 		for salary_slip in salary_slips:
# 			if salary_slip.docstatus == 1:
# 				frappe.get_doc("Salary Slip", salary_slip.name).cancel()
# 			frappe.delete_doc("Salary Slip", salary_slip.name)

# 	def cancel_linked_journal_entries(self):
# 		journal_entries = frappe.get_all(
# 			"Journal Entry Account",
# 			{"reference_type": self.doctype, "reference_name": self.name, "docstatus": 1},
# 			pluck="parent",
# 			distinct=True,
# 		)

# 		# cancel Journal Entries
# 		for je in journal_entries:
# 			frappe.get_doc("Journal Entry", je).cancel()

# 	def get_linked_salary_slips(self):
# 		return frappe.get_all("Salary Slip", {"payroll_entry": self.name}, ["name", "docstatus"])

# 	def make_filters(self):
# 		filters = frappe._dict(
# 			company=self.company,
# 			branch=self.branch,
# 			department=self.department,
# 			designation=self.designation,
# 			grade=self.grade,
# 			currency=self.currency,
# 			start_date=self.start_date,
# 			end_date=self.end_date,
# 			payroll_payable_account=self.payroll_payable_account,
# 			salary_slip_based_on_timesheet=self.salary_slip_based_on_timesheet,
# 		)

# 		if not self.salary_slip_based_on_timesheet:
# 			filters.update(dict(payroll_frequency=self.payroll_frequency))

# 		return filters

# 	@frappe.whitelist()
# 	def fill_employee_details(self):
# 		filters = self.make_filters()
# 		employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)

# 		# Replace 'payroll_payable_account' with 'custom_payroll_payable_account'
# 		for employee in employees:
# 			employee['custom_payroll_payable_account'] = employee.pop('payroll_payable_account')

# 		self.set("employees", [])

# 		if not employees:
# 			error_msg = _(
# 				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
# 			).format(
# 				frappe.bold(self.company),
# 				frappe.bold(self.currency),
# 				frappe.bold(self.payroll_payable_account),
# 			)
# 			if self.branch:
# 				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
# 			if self.department:
# 				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
# 			if self.designation:
# 				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
# 			if self.start_date:
# 				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
# 			if self.end_date:
# 				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
# 			frappe.throw(error_msg, title=_("No employees found"))

# 		self.set("employees", employees)
# 		self.number_of_employees = len(self.employees)

# 		return self.get_employees_with_unmarked_attendance()


# 	@frappe.whitelist()
# 	def create_salary_slips(self):
# 		"""
# 		Creates salary slip for selected employees if already not created
# 		"""
# 		add_check_employees = []
# 		for row in self.employees:
# 			employee_payment_method = frappe.db.get_value("Employee", row.employee, "custom_payment_method")
# 			if employee_payment_method == "Check":
# 				add_check_employees.append(row.employee)

# 		available_check = frappe.get_all(
# 				"Check",
# 				filters={"status": "Available"},
# 				fields=["name", "check_number"],
# 				order_by="check_number ASC",
# 			)

# 		available_check = available_check[::-1]

# 		if len(available_check) < len(add_check_employees):
# 			frappe.throw("Number of available checks are less than the required.")

# 		else:

# 			self.check_permission("write")
# 			employees = [emp.employee for emp in self.employees]

# 			if employees:
# 				args = frappe._dict(
# 					{
# 						"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
# 						"payroll_frequency": self.payroll_frequency,
# 						"start_date": self.start_date,
# 						"end_date": self.end_date,
# 						"company": self.company,
# 						"posting_date": self.posting_date,
# 						"deduct_tax_for_unclaimed_employee_benefits": 0,
# 						"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
# 						"payroll_entry": self.name,
# 						"exchange_rate": self.exchange_rate,
# 						"currency": self.currency,
# 					}
# 				)
# 				if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
# 					self.db_set("status", "Queued")
# 					frappe.enqueue(
# 						create_salary_slips_for_employees,
# 						timeout=3000,
# 						employees=employees,
# 						args=args,
# 						publish_progress=False,
# 					)
# 					frappe.msgprint(
# 						_("Salary Slip creation is queued. It may take a few minutes"),
# 						alert=True,
# 						indicator="blue",
# 					)
# 				else:
# 					create_salary_slips_for_employees(employees, args, publish_progress=False)
# 					# since this method is called via frm.call this doc needs to be updated manually
# 					self.reload()


# 	def get_sal_slip_list(self, ss_status, as_dict=False):
# 		"""
# 		Returns list of salary slips based on selected criteria
# 		"""

# 		ss = frappe.qb.DocType("Salary Slip")
# 		ss_list = (
# 			frappe.qb.from_(ss)
# 			.select(ss.name, ss.salary_structure)
# 			.where(
# 				(ss.docstatus == ss_status)
# 				& (ss.start_date >= self.start_date)
# 				& (ss.end_date <= self.end_date)
# 				& (ss.payroll_entry == self.name)
# 				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
# 				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
# 			)
# 		).run(as_dict=as_dict)

# 		return ss_list

# 	@frappe.whitelist()
# 	def submit_salary_slips(self):
# 		self.check_permission("write")
# 		salary_slips = self.get_sal_slip_list(ss_status=0)

# 		if len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry:
# 			self.db_set("status", "Queued")
# 			frappe.enqueue(
# 				submit_salary_slips_for_employees,
# 				timeout=3000,
# 				payroll_entry=self,
# 				salary_slips=salary_slips,
# 				publish_progress=False,
# 			)
# 			frappe.msgprint(
# 				_("Salary Slip submission is queued. It may take a few minutes"),
# 				alert=True,
# 				indicator="blue",
# 			)
# 		else:
# 			submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

# 	def email_salary_slip(self, submitted_ss):
# 		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
# 			for ss in submitted_ss:
# 				ss.email_salary_slip()


# # # ----------------------below is working in case of expense and  2 liability accounts-----------------
# 	def get_salary_component_accounts(self, salary_component):
# 		comp_doc = frappe.get_doc("Salary Component", salary_component)
# 		account = None

# 		# Deduction + employer component:
# 		# pick LIABILITY account so ER + EE merge in JE credit
# 		if (
# 			comp_doc.type == "Deduction"
# 			and comp_doc.custom_is_employer_component
# 		):
# 			for row in comp_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.account)

# 				if acc_doc.root_type == "Liability":
# 					account = row.account
# 					break

# 		# Normal earning/deduction
# 		if not account:
# 			for row in comp_doc.accounts:
# 				account = row.account
# 				break

# 		if not account:
# 			frappe.throw(
# 				_("Please set account in Salary Component {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				)
# 			)

# 		return account

# # # ----------------------below is working in case of expense and liability----------------
# 	def get_salary_component_account(self, salary_component):
# 		comp_doc = frappe.get_doc("Salary Component", salary_component)
# 		account = None

# 		# Employer deduction with separate liability + expense
# 		if (
# 			comp_doc.type == "Deduction"
# 			and comp_doc.do_not_include_in_total
# 			and comp_doc.custom_is_employer_component
# 		):
# 			liability_account = None
# 			expense_account = None

# 			for row in comp_doc.accounts:
# 				acc_doc = frappe.get_doc("Account", row.account)

# 				if acc_doc.root_type == "Liability" and not liability_account:
# 					liability_account = row.account

# 				elif acc_doc.root_type == "Expense" and not expense_account:
# 					expense_account = row.account

# 			if not liability_account:
# 				frappe.throw(
# 					_("Please set Liability account in Salary Component {0}").format(
# 						get_link_to_form("Salary Component", salary_component)
# 					)
# 				)

# 			if not expense_account:
# 				frappe.throw(
# 					_("Please set Expense account in Salary Component {0}").format(
# 						get_link_to_form("Salary Component", salary_component)
# 					)
# 				)

# 			return {
# 				"liability_account": liability_account,
# 				"expense_account": expense_account,
# 			}

# 		# Normal earning/deduction
# 		for row in comp_doc.accounts:
# 			account = row.account
# 			break

# 		if not account:
# 			frappe.throw(
# 				_("Please set account in Salary Component {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				)
# 			)

# 		return account

# 	def get_salary_components(self, component_type):
# 		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

# 		if salary_slips:
# 			ss = frappe.qb.DocType("Salary Slip")
# 			ssd = frappe.qb.DocType("Salary Detail")
# 			salary_components = (
# 				frappe.qb.from_(ss)
# 				.join(ssd)
# 				.on(ss.name == ssd.parent)
# 				.select(
# 					ssd.salary_component,
# 					ssd.amount,
# 					ssd.parentfield,
# 					ssd.additional_salary,
# 					ss.salary_structure,
# 					ss.employee,
# 				)
# 				.where((ssd.parentfield == component_type) & (ss.name.isin([d.name for d in salary_slips])))
# 			).run(as_dict=True)

# 			return salary_components


# 	def get_salary_component_total(
# 		self,
# 		component_type=None,
# 		employee_wise_accounting_enabled=False
# 	):

# 		salary_components = self.get_salary_components(component_type)
# 		if salary_components:
# 			component_dict = {}
# 			for item in salary_components:
# 				if not self.should_add_component_to_accrual_jv(component_type, item):
# 					continue

# 				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
# 					item.employee, item.salary_structure
# 				)
			
# 				employee_advance = self.get_advance_deduction(component_type, item)
# 				for cost_center, percentage in employee_cost_centers.items():
					
# 					amount_against_cost_center = flt(item.amount) * percentage / 100

# 					if employee_advance:
# 						self.add_advance_deduction_entry(
# 							item, amount_against_cost_center, cost_center, employee_advance
# 						)
# 					else:
# 						employee = [_.employee for _ in self.employees if _.employee == item.employee][0]
# 						key = (item.salary_component, cost_center)
		
# 						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center						

# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							component_type, item.employee, amount_against_cost_center
# 						)
# 			account_details = self.get_account(component_dict=component_dict)
# 			return account_details


# 	def get_employer_expense(
# 		self,
# 		component_type=None,
# 		employee_wise_accounting_enabled=False,
# 		employer_expense = False
# 	):

# 		salary_components = self.get_salary_components(component_type)
# 		if salary_components:
# 			component_dict = {}
# 			for item in salary_components:
# 				if not self.should_add_component_to_accrual_jv(component_type, item):
# 					continue

# 				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
# 					item.employee, item.salary_structure
# 				)
			
# 				employee_advance = self.get_advance_deduction(component_type, item)
# 				for cost_center, percentage in employee_cost_centers.items():
					
# 					amount_against_cost_center = flt(item.amount) * percentage / 100

# 					if employee_advance:
# 						self.add_advance_deduction_entry(
# 							item, amount_against_cost_center, cost_center, employee_advance
# 						)

# 					else:
# 						employee = [_.employee for _ in self.employees if _.employee == item.employee][0]
# 						key = (item.salary_component, cost_center)

# 						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center
						
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							component_type, item.employee, amount_against_cost_center
# 						)
# 			employer_expense_account_details = self.get_employer_expense_account(component_dict=component_dict)
# 			return employer_expense_account_details

# 	def should_add_component_to_accrual_jv(self, component_type: str, item: dict) -> bool:
# 		add_component_to_accrual_jv = True
# 		if component_type == "earnings":
# 			is_flexible_benefit, custom_only_tax_impact = frappe.get_cached_value(
# 				"Salary Component", item["salary_component"], ["is_flexible_benefit", "custom_only_tax_impact"]
# 			)
# 			if cint(is_flexible_benefit) and cint(custom_only_tax_impact):
# 				add_component_to_accrual_jv = False

# 		return add_component_to_accrual_jv

# 	def get_advance_deduction(self, component_type: str, item: dict) -> str | None:
# 		if component_type == "deductions" and item.additional_salary:
# 			ref_doctype, ref_docname = frappe.db.get_value(
# 				"Additional Salary",
# 				item.additional_salary,
# 				["ref_doctype", "ref_docname"],
# 			)

# 			if ref_doctype == "Employee Advance":
# 				return ref_docname
# 		return

# 	def add_advance_deduction_entry(
# 		self,
# 		item: dict,
# 		amount: float,
# 		cost_center: str,
# 		employee_advance: str,
# 	) -> None:
# 		self._advance_deduction_entries.append(
# 			{
# 				"employee": item.employee,
# 				"account": self.get_salary_component_account(item.salary_component),
# 				"amount": amount,
# 				"cost_center": cost_center,
# 				"reference_type": "Employee Advance",
# 				"reference_name": employee_advance,
# 			}
# 		)

# 	def set_accounting_entries_for_advance_deductions(
# 		self,
# 		accounts: list,
# 		currencies: list,
# 		company_currency: str,
# 		accounting_dimensions: list,
# 		precision: int,
# 		payable_amount: float,
# 	):
# 		for entry in self._advance_deduction_entries:
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				entry.get("account"),
# 				entry.get("cost_center"),
# 				entry.get("amount"),
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="credit",
# 				accounts=accounts,
# 				party=entry.get("employee"),
# 				reference_type="Employee Advance",
# 				reference_name=entry.get("reference_name"),
# 				is_advance="Yes",
# 			)

# 		return payable_amount

# 	def set_employee_based_payroll_payable_entries(
# 		self, component_type, employee, amount, salary_structure=None
# 	):

# 		employee_details = self.employee_based_payroll_payable_entries.setdefault(employee, {})
# 		employee_details.setdefault(component_type, 0)
# 		employee_details[component_type] += amount

# 		if salary_structure and "salary_structure" not in employee_details:
# 			employee_details["salary_structure"] = salary_structure

# 	def get_payroll_cost_centers_for_employee(self, employee, salary_structure):
# 		if not hasattr(self, "employee_cost_centers"):
# 			self.employee_cost_centers = {}

# 		if not self.employee_cost_centers.get(employee):
# 			SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
# 			EmployeeCostCenter = frappe.qb.DocType("Employee Cost Center")

# 			cost_centers = dict(
# 				(
# 					frappe.qb.from_(SalaryStructureAssignment)
# 					.join(EmployeeCostCenter)
# 					.on(SalaryStructureAssignment.name == EmployeeCostCenter.parent)
# 					.select(EmployeeCostCenter.cost_center, EmployeeCostCenter.percentage)
# 					.where(
# 						(SalaryStructureAssignment.employee == employee)
# 						& (SalaryStructureAssignment.docstatus == 1)
# 						& (SalaryStructureAssignment.salary_structure == salary_structure)
# 					)
# 				).run(as_list=True)
# 			)

# 			if not cost_centers:
# 				default_cost_center, department = frappe.get_cached_value(
# 					"Employee", employee, ["payroll_cost_center", "department"]
# 				)

# 				if not default_cost_center and department:
# 					default_cost_center = frappe.get_cached_value("Department", department, "payroll_cost_center")

# 				if not default_cost_center:
# 					default_cost_center = self.cost_center

# 				cost_centers = {default_cost_center: 100}

# 			self.employee_cost_centers.setdefault(employee, cost_centers)

# 		return self.employee_cost_centers.get(employee, {})


# # --------------------------------------below is working function in case of ER + EE amounts-----------------------------
# 	# def get_account(self, component_dict=None, employee=None):
# 	# 	account_dict = {}
# 	# 	account_map = {}  # Maps (component, fund, department) to account

# 	# 	# First pass: resolve accounts for all components
# 	# 	for key in component_dict:
# 	# 		component, cost_center, fund, department, employee = key
# 	# 		account = self.get_salary_component_accounts(component, fund, department)
# 	# 		account_map[key] = account

# 	# 	# Second pass: aggregate amounts with deduction logic
# 	# 	for key, amount in component_dict.items():
# 	# 		component, cost_center, fund, department, employee = key
# 	# 		comp_doc = frappe.get_doc("Salary Component", component)
# 	# 		account = account_map[key]

# 	# 		# Deduction logic: check for matching account with opposite do_not_include_in_total
# 	# 		if comp_doc.type == "Deduction":
# 	# 			for other_key, other_account in account_map.items():
# 	# 				if other_key == key:
# 	# 					continue

# 	# 				other_component, _, other_fund, other_department, _ = other_key
# 	# 				if other_fund != fund or other_department != department:
# 	# 					continue

# 	# 				other_doc = frappe.get_doc("Salary Component", other_component)
# 	# 				if other_doc.type == "Deduction" and other_account == account:
# 	# 					if comp_doc.do_not_include_in_total != other_doc.do_not_include_in_total:
# 	# 						# Merge amounts under same accounting key
# 	# 						key = other_key if other_doc.do_not_include_in_total is False else key
# 	# 						break

# 	# 		# Build accounting key
# 	# 		if department:
# 	# 			accounting_key = (account, cost_center, fund, department, employee)
# 	# 		else:
# 	# 			accounting_key = (account, cost_center, fund, employee)

# 	# 		account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

# 	# 	return account_dict


# # 	def get_account(self, component_dict=None):
# # 		account_dict = {}
# # 		for key, amount in component_dict.items():
# # 			component, cost_center = key
# # 			account = self.get_salary_component_accounts(component)
# # 			accounting_key = (account, cost_center)

# # 			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

# # 		return account_dict

# # # --------------------------------------below is working function in case of ER + EE, ER expense separate amounts-----------------------------
# # 	def get_employer_expense_account(self, component_dict=None, employee=None):
# # 		account_dict = {}
# # 		account_map = {}

# # 		# First pass: resolve accounts
# # 		for key in component_dict:
# # 			component, cost_center = key
# # 			account = self.get_salary_component_account(component)
# # 			account_map[key] = account

# # 		# Second pass: aggregate
# # 		for key, amount in component_dict.items():
# # 			component, cost_center = key
# # 			comp_doc = frappe.get_doc("Salary Component", component)
# # 			account_info = account_map[key]

# # 			if isinstance(account_info, dict):
# # 				# Deduction with do_not_include_in_total = True
# # 				liability_account = account_info["liability_account"]
# # 				expense_account = account_info["expense_account"]

# # 				# expense_account gets only ER
# # 				if comp_doc.type == "Deduction" and comp_doc.do_not_include_in_total:
# # 					expense_key = (expense_account, cost_center, employee)
# # 					account_dict[expense_key] = account_dict.get(expense_key, 0) + amount

# # 		return account_dict


# 	def get_account(self, component_dict=None):
# 		account_dict = {}
# 		account_map = {}

# 		# First pass: resolve accounts
# 		for key in component_dict:
# 			component, cost_center = key
# 			account_map[key] = self.get_salary_component_accounts(component)

# 		# Second pass: aggregate with deduction merge logic
# 		for key, amount in component_dict.items():
# 			component, cost_center = key
# 			comp_doc = frappe.get_doc("Salary Component", component)
# 			account = account_map[key]

# 			if comp_doc.type == "Deduction":
# 				for other_key, other_account in account_map.items():
# 					if other_key == key:
# 						continue

# 					other_component, other_cost_center = other_key
# 					if other_cost_center != cost_center:
# 						continue

# 					other_doc = frappe.get_doc("Salary Component", other_component)

# 					if (
# 						other_doc.type == "Deduction"
# 						and other_account == account
# 						and comp_doc.do_not_include_in_total != other_doc.do_not_include_in_total
# 					):
# 						key = (
# 							other_key
# 							if other_doc.do_not_include_in_total is False
# 							else key
# 						)
# 						break

# 			accounting_key = (account, cost_center)
# 			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount



# 		return account_dict


# 	def get_employer_expense_account(self, component_dict=None):
# 		account_dict = {}
# 		account_map = {}

# 		# First pass: resolve accounts
# 		for key in component_dict:
# 			component, cost_center = key
# 			account_map[key] = self.get_salary_component_account(component)

# 		# Second pass: aggregate employer expense only
# 		for key, amount in component_dict.items():
# 			component, cost_center = key
# 			comp_doc = frappe.get_doc("Salary Component", component)
# 			account_info = account_map[key]

# 			if isinstance(account_info, dict):
# 				expense_account = account_info["expense_account"]

# 				if (
# 					comp_doc.type == "Deduction"
# 					and comp_doc.do_not_include_in_total
# 				):
# 					expense_key = (expense_account, cost_center)
# 					account_dict[expense_key] = (
# 						account_dict.get(expense_key, 0) + amount
# 					)

# 		return account_dict


# 	def make_accrual_jv_entry(self, submitted_salary_slips):
# 		self.check_permission("write")
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)
# 		self.employee_based_payroll_payable_entries = {}
# 		self._advance_deduction_entries = []

# 		earnings = (
# 			self.get_salary_component_total(
# 				component_type="earnings",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled			)
# 			or {}
# 		)

# 		deductions = (
# 			self.get_salary_component_total(
# 				component_type="deductions",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled			)
# 			or {}
# 		)


# 		employer_expense = (
# 			self.get_employer_expense(
# 				component_type="deductions",
# 				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
# 				employer_expense = True
# 			)
# 			or {}
# 		)

# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

# 		if earnings or deductions:
# 			accounts = []
# 			currencies = []
# 			payable_amount = 0
# 			accounting_dimensions = get_accounting_dimensions() or []
# 			company_currency = erpnext.get_company_currency(self.company)

# 			for emp in self.employees:
# 				payable_amount = 0
# 				# _earnings = {k:v for k,v in earnings.items() if k[-2] == emp.custom_fund and k[-1] == emp.employee}
# 				# _deductions = {k:v for k,v in deductions.items() if k[-2] == emp.custom_fund and k[-1] == emp.employee}

# 				# _earnings = filter_salary_components(earnings, emp)
# 				# _deductions = filter_salary_components(deductions, emp)
# 				# _employer_expense = filter_salary_components(employer_expense, emp)

# 				_earnings = earnings
# 				_deductions = deductions
# 				_employer_expense = employer_expense

# 				payable_amount = self.get_payable_amount_for_earnings_and_deductions(
# 					accounts,
# 					_earnings,
# 					_deductions,
# 					_employer_expense,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 				)

# 				payable_amount = self.set_accounting_entries_for_advance_deductions(
# 					accounts,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 				)

# 				self.set_payable_amount_against_payroll_payable_account(
# 					accounts,
# 					currencies,
# 					company_currency,
# 					accounting_dimensions,
# 					precision,
# 					payable_amount,
# 					# self.payroll_payable_account,
# 					emp.custom_payroll_payable_account,
# 					employee_wise_accounting_enabled,
# 				)

# 				for ac in accounts:
# 					if "reference_name" in ac and "employee" not in ac:
# 						ac['employee'] = emp.employee
# 						break
			
# 			grouped_accounts = {"bank": [], "check": []}
# 			temp_group = []
# 			current_employee = None

# 			for entry in accounts:
# 				if "employee" in entry:
# 					if temp_group:
# 						current_employee = entry["employee"]
# 						payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method") or "Bank"
# 						if payment_method == "Bank":
# 							temp_group.append(entry)
# 							grouped_accounts["bank"].extend(temp_group)
# 						else:
# 							temp_group.append(entry)
# 							grouped_accounts["check"].append(temp_group)
# 						temp_group = []
					
# 				else:
# 					temp_group.append(entry)


# 			#============================================for bank type entries ======================			
# 			bank_accounts = grouped_accounts["bank"]
# 			bank_type_employees = list(set([_.get('employee') for _ in bank_accounts]))
# 			bank_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in bank_type_employees]

# 			if bank_accounts:

# 				# for slip in bank_salary_slips:
# 				# 	slip_doc = frappe.get_doc("Salary Slip", slip.name)					
# 				# 	cheque_no = slip_doc.custom_check_no or "PY Bank Entry"

# 				cheque_no = None
# 				for slip in bank_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", slip.name)
# 					if slip_doc.custom_check_no:
# 						cheque_no = slip_doc.custom_check_no
# 						break

# 				cheque_no = cheque_no or "PY Bank Entry"

				
# 				self.queue_journal_entry(
# 					bank_accounts,
# 					currencies,
# 					None,
# 					voucher_type="Journal Entry",
# 					custom_check_entry=False,
# 					cheque_date = "",
# 					cheque_no = cheque_no,
# 					user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
# 						self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					submitted_salary_slips=bank_salary_slips,
# 				)

# 			#==========================for check entries===========================
# 			check_accounts = grouped_accounts["check"]

# 			if check_accounts:

# 				check_type_employees = []

# 				for ch_acc in check_accounts:
# 					# check_type_employees = []
# 					emp =""
# 					for c_a in ch_acc:

# 						emp = c_a.get("employee")

# 						if emp and emp not in check_type_employees:
# 							check_type_employees.append(c_a.get("employee"))

# 					check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 					cur_salary_slip = [sal_slip for sal_slip in check_salary_slips if sal_slip.employee == emp]
# 					if cur_salary_slip:
# 						cur_salary_slip = cur_salary_slip[0]
					
# 					cheque_no = cur_salary_slip.custom_check_no or "PY Bank Entry"
					
# 					self.queue_journal_entry(
# 						ch_acc,
# 						currencies,
# 						None,
# 						voucher_type="Journal Entry",
# 						custom_check_entry=False,
# 						cheque_date = "",
# 						user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
# 							self.start_date, self.end_date
# 						),
# 						submit_journal_entry=True,
# 						submitted_salary_slips=check_salary_slips,
# 						cheque_no = cheque_no,
# 					)

# 	def create_payment_entries_by_method(self):
# 		bank_employees = []
# 		check_employees = []

# 		for emp_row in self.employees:
# 			custom_method = frappe.db.get_value("Employee", emp_row.employee, "custom_payment_method")
# 			if custom_method == "Bank":
# 				bank_employees.append(emp_row.employee)
# 			elif custom_method == "Check":
# 				check_employees.append(emp_row.employee)

# 		# Handle bank employees with one JV
# 		if bank_employees:
# 			self.create_bank_entry_for_employees(bank_employees)

# 		# Handle check employees with separate JVs
# 		for emp in check_employees:
# 			self.create_check_entry_for_employee(emp)


# 	def queue_journal_entry(
# 		self,
# 		accounts,
# 		currencies,
# 		payroll_payable_account=None,
# 		voucher_type="Journal Entry",
# 		custom_check_entry=False,
# 		cheque_date="",
# 		user_remark="",
# 		submitted_salary_slips=None,
# 		submit_journal_entry=False,
# 		cheque_no=None,
# 	):
# 		logger.info(
# 			f"[JV QUEUE] Payroll Entry={self.name}, "
# 			f"Voucher={voucher_type}, "
# 			f"Accounts={len(accounts)}"
# 		)

# 		frappe.enqueue(
# 			"us_payroll.override.payroll_entry.enqueue_make_journal_entry",
# 			queue="long",               # ✅ IMPORTANT
# 			timeout=3600,
# 			docname=self.name,
# 			accounts=accounts,
# 			currencies=currencies,
# 			payroll_payable_account=payroll_payable_account,
# 			voucher_type=voucher_type,
# 			custom_check_entry=custom_check_entry,
# 			cheque_date=cheque_date,
# 			user_remark=user_remark,
# 			submitted_salary_slips=submitted_salary_slips,
# 			submit_journal_entry=submit_journal_entry,
# 			cheque_no=cheque_no,
# 		)

# 		frappe.msgprint(
# 			_("Journal Entry creation started in background."),
# 			alert=True,
# 			indicator="blue",
# 		)


# 	def make_journal_entry(
# 		self,
# 		accounts,
# 		currencies,
# 		payroll_payable_account=None,
# 		voucher_type="Journal Entry",
# 		custom_check_entry=False,
# 		cheque_date = "",
# 		user_remark="",
# 		submitted_salary_slips: list = None,
# 		submit_journal_entry=False,
# 		cheque_no = None,
# 	):

# 		if voucher_type == "Journal Entry":
# 			payable_amount = 0
# 			payable_amount_dict = {}
# 			for acc in accounts:
# 				if "reference_name" in acc:
# 					payable_amount = acc.get("credit_in_account_currency")
# 					payable_amount_dict[(acc['employee'])] = payable_amount

# 			fund_account_mapping = {}

# 			bank_employees = []
# 			check_employees = []

# 			# payroll's account from Fund Setting
# 			for row in self.employees:	
# 				employee = row.employee
				
# 				if not (row.employee) in payable_amount_dict:
# 					continue

# 				payroll_config_accounts = frappe.get_all("Payroll Accounts Config", 
# 								filters={"parent": "Payroll Config"}, 
# 								fields=["due_to_account", "due_from_account"])


# 				if payroll_config_accounts:
					
# 					due_from_account = payroll_config_accounts[0].get("due_from_account")
# 					due_to_account = payroll_config_accounts[0].get("due_to_account")

# 					acc_doc = frappe.get_doc("Account",{"name":due_from_account})
# 					due_from_account_name = f"{acc_doc.account_name} fund {fund_value}"

# 					if due_from_account and due_to_account:
# 						accounts.append({
# 							'account': due_from_account, 
# 							'custom_account_number': due_from_account_name, 
# 							'exchange_rate': 1.0, 
# 							# 'cost_center': 'Main - RL', 
# 							'cost_center': '',
# 							'project': None, 
# 							# 'debit_in_account_currency': payable_amount_dict[fund_value], 
# 							'debit_in_account_currency': payable_amount_dict[(row.employee)], 
# 							'fund': fund_value
# 						})

# 						accounts.append({
# 							'account': due_to_account, 
# 							'exchange_rate': 1.0, 
# 							# 'cost_center': 'Main - RL', 
# 							'cost_center': '', 
# 							'project': None, 
# 							# 'credit_in_account_currency': payable_amount_dict[fund_value], 
# 							'credit_in_account_currency': payable_amount_dict[(row.employee)],
# 							'fund': fund_value
# 						})


# 				else:				
# 					site_url = get_url()
# 					payroll_config_url = f"{site_url}/desk/payroll-config"

# 					frappe.throw(f"Please add Payroll Accounts in <b>Payroll Accounts Config</b> table in <a href= '{payroll_config_url}' >Payroll Config</a>")


# 		multi_currency = 0
# 		if len(currencies) > 1:
# 			multi_currency = 1

# 		journal_entry = frappe.new_doc("Journal Entry")
# 		journal_entry.voucher_type = voucher_type
# 		journal_entry.user_remark = user_remark
# 		journal_entry.company = self.company
# 		journal_entry.posting_date = self.posting_date
# 		journal_entry.cheque_date = self.posting_date
		
# 		if cheque_no:
# 			journal_entry.cheque_no = cheque_no
		
# 		journal_entry.custom_is_inter_fund_transaction = False
# 		# journal_entry.cheque_date = cheque_date
# 		journal_entry.custom_check_entry = custom_check_entry

# 		journal_entry.set("accounts", accounts)
# 		journal_entry.multi_currency = multi_currency

# 		journal_entry.save(ignore_permissions=True)
		
# 		if voucher_type == "Journal Entry":
# 			journal_entry.title = journal_entry.name

# 		if voucher_type == "Bank Entry":
# 			journal_entry.title = journal_entry.name


# 		journal_entry.save(ignore_permissions=True)

# 		try:
# 			if submit_journal_entry:
# 				journal_entry.submit()

# 			if submitted_salary_slips:
# 				self.update_salary_slip_status(submitted_salary_slips, jv_name=journal_entry.name)

# 		except Exception as e:
# 			if type(e) in (str, list, tuple):
# 				frappe.msgprint(e)

# 			self.log_error("Journal Entry creation against Salary Slip failed")
# 			raise

# 	def get_payable_amount_for_earnings_and_deductions(
# 		self,
# 		accounts,
# 		earnings,
# 		deductions,
# 		employer_expense,
# 		currencies,
# 		company_currency,
# 		accounting_dimensions,
# 		precision,
# 		payable_amount,
# 	):
# 		# Earnings
# 		for acc_cc, amount in earnings.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="debit",
# 				accounts=accounts,
# 			)

# 		# Deductions
# 		for acc_cc, amount in deductions.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="credit",
# 				accounts=accounts,
# 			)

# 		# Employer Expense
# 		for acc_cc, amount in employer_expense.items():
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				acc_cc[0],
# 				acc_cc[1] or self.cost_center,
# 				amount,
# 				currencies,
# 				company_currency,
# 				payable_amount,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="debit",
# 				accounts=accounts,
# 			)

# 		return payable_amount

# 	def set_payable_amount_against_payroll_payable_account(
# 		self,
# 		accounts,
# 		currencies,
# 		company_currency,
# 		accounting_dimensions,
# 		precision,
# 		payable_amount,
# 		payroll_payable_account,
# 		employee_wise_accounting_enabled,
# 	):
# 		# Payable amount
# 		if employee_wise_accounting_enabled:
# 			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
# 				payable_amount = employee_details.get("earnings", 0) - employee_details.get("deductions", 0)

# 				payable_amount = self.get_accounting_entries_and_payable_amount(
# 					payroll_payable_account,
# 					self.cost_center,
# 					payable_amount,
# 					currencies,
# 					company_currency,
# 					0,
# 					accounting_dimensions,
# 					precision,
# 					entry_type="payable",
# 					party=employee,
# 					accounts=accounts,
# 				)
# 		else:
# 			payable_amount = self.get_accounting_entries_and_payable_amount(
# 				payroll_payable_account,
# 				self.cost_center,
# 				payable_amount,
# 				currencies,
# 				company_currency,
# 				0,
# 				accounting_dimensions,
# 				precision,
# 				entry_type="payable",
# 				accounts=accounts,
# 			)

# 	def get_accounting_entries_and_payable_amount(
# 		self,
# 		account,
# 		cost_center,
# 		amount,
# 		currencies,
# 		company_currency,
# 		payable_amount,
# 		accounting_dimensions,
# 		precision,
# 		entry_type="credit",
# 		party=None,
# 		accounts=None,
# 		reference_type=None,
# 		reference_name=None,
# 		is_advance=None,
# 	):

# 		exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
# 			account, amount, company_currency, currencies
# 		)

# 		row = {
# 			"account": account,
# 			"exchange_rate": flt(exchange_rate),
# 			"cost_center": cost_center,
# 			"project": self.project,
# 		}

# 		if entry_type == "debit":
# 			payable_amount += flt(amount, precision)
# 			row.update(
# 				{
# 					"debit_in_account_currency": flt(amt, precision),
# 				}
# 			)
# 		elif entry_type == "credit":
# 			payable_amount -= flt(amount, precision)
# 			row.update(
# 				{
# 					"credit_in_account_currency": flt(amt, precision),
# 				}
# 			)
# 		else:
# 			row.update(
# 				{
# 					"credit_in_account_currency": flt(amt, precision),
# 					"reference_type": self.doctype,
# 					"reference_name": self.name,
# 				}
# 			)

# 		if party:
# 			row.update(
# 				{
# 					"party_type": "Employee",
# 					"party": party,
# 				}
# 			)

# 		if reference_type:
# 			row.update(
# 				{
# 					"reference_type": reference_type,
# 					"reference_name": reference_name,
# 					"is_advance": is_advance,
# 				}
# 			)

# 		self.update_accounting_dimensions(
# 			row,
# 			accounting_dimensions,
# 		)

# 		if amt:
# 			accounts.append(row)

# 		return payable_amount

# 	def update_accounting_dimensions(self, row, accounting_dimensions):
# 		for dimension in accounting_dimensions:
# 			row.update({dimension: self.get(dimension)})

# 		return row

# 	def get_amount_and_exchange_rate_for_journal_entry(
# 		self, account, amount, company_currency, currencies
# 	):
# 		conversion_rate = 1
# 		exchange_rate = self.exchange_rate
# 		account_currency = frappe.db.get_value("Account", account, "account_currency")

# 		if account_currency not in currencies:
# 			currencies.append(account_currency)

# 		if account_currency == company_currency:
# 			conversion_rate = self.exchange_rate
# 			exchange_rate = 1

# 		amount = flt(amount) * flt(conversion_rate)

# 		return exchange_rate, amount


# 	def get_amount_and_exchange_rate_for_bank_entry(
# 		self, account, employee_amount_mapping, company_currency, currencies
# 	):
# 		# Dictionary to store exchange rate and amount for each employee
# 		employee_exchange_rate_amount = {}

# 		account_currency = frappe.db.get_value("Account", account, "account_currency")

# 		if account_currency not in currencies:
# 			currencies.append(account_currency)

# 		for employee, amount in employee_amount_mapping.items():
# 			# Initialize conversion_rate and exchange_rate
# 			conversion_rate = 1
# 			exchange_rate = self.exchange_rate

# 			if account_currency == company_currency:
# 				conversion_rate = self.exchange_rate
# 				exchange_rate = 1

# 			# Calculate the amount for this employee
# 			employee_amount = flt(amount) * flt(conversion_rate)

# 			# Store the exchange rate and calculated amount for the employee
# 			# employee_exchange_rate_amount[employee] = {
# 			# 	'exchange_rate': exchange_rate,
# 			# 	'amount': employee_amount
# 			# }

# 			employee_exchange_rate_amount[employee] = employee_amount
# 		return exchange_rate, employee_exchange_rate_amount


# 	@frappe.whitelist()
# 	def make_bank_entry(self):
# 		self.check_permission("write")
# 		self.employee_based_payroll_payable_entries = {}
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)

# 		employee_totals = {}
# 		total_net_salary = {}

# 		salary_slips = self.get_salary_slip_details()
# 		for salary_detail in salary_slips:
# 			employee = salary_detail.employee

# 			if employee not in employee_totals:
# 				employee_totals[employee] = 0

# 			if employee not in total_net_salary:
# 				total_net_salary[employee] = 0

# 			if salary_detail.parentfield == "earnings":
# 				(
# 					is_flexible_benefit,
# 					custom_only_tax_impact,
# 					create_separate_je,
# 					statistical_component,
# 				) = frappe.db.get_value(
# 					"Salary Component",
# 					salary_detail.salary_component,
# 					(
# 						"is_flexible_benefit",
# 						"custom_only_tax_impact",
# 						"custom_create_separate_payment_entry_against_benefit_claim",
# 						"statistical_component",
# 					),
# 					cache=True,
# 				)

# 				if custom_only_tax_impact != 1 and statistical_component != 1:
# 					if is_flexible_benefit == 1 and create_separate_je == 1:
# 						self.set_accounting_entries_for_bank_entry(
# 							salary_detail.amount, salary_detail.salary_component
# 						)
# 					else:
# 						if employee_wise_accounting_enabled:
# 							self.set_employee_based_payroll_payable_entries(
# 								"earnings",
# 								salary_detail.employee,
# 								salary_detail.amount,
# 								salary_detail.salary_structure,
# 							)
						
# 						total_net_salary[employee] += salary_detail.amount
# 			if salary_detail.parentfield == "deductions":
# 				statistical_component = frappe.db.get_value(
# 					"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 				)

# 				if not statistical_component:
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							"deductions",
# 							salary_detail.employee,
# 							salary_detail.amount,
# 							salary_detail.salary_structure,
# 						)
# 					total_net_salary[employee] -= salary_detail.amount

# 					comp_doc = frappe.get_doc("Salary Component", salary_detail.salary_component)
# 					if comp_doc.do_not_include_in_total:
# 						total_net_salary[employee] += salary_detail.amount

# 		total_salary_slip_amount = sum(total_net_salary.values())
# 		employer_salary_slip_amount = sum(total_net_salary.values())
# 		salary_slip_amount_totals = total_salary_slip_amount + employer_salary_slip_amount
# 		if salary_slip_amount_totals > 0:
# 			self.set_accounting_entries_for_bank_entry(total_net_salary, "salary")


# 	@frappe.whitelist()
# 	def make_check_entry(self):
# 		self.check_permission("write")
# 		self.employee_based_payroll_payable_entries = {}
# 		employee_wise_accounting_enabled = frappe.db.get_single_value(
# 			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
# 		)

# 		employee_totals = {}
# 		total_net_salary = {}

# 		salary_slips = self.get_salary_slip_details()
# 		for salary_detail in salary_slips:
# 			employee = salary_detail.employee

# 			if employee not in employee_totals:
# 				employee_totals[employee] = 0

# 			if employee not in total_net_salary:
# 				total_net_salary[employee] = 0

# 			if salary_detail.parentfield == "earnings":
# 				(
# 					is_flexible_benefit,
# 					custom_only_tax_impact,
# 					create_separate_je,
# 					statistical_component,
# 				) = frappe.db.get_value(
# 					"Salary Component",
# 					salary_detail.salary_component,
# 					(
# 						"is_flexible_benefit",
# 						"custom_only_tax_impact",
# 						"custom_create_separate_payment_entry_against_benefit_claim",
# 						"statistical_component",
# 					),
# 					cache=True,
# 				)

# 				if custom_only_tax_impact != 1 and statistical_component != 1:
# 					if is_flexible_benefit == 1 and create_separate_je == 1:
# 						self.set_accounting_entries_for_bank_entry(
# 							salary_detail.amount, salary_detail.salary_component
# 						)
# 					else:
# 						if employee_wise_accounting_enabled:
# 							self.set_employee_based_payroll_payable_entries(
# 								"earnings",
# 								salary_detail.employee,
# 								salary_detail.amount,
# 								salary_detail.salary_structure,
# 							)
# 						total_net_salary[employee] += salary_detail.amount
# 			if salary_detail.parentfield == "deductions":
# 				statistical_component = frappe.db.get_value(
# 					"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
# 				)

# 				if not statistical_component:
# 					if employee_wise_accounting_enabled:
# 						self.set_employee_based_payroll_payable_entries(
# 							"deductions",
# 							salary_detail.employee,
# 							salary_detail.amount,
# 							salary_detail.salary_structure,
# 						)
# 					total_net_salary[employee] -= salary_detail.amount

# 					comp_doc = frappe.get_doc("Salary Component", salary_detail.salary_component)
# 					if comp_doc.do_not_include_in_total:
# 						total_net_salary[employee] += salary_detail.amount

# 		total_salary_slip_amount = sum(total_net_salary.values())
# 		employer_salary_slip_amount = sum(total_net_salary.values())
# 		salary_slip_amount_totals = total_salary_slip_amount + employer_salary_slip_amount
# 		if salary_slip_amount_totals > 0:
# 			self.set_accounting_entries_for_check_entry(total_net_salary, "salary")


# 	def get_salary_slip_details(self):
# 		SalarySlip = frappe.qb.DocType("Salary Slip")
# 		SalaryDetail = frappe.qb.DocType("Salary Detail")

# 		return (
# 			frappe.qb.from_(SalarySlip)
# 			.join(SalaryDetail)
# 			.on(SalarySlip.name == SalaryDetail.parent)
# 			.select(
# 				SalarySlip.name,
# 				SalarySlip.employee,
# 				SalarySlip.salary_structure,
# 				SalaryDetail.salary_component,
# 				SalaryDetail.amount,
# 				SalaryDetail.parentfield,
# 			)
# 			.where(
# 				(SalarySlip.docstatus == 1)
# 				& (SalarySlip.start_date >= self.start_date)
# 				& (SalarySlip.end_date <= self.end_date)
# 				& (SalarySlip.payroll_entry == self.name)
# 			)
# 		).run(as_dict=True)


# 	def set_accounting_entries_for_bank_entry(self, je_payment_amount, user_remark):
# 		payroll_payable_account = self.payroll_payable_account
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

# 		accounts = []
# 		currencies = []
# 		company_currency = erpnext.get_company_currency(self.company)
# 		accounting_dimensions = get_accounting_dimensions() or []

# 		# Payroll Bank Cash Accounts Config from Fund Setting	
# 		for row in self.employees:
# 			employee = row.employee

# 			common_account_for_bank_entry = frappe.get_all("Payroll Accounts Config", 
# 							filters={"parent": "Payroll Config",}, 
# 							fields=["due_from_account"])

# 			for common_acc in common_account_for_bank_entry:
# 				common_account = common_acc.get("due_from_account")

# 				acc_doc = frappe.get_doc("Account",{"name":common_account})
# 				due_from_account_name = f"{acc_doc.account_name}"

# 				common_cash_account_for_bank_entry = frappe.get_value("Payroll Bank Cash Accounts Config", 
# 					{"parent": "Payroll Config"}, "account")

# 			fund_setting_accounts_for_bank_entry = frappe.get_all("Payroll Bank Cash Accounts Config", 
# 							filters={"parent": "Payroll Config"}, fields=["account"])

# 			if fund_setting_accounts_for_bank_entry:				
# 				bank_cash_account = fund_setting_accounts_for_bank_entry[0].get("account")
# 				if bank_cash_account:
# 					exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 						bank_cash_account, je_payment_amount, company_currency, currencies
# 					)
				
# 					for emp,amount in emplyee_amount_mapping.items():
# 						if emp == row.employee:
# 							emp_amount = amount
					
# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": bank_cash_account,
# 										"bank_account": self.bank_account,
# 										"credit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"employee":row.employee
# 									},
# 									accounting_dimensions,
# 								)
# 							)

# 					if self.employee_based_payroll_payable_entries:
# 						for employee, employee_details in self.employee_based_payroll_payable_entries.items():
# 							je_payment_amount = employee_details.get("earnings", 0) - (
# 								employee_details.get("deductions", 0)
# 							)
							
# 							exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 								bank_cash_account, je_payment_amount, company_currency, currencies
# 							)

# 							cost_centers = self.get_payroll_cost_centers_for_employee(
# 								employee, employee_details.get("salary_structure")
# 							)

# 							for cost_center, percentage in cost_centers.items():
# 								for emp,amount in emplyee_amount_mapping.items():
# 									if emp == row.employee:
# 										emp_amount = amount
# 										amount_against_cost_center = flt(emp_amount) * percentage / 100
# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": row.custom_payroll_payable_account,
# 													"debit_in_account_currency": flt(amount_against_cost_center, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"reference_type": self.doctype,
# 													"reference_name": self.name,
# 													"party_type": "Employee",
# 													"party": employee,
# 													"cost_center": cost_center,
# 													# "fund": fund
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": common_account,
# 													"custom_account_number": due_from_account_name,
# 													"bank_account": self.bank_account,
# 													"credit_in_account_currency": flt(emp_amount, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"cost_center": self.cost_center,
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 										accounts.append(
# 											self.update_accounting_dimensions(
# 												{
# 													"account": common_cash_account_for_bank_entry,
# 													"bank_account": self.bank_account,
# 													"debit_in_account_currency": flt(emp_amount, precision),
# 													"exchange_rate": flt(exchange_rate),
# 													"cost_center": self.cost_center,
# 												},
# 												accounting_dimensions,
# 											)
# 										)

# 					else:
# 						exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 							bank_cash_account, je_payment_amount, company_currency, currencies
# 						)

# 						for emp,amount in emplyee_amount_mapping.items():
# 							if emp == row.employee:
# 								emp_amount = amount
								
# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": row.custom_payroll_payable_account,
# 											"debit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"reference_type": self.doctype,
# 											"reference_name": self.name,
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)

# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": common_account,
# 											"custom_account_number": due_from_account_name,
# 											"bank_account": self.bank_account,
# 											"credit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)

# 								accounts.append(
# 									self.update_accounting_dimensions(
# 										{
# 											"account": common_cash_account_for_bank_entry,
# 											"bank_account": self.bank_account,
# 											"debit_in_account_currency": flt(emp_amount, precision),
# 											"exchange_rate": flt(exchange_rate),
# 											"cost_center": self.cost_center,
# 											"employee":row.employee
# 										},
# 										accounting_dimensions,
# 									)
# 								)			

# 			else:				
# 				site_url = get_url()
# 				payroll_config_url = f"{site_url}/desk/payroll-config"
# 				frappe.throw(f"Please add Payroll Bank/Cash Accounts in <b>Payroll Bank Cash Accounts Config</b> table in <a href= '{payroll_config_url}' >Payroll Config</a>")

# 		# -------------------------------------------------------------------------------------------------

# 		grouped_accounts = {"bank": [], "check": []}
# 		temp_group = []
# 		current_employee = None

# 		for entry in accounts:			
# 			current_employee = entry["employee"]
# 			payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method")
# 			if payment_method == "Bank":
# 				grouped_accounts["bank"].append(entry)
# 			else:
# 				temp_group.append(entry)
# 				grouped_accounts["check"].append(entry)
					
# 		#for bank type entry 
# 		bank_accounts = grouped_accounts["bank"]
# 		if bank_accounts:
# 			# # Default cheque_no for Bank Entry
# 			cheque_no = "PY Bank Entry"

# 			self.queue_journal_entry(
# 				bank_accounts,
# 				currencies,
# 				voucher_type="Bank Entry",
# 				custom_check_entry=False,
# 				cheque_date = self.posting_date,
# 				user_remark=_("Payment of {0} from {1} to {2}").format(
# 					user_remark, self.start_date, self.end_date
# 				),
# 				submit_journal_entry=True,
# 				cheque_no = cheque_no,
# 			)

# 		#for check type entryes -------------------------------------------------------------
# 		submitted_salary_slips = frappe.db.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["name"])	

# 		check_accounts = grouped_accounts["check"]
# 		if check_accounts:
# 			grouped_by_employee = defaultdict(list)
# 			for entry in check_accounts:
# 				grouped_by_employee[entry['employee']].append(entry)
			
# 			grouped_by_employee = dict(grouped_by_employee)
# 			check_type_employees = []
# 			for emp, ch_acc in grouped_by_employee.items():
# 				if emp and emp not in check_type_employees:
# 						check_type_employees.append(emp)

# 				# check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 				check_salary_slip_check_no = []
# 				current_salary_slip = []
# 				for sl in submitted_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", sl.get("name"))

# 					if slip_doc.employee in check_type_employees and slip_doc.employee == emp:

# 						check_salary_slip_check_no.append(slip_doc.custom_check_no)				

# 				if check_salary_slip_check_no:
# 					check_salary_slip_check_no = check_salary_slip_check_no[0]
				
# 				cheque_no = check_salary_slip_check_no or "PY Bank Entry"
# 				self.queue_journal_entry(
# 					ch_acc,
# 					currencies,
# 					voucher_type="Bank Entry",
# 					custom_check_entry=False,
# 					cheque_date = self.posting_date,
# 					user_remark=_("Payment of {0} from {1} to {2}").format(
# 						user_remark, self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					cheque_no = cheque_no,
# 				)

# 	def set_accounting_entries_for_check_entry(self, je_payment_amount, user_remark):
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
# 		accounts = []
# 		currencies = []
# 		company_currency = erpnext.get_company_currency(self.company)
# 		accounting_dimensions = get_accounting_dimensions() or []

# 		# Payroll Bank Cash Accounts Config from Fund Setting
# 		for row in self.employees:
# 			fund_value = row.custom_fund
# 			employee = row.employee
# 			common_account_for_bank_entry = frappe.get_all("Payroll Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "due_to_account"])

# 			for common_acc in common_account_for_bank_entry:
# 				common_account = common_acc.get("due_to_account")

# 				acc_doc = frappe.get_doc("Account",{"name":common_account})
# 				due_to_account_name = f"{acc_doc.account_name} fund {fund_value}"

# 				common_fund = acc_doc.custom_fund

# 				common_cash_account_for_bank_entry = frappe.get_value("Payroll Bank Cash Accounts Config", 
# 					{"parent": "Fund Settings", "fund": common_fund}, 
# 					"account")

# 			fund_setting_accounts_for_bank_entry = frappe.get_all("Payroll Bank Cash Accounts Config", 
# 							filters={"parent": "Fund Settings", "fund":fund_value}, 
# 							fields=["fund", "account"])

# 			if fund_setting_accounts_for_bank_entry:				
# 				bank_cash_account = fund_setting_accounts_for_bank_entry[0].get("account")
# 				if bank_cash_account:
# 					exchange_rate, emplyee_amount_mapping = self.get_amount_and_exchange_rate_for_bank_entry(
# 						bank_cash_account, je_payment_amount, company_currency, currencies
# 					)
				
# 					for emp,amount in emplyee_amount_mapping.items():
# 						if emp == row.employee:
# 							emp_amount = amount

# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": common_account,
# 										"custom_account_number": due_to_account_name,
# 										"bank_account": self.bank_account,
# 										"debit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"reference_type" : 'Payroll Entry',
# 										"reference_name" : self.name,
# 										"employee":row.employee

# 									},
# 									accounting_dimensions,
# 								)
# 							)

# 							accounts.append(
# 								self.update_accounting_dimensions(
# 									{
# 										"account": common_cash_account_for_bank_entry,
# 										"bank_account": self.bank_account,
# 										"credit_in_account_currency": flt(emp_amount, precision),
# 										"exchange_rate": flt(exchange_rate),
# 										"cost_center": self.cost_center,
# 										"employee":row.employee
# 									},
# 									accounting_dimensions,
# 								)
# 							)			

# 			else:				
# 				site_url = get_url()
# 				fund_settings_url = f"{site_url}/app/fund-settings/Fund%20Settings"

# 				frappe.throw(f"Please add Payroll Bank/Cash Accounts for fund <b>{fund_value}</b> in <b>Payroll Bank Cash Accounts Config</b> table in <a href= '{fund_settings_url}' >Fund Settings</a>")			

# 		# -------------------------------------------------------------------------------------------------
# 		grouped_accounts = {"bank": [], "check": []}
# 		temp_group = []
# 		current_employee = None

# 		for entry in accounts:			
# 			current_employee = entry["employee"]
# 			payment_method = frappe.db.get_value("Employee", current_employee, "custom_payment_method")
# 			if payment_method == "Bank":
# 				grouped_accounts["bank"].append(entry)
# 			else:
# 				temp_group.append(entry)
# 				grouped_accounts["check"].append(entry)
		
# 		#for bank type entry 
# 		bank_accounts = grouped_accounts["bank"]
# 		if bank_accounts:
# 			# # Default cheque_no for Bank Entry
# 			cheque_no = "PY Bank Entry"

# 			self.queue_journal_entry(
# 				bank_accounts,
# 				currencies,
# 				voucher_type="Bank Entry",
# 				custom_check_entry=True,
# 				cheque_date = self.posting_date,
# 				user_remark=_("Payment of {0} from {1} to {2}").format(
# 					user_remark, self.start_date, self.end_date
# 				),
# 				submit_journal_entry=True,
# 				cheque_no = cheque_no,
# 			)

# 		##for check type entryes --------------------------------------------------------------------------------

# 		submitted_salary_slips = frappe.db.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["name"])
# 		check_accounts = grouped_accounts["check"]
# 		if check_accounts:
# 			grouped_by_employee = defaultdict(list)
# 			for entry in check_accounts:
# 				grouped_by_employee[entry['employee']].append(entry)
			
# 			grouped_by_employee = dict(grouped_by_employee)
# 			check_type_employees = []

# 			for emp, ch_acc in grouped_by_employee.items():
# 				if emp and emp not in check_type_employees:
# 						check_type_employees.append(emp)

# 				# check_salary_slips  = [_ for _ in submitted_salary_slips if _.employee in check_type_employees]

# 				check_salary_slip_check_no = []
# 				current_salary_slip = []
# 				for sl in submitted_salary_slips:
# 					slip_doc = frappe.get_doc("Salary Slip", sl.get("name"))
# 					if slip_doc.employee in check_type_employees and slip_doc.employee == emp:

# 						# check_salary_slips.append(sl.get("name"))

# 						check_salary_slip_check_no.append(slip_doc.custom_check_no)				

# 				if check_salary_slip_check_no:
# 					check_salary_slip_check_no = check_salary_slip_check_no[0]
				
# 				cheque_no = check_salary_slip_check_no or "PY Bank Entry"

# 				self.queue_journal_entry(
# 					ch_acc,
# 					currencies,
# 					voucher_type="Bank Entry",
# 					custom_check_entry=True,
# 					cheque_date = self.posting_date,
# 					user_remark=_("Payment of {0} from {1} to {2}").format(
# 						user_remark, self.start_date, self.end_date
# 					),
# 					submit_journal_entry=True,
# 					cheque_no = cheque_no,
# 				)


# 	def update_salary_slip_status(self, submitted_salary_slips, jv_name=None):
# 		SalarySlip = frappe.qb.DocType("Salary Slip")
# 		(
# 			frappe.qb.update(SalarySlip)
# 			.set(SalarySlip.journal_entry, jv_name)
# 			.where(SalarySlip.name.isin([salary_slip.name for salary_slip in submitted_salary_slips]))
# 		).run()

# 	def set_start_end_dates(self):
# 		self.update(
# 			get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company)
# 		)

# 	@frappe.whitelist()
# 	def get_employees_with_unmarked_attendance(self) -> list[dict] | None:
# 		if not self.validate_attendance:
# 			return

# 		unmarked_attendance = []
# 		employee_details = self.get_employee_and_attendance_details()
# 		default_holiday_list = frappe.db.get_value(
# 			"Company", self.company, "default_holiday_list", cache=True
# 		)

# 		for emp in self.employees:
# 			details = next((record for record in employee_details if record.name == emp.employee), None)
# 			if not details:
# 				continue

# 			start_date, end_date = self.get_payroll_dates_for_employee(details)
# 			holidays = self.get_holidays_count(
# 				details.holiday_list or default_holiday_list, start_date, end_date
# 			)
# 			payroll_days = date_diff(end_date, start_date) + 1
# 			unmarked_days = payroll_days - (holidays + details.attendance_count)

# 			if unmarked_days > 0:
# 				unmarked_attendance.append(
# 					{"employee": emp.employee, "employee_name": emp.employee_name, "unmarked_days": unmarked_days}
# 				)

# 		return unmarked_attendance

# 	def get_employee_and_attendance_details(self) -> list[dict]:
# 		"""Returns a list of employee and attendance details like
# 		[
# 				{
# 						"name": "HREMP00001",
# 						"date_of_joining": "2019-01-01",
# 						"relieving_date": "2022-01-01",
# 						"holiday_list": "Holiday List Company",
# 						"attendance_count": 22
# 				}
# 		]
# 		"""
# 		employees = [emp.employee for emp in self.employees]

# 		Employee = frappe.qb.DocType("Employee")
# 		Attendance = frappe.qb.DocType("Attendance")

# 		return (
# 			frappe.qb.from_(Employee)
# 			.left_join(Attendance)
# 			.on(
# 				(Employee.name == Attendance.employee)
# 				& (Attendance.attendance_date.between(self.start_date, self.end_date))
# 				& (Attendance.docstatus == 1)
# 			)
# 			.select(
# 				Employee.name,
# 				Employee.date_of_joining,
# 				Employee.relieving_date,
# 				Employee.holiday_list,
# 				Count(Attendance.name).as_("attendance_count"),
# 			)
# 			.where(Employee.name.isin(employees))
# 			.groupby(Employee.name)
# 		).run(as_dict=True)

# 	def get_payroll_dates_for_employee(self, employee_details: dict) -> tuple[str, str]:
# 		start_date = self.start_date
# 		if employee_details.date_of_joining > getdate(self.start_date):
# 			start_date = employee_details.date_of_joining

# 		end_date = self.end_date
# 		if employee_details.relieving_date and employee_details.relieving_date < getdate(self.end_date):
# 			end_date = employee_details.relieving_date

# 		return start_date, end_date

# 	def get_holidays_count(self, holiday_list: str, start_date: str, end_date: str) -> float:
# 		"""Returns number of holidays between start and end dates in the holiday list"""
# 		if not hasattr(self, "_holidays_between_dates"):
# 			self._holidays_between_dates = {}

# 		key = f"{start_date}-{end_date}-{holiday_list}"
# 		if key in self._holidays_between_dates:
# 			return self._holidays_between_dates[key]

# 		holidays = frappe.db.get_all(
# 			"Holiday",
# 			filters={"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])},
# 			fields=["COUNT(*) as holidays_count"],
# 		)[0]

# 		if holidays:
# 			self._holidays_between_dates[key] = holidays.holidays_count

# 		return self._holidays_between_dates.get(key) or 0


# 	def create_bank_entry_for_employees(self, employees):
# 		frappe.msgprint(_("Creating one Bank JV for Bank employees: {0}").format(", ".join(employees)))
# 		self.employees = [row for row in self.employees if row.employee in employees]
# 		self.make_bank_entry()

# 	def create_check_entry_for_employee(self, employee):
# 		frappe.msgprint(_("Creating Check JV for {0}").format(employee))
# 		self.employees = [row for row in self.employees if row.employee == employee]
# 		self.make_check_entry()

# 	@frappe.whitelist()
# 	def enqueue_make_accrual_jv(self):
# 		"""
# 		Lightweight request method.
# 		Only enqueues background job.
# 		"""

# 		self.check_permission("write")

# 		# self.db_set("status", "Queued")
# 		self.db_set("status", "Submitted")

# 		frappe.enqueue(
# 			"us_payroll.override.payroll_entry.process_accrual_jv",
# 			queue="long",
# 			timeout=7200,
# 			payroll_entry_name=self.name,
# 			enqueue_after_commit=True,   # ✅ THIS FIXES IT
# 		)

# 		frappe.msgprint(
# 			_("Accrual Journal Entry creation is queued and running in background."),
# 			indicator="blue",
# 			alert=True,
# 		)

	

# def get_salary_structure(
# 	company: str, currency: str, salary_slip_based_on_timesheet: int, payroll_frequency: str
# ) -> list[str]:
# 	SalaryStructure = frappe.qb.DocType("Salary Structure")

# 	query = (
# 		frappe.qb.from_(SalaryStructure)
# 		.select(SalaryStructure.name)
# 		.where(
# 			(SalaryStructure.docstatus == 1)
# 			& (SalaryStructure.is_active == "Yes")
# 			& (SalaryStructure.company == company)
# 			& (SalaryStructure.currency == currency)
# 			& (SalaryStructure.salary_slip_based_on_timesheet == salary_slip_based_on_timesheet)
# 		)
# 	)

# 	if not salary_slip_based_on_timesheet:
# 		query = query.where(SalaryStructure.payroll_frequency == payroll_frequency)

# 	return query.run(pluck=True)


# def get_filtered_employees(
# 	sal_struct,
# 	filters,
# 	searchfield=None,
# 	search_string=None,
# 	fields=None,
# 	as_dict=False,
# 	limit=None,
# 	offset=None,
# 	ignore_match_conditions=False,
# ) -> list:
# 	SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
# 	Employee = frappe.qb.DocType("Employee")

# 	query = (
# 		frappe.qb.from_(Employee)
# 		.join(SalaryStructureAssignment)
# 		.on(Employee.name == SalaryStructureAssignment.employee)
# 		.where(
# 			(SalaryStructureAssignment.docstatus == 1)
# 			& (Employee.status != "Inactive")
# 			& (Employee.status != "Suspended")
# 			& (Employee.status != "Left")
# 			& (Employee.status != "Retired")
# 			& (Employee.status != "Terminated")
# 			& (Employee.status != "Resigned")
# 			& (Employee.company == filters.company)
# 			& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
# 			& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
# 			& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
# 			& (filters.end_date >= SalaryStructureAssignment.from_date)
# 		)
# 		.select(
# 			SalaryStructureAssignment.payroll_payable_account,  # Select the payroll_payable_account
# 			# Employee.name,
# 			# SalaryStructureAssignment.salary_structure,
# 			# SalaryStructureAssignment.from_date
# 		)
# 	)

# 	query = set_fields_to_select(query, fields)
# 	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
# 	query = set_filter_conditions(query, filters, qb_object=Employee)

# 	if not ignore_match_conditions:
# 		query = set_match_conditions(query=query, qb_object=Employee)

# 	if limit:
# 		query = query.limit(limit)

# 	if offset:
# 		query = query.offset(offset)

# 	return query.run(as_dict=as_dict)


# def set_fields_to_select(query, fields: list[str] = None):
# 	default_fields = ["employee", "employee_name", "department", "designation"]

# 	if fields:
# 		query = query.select(*fields).distinct()
# 	else:
# 		query = query.select(*default_fields).distinct()

# 	return query


# def set_searchfield(query, searchfield, search_string, qb_object):
# 	if searchfield:
# 		query = query.where(
# 			(qb_object[searchfield].like("%" + search_string + "%"))
# 			| (qb_object.employee_name.like("%" + search_string + "%"))
# 		)

# 	return query


# def set_filter_conditions(query, filters, qb_object):
# 	"""Append optional filters to employee query"""
# 	if filters.get("employees"):
# 		query = query.where(qb_object.name.notin(filters.get("employees")))

# 	for fltr_key in ["branch", "department", "designation", "grade"]:
# 		if filters.get(fltr_key):
# 			query = query.where(qb_object[fltr_key] == filters[fltr_key])

# 	return query


# def set_match_conditions(query, qb_object):
# 	match_conditions = get_match_cond("Employee", as_condition=False)

# 	for cond in match_conditions:
# 		if isinstance(cond, dict):
# 			for key, value in cond.items():
# 				if isinstance(value, list):
# 					query = query.where(qb_object[key].isin(value))
# 				else:
# 					query = query.where(qb_object[key] == value)

# 	return query


# def remove_payrolled_employees(emp_list, start_date, end_date):
# 	SalarySlip = frappe.qb.DocType("Salary Slip")

# 	employees_with_payroll = (
# 		frappe.qb.from_(SalarySlip)
# 		.select(SalarySlip.employee)
# 		.where(
# 			(SalarySlip.docstatus == 1)
# 			& (SalarySlip.start_date == start_date)
# 			& (SalarySlip.end_date == end_date)
# 		)
# 	).run(pluck=True)

# 	return [emp_list[emp] for emp in emp_list if emp not in employees_with_payroll]


# @frappe.whitelist()
# def get_start_end_dates(payroll_frequency, start_date=None, company=None):
# 	"""Returns dict of start and end dates for given payroll frequency based on start_date"""

# 	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
# 		fiscal_year = get_fiscal_year(start_date, company=company)[0]
# 		month = "%02d" % getdate(start_date).month
# 		m = get_month_details(fiscal_year, month)
# 		if payroll_frequency == "Bimonthly":
# 			if getdate(start_date).day <= 15:
# 				start_date = m["month_start_date"]
# 				end_date = m["month_mid_end_date"]
# 			else:
# 				start_date = m["month_mid_start_date"]
# 				end_date = m["month_end_date"]
# 		else:
# 			start_date = m["month_start_date"]
# 			end_date = m["month_end_date"]

# 	if payroll_frequency == "Weekly":
# 		end_date = add_days(start_date, 6)

# 	if payroll_frequency == "Fortnightly":
# 		end_date = add_days(start_date, 13)

# 	if payroll_frequency == "Daily":
# 		end_date = start_date

# 	return frappe._dict({"start_date": start_date, "end_date": end_date})


# def get_frequency_kwargs(frequency_name):
# 	frequency_dict = {
# 		"monthly": {"months": 1},
# 		"fortnightly": {"days": 14},
# 		"weekly": {"days": 7},
# 		"daily": {"days": 1},
# 	}
# 	return frequency_dict.get(frequency_name)


# @frappe.whitelist()
# def get_end_date(start_date, frequency):
# 	start_date = getdate(start_date)
# 	frequency = frequency.lower() if frequency else "monthly"
# 	kwargs = (
# 		get_frequency_kwargs(frequency) if frequency != "bimonthly" else get_frequency_kwargs("monthly")
# 	)

# 	# weekly, fortnightly and daily intervals have fixed days so no problems
# 	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
# 	if frequency != "bimonthly":
# 		return dict(end_date=end_date.strftime(DATE_FORMAT))

# 	else:
# 		return dict(end_date="")


# def get_month_details(year, month):
# 	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
# 	if ysd:
# 		import calendar
# 		import datetime

# 		diff_mnt = cint(month) - cint(ysd.month)
# 		if diff_mnt < 0:
# 			diff_mnt = 12 - int(ysd.month) + cint(month)
# 		msd = ysd + relativedelta(months=diff_mnt)  # month start date
# 		month_days = cint(calendar.monthrange(cint(msd.year), cint(month))[1])  # days in month
# 		mid_start = datetime.date(msd.year, cint(month), 16)  # month mid start date
# 		mid_end = datetime.date(msd.year, cint(month), 15)  # month mid end date
# 		med = datetime.date(msd.year, cint(month), month_days)  # month end date
# 		return frappe._dict(
# 			{
# 				"year": msd.year,
# 				"month_start_date": msd,
# 				"month_end_date": med,
# 				"month_mid_start_date": mid_start,
# 				"month_mid_end_date": mid_end,
# 				"month_days": month_days,
# 			}
# 		)
# 	else:
# 		frappe.throw(_("Fiscal Year {0} not found").format(year))


# def get_payroll_entry_bank_entries(payroll_entry_name):
# 	je = frappe.qb.DocType("Journal Entry")
# 	jea = frappe.qb.DocType("Journal Entry Account")

# 	journal_entries = (
# 		frappe.qb.from_(je)
# 		.from_(jea)
# 		.select(je.name)
# 		.where(
# 			(je.name == jea.parent)
# 			& (je.voucher_type == "Bank Entry")
# 			& (jea.reference_name == payroll_entry_name)
# 			& (jea.reference_type == "Payroll Entry")
# 		)
# 	).run(as_dict=True)

# 	return journal_entries


# @frappe.whitelist()
# def payroll_entry_has_bank_entries(name: str):
# 	response = {}
# 	bank_entries = get_payroll_entry_bank_entries(name)
# 	response["submitted"] = 1 if bank_entries else 0

# 	return response


# def log_payroll_failure(process, payroll_entry, error):
# 	error_log = frappe.log_error(
# 		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
# 	)
# 	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

# 	try:
# 		if isinstance(message_log, str):
# 			error_message = json.loads(message_log).get("message")
# 		else:
# 			error_message = message_log.get("message")
# 	except Exception:
# 		error_message = message_log

# 	error_message += "\n" + _("Check Error Log {0} for more details.").format(
# 		get_link_to_form("Error Log", error_log.name)
# 	)

# 	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})


# def create_salary_slips_for_employees(employees, args, publish_progress=True):
# 	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)

# 	try:
# 		salary_slips_exist_for = get_existing_salary_slips(employees, args)
# 		count = 0

# 		employees = list(set(employees) - set(salary_slips_exist_for))
# 		for emp in employees:
# 			args.update({"doctype": "Salary Slip", "employee": emp})
# 			frappe.get_doc(args).insert()

# 			count += 1
# 			if publish_progress:
# 				frappe.publish_progress(
# 					count * 100 / len(employees),
# 					title=_("Creating Salary Slips..."),
# 				)

# 		payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})

# 		if salary_slips_exist_for:
# 			frappe.msgprint(
# 				_(
# 					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
# 				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
# 				title=_("Message"),
# 				indicator="orange",
# 			)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("creation", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_creation", user=frappe.session.user)


# def show_payroll_submission_status(submitted, unsubmitted, payroll_entry):
# 	if not submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_(
# 				"No salary slip found to submit for the above selected criteria OR salary slip already submitted"
# 			)
# 		)
# 	elif submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_("Salary Slips submitted for period from {0} to {1}").format(
# 				payroll_entry.start_date, payroll_entry.end_date
# 			)
# 		)
# 	elif unsubmitted:
# 		frappe.msgprint(
# 			_("Could not submit some Salary Slips: {}").format(
# 				", ".join(get_link_to_form("Salary Slip", entry) for entry in unsubmitted)
# 			)
# 		)


# def get_existing_salary_slips(employees, args):
# 	SalarySlip = frappe.qb.DocType("Salary Slip")

# 	return (
# 		frappe.qb.from_(SalarySlip)
# 		.select(SalarySlip.employee)
# 		.distinct()
# 		.where(
# 			(SalarySlip.docstatus != 2)
# 			& (SalarySlip.company == args.company)
# 			& (SalarySlip.payroll_entry == args.payroll_entry)
# 			& (SalarySlip.start_date >= args.start_date)
# 			& (SalarySlip.end_date <= args.end_date)
# 			& (SalarySlip.employee.isin(employees))
# 		)
# 	).run(pluck=True)


# def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
# 	try:
# 		submitted = []
# 		unsubmitted = []
# 		frappe.flags.via_payroll_entry = True
# 		count = 0

# 		for entry in salary_slips:
# 			salary_slip = frappe.get_doc("Salary Slip", entry[0])
# 			if salary_slip.net_pay < 0:
# 				unsubmitted.append(entry[0])
# 			else:
# 				try:
# 					salary_slip.submit()
# 					submitted.append(salary_slip)
# 				except frappe.ValidationError:
# 					unsubmitted.append(entry[0])

# 			count += 1
# 			if publish_progress:
# 				frappe.publish_progress(count * 100 / len(salary_slips), title=_("Submitting Salary Slips..."))

# 		if submitted:
# 			print(submitted, "submitted===================================")
# 			# payroll_entry.make_accrual_jv_entry(submitted)
# 			payroll_entry.enqueue_make_accrual_jv()
# 			payroll_entry.email_salary_slip(submitted)
# 			# payroll_entry.db_set({"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""})
# 			payroll_entry.db_set({"salary_slips_submitted": 1, "error_message": ""})


# 		show_payroll_submission_status(submitted, unsubmitted, payroll_entry)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("submission", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_submission", user=frappe.session.user)

# 	frappe.flags.via_payroll_entry = False


# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
# 	return frappe.db.sql(
# 		"""
# 		select name from `tabPayroll Entry`
# 		where `{key}` LIKE %(txt)s
# 		and name not in
# 			(select reference_name from `tabJournal Entry Account`
# 				where reference_type="Payroll Entry")
# 		order by name limit %(start)s, %(page_len)s""".format(
# 			key=searchfield
# 		),
# 		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
# 	)


# def get_employee_list(
# 	filters: frappe._dict,
# 	searchfield=None,
# 	search_string=None,
# 	fields: list[str] = None,
# 	as_dict=True,
# 	limit=None,
# 	offset=None,
# 	ignore_match_conditions=False,
# ) -> list:
# 	sal_struct = get_salary_structure(
# 		filters.company,
# 		filters.currency,
# 		filters.salary_slip_based_on_timesheet,
# 		filters.payroll_frequency,
# 	)

# 	if not sal_struct:
# 		return []

# 	emp_list = get_filtered_employees(
# 		sal_struct,
# 		filters,
# 		searchfield,
# 		search_string,
# 		fields,
# 		as_dict=as_dict,
# 		limit=limit,
# 		offset=offset,
# 		ignore_match_conditions=ignore_match_conditions,
# 	)

# 	if as_dict:
# 		employees_to_check = {emp.employee: emp for emp in emp_list}
# 	else:
# 		employees_to_check = {emp[0]: emp for emp in emp_list}

# 	return remove_payrolled_employees(employees_to_check, filters.start_date, filters.end_date)


# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def employee_query(doctype, txt, searchfield, start, page_len, filters):
# 	doctype = "Employee"
# 	filters = frappe._dict(filters)

# 	if not filters.payroll_frequency:
# 		frappe.throw(_("Select Payroll Frequency."))

# 	employee_list = get_employee_list(
# 		filters,
# 		searchfield=searchfield,
# 		search_string=txt,
# 		fields=["name", "employee_name"],
# 		as_dict=False,
# 		limit=page_len,
# 		offset=start,
# 	)

# 	return employee_list


# def filter_salary_components(components, emp):
# 	filtered = {}
# 	for k, v in components.items():
# 		# last element is always employee
# 		if k[-1] != emp.employee:
# 			continue  

# 		fund = k[2]

# 		if len(k) == 5:
# 			department = k[3]
# 			if fund == emp.custom_fund and department == emp.custom_department_name:
# 				filtered[k] = v

# 		elif len(k) == 4:
# 			if fund == emp.custom_fund:
# 				filtered[k] = v
# 	return filtered


# def enqueue_make_journal_entry(
# 	docname,
# 	accounts,
# 	currencies,
# 	payroll_payable_account=None,
# 	voucher_type="Journal Entry",
# 	custom_check_entry=False,
# 	cheque_date="",
# 	user_remark="",
# 	submitted_salary_slips=None,
# 	submit_journal_entry=False,
# 	cheque_no=None,
# ):
# 	start = time.time()
# 	stage = "INIT"

# 	try:
# 		logger.info(f"[JV START] Payroll Entry={docname}")

# 		doc = frappe.get_doc("Payroll Entry", docname)

# 		stage = "MAKE_JV"
# 		logger.info(
# 			f"[JV PROCESS] Stage={stage}, "
# 			f"Accounts={len(accounts)}, "
# 			f"Voucher={voucher_type}"
# 		)

# 		doc.make_journal_entry(
# 			accounts=accounts,
# 			currencies=currencies,
# 			payroll_payable_account=payroll_payable_account,
# 			voucher_type=voucher_type,
# 			custom_check_entry=custom_check_entry,
# 			cheque_date=cheque_date,
# 			user_remark=user_remark,
# 			submitted_salary_slips=submitted_salary_slips,
# 			submit_journal_entry=submit_journal_entry,
# 			cheque_no=cheque_no,
# 		)

# 		logger.info(
# 			f"[JV SUCCESS] Payroll Entry={docname}, "
# 			f"TimeTaken={round(time.time() - start, 2)}s"
# 		)

# 	except Exception:
# 		logger.error(
# 			f"[JV FAILED] Payroll Entry={docname}, "
# 			f"Stage={stage}, "
# 			f"TimeTaken={round(time.time() - start, 2)}s\n"
# 			f"{frappe.get_traceback()}"
# 		)

# 		frappe.log_error(
# 			frappe.get_traceback(),
# 			"Payroll JV Background Job Failed",
# 		)
# 		raise


# def process_accrual_jv(payroll_entry_name):
# 	"""
# 	Background job:
# 	- Load Payroll Entry
# 	- Load Salary Slips from DB
# 	- Run existing accrual logic
# 	"""

# 	frappe.set_user("Administrator")

# 	pe = frappe.get_doc("Payroll Entry", payroll_entry_name)

# 	# Safety check: avoid duplicate JV creation
# 	existing_jv = frappe.db.exists(
# 		"Journal Entry Account",
# 		{
# 			"reference_type": "Payroll Entry",
# 			"reference_name": pe.name,
# 			"docstatus": 1,
# 		},
# 	)
# 	if existing_jv:
# 		return

# 	# Load submitted salary slips INSIDE worker
# 	submitted_salary_slips = frappe.get_all(
# 		"Salary Slip",
# 		filters={
# 			"payroll_entry": pe.name,
# 			"docstatus": 1,
# 		},
# 		fields=["name", "employee", "custom_check_no"],
# 	)

# 	if not submitted_salary_slips:
# 		frappe.throw("No submitted Salary Slips found for accrual JV")

# 	# Existing heavy logic – UNCHANGED
# 	pe.make_accrual_jv_entry(submitted_salary_slips)

# 	# Update status after success
# 	pe.db_set("status", "Submitted")


# ==========================================core override with insurance provider feature for ssa====================

# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
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

from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import if_lending_app_installed
from hrms.payroll.doctype.salary_withholding.salary_withholding import link_bank_entry_in_salary_withholdings
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry



class OverridePayrollEntry(PayrollEntry):
	def onload(self):
		if self.docstatus == 0 and not self.salary_slips_created and self.employees:
			[employees_eligible_for_overtime, unsubmitted_overtime_slips] = self.get_overtime_slip_details()
			overtime_step = None
			if unsubmitted_overtime_slips:
				overtime_step = "Submit"
			elif employees_eligible_for_overtime:
				overtime_step = "Create"

			self.overtime_step = overtime_step

		if not self.docstatus == 1 or self.salary_slips_submitted:
			return

		# check if salary slips were manually submitted
		entries = frappe.db.count("Salary Slip", {"payroll_entry": self.name, "docstatus": 1}, ["name"])
		if cint(entries) == len(self.employees):
			self.set_onload("submitted_ss", True)

	def validate(self):
		self.number_of_employees = len(self.employees)
		self.set_status()

	def set_status(self, status=None, update=False):
		if not status:
			status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

		if update:
			self.db_set("status", status)
		else:
			self.status = status

	def before_submit(self):
		self.validate_existing_salary_slips()
		self.validate_payroll_payable_account()
		if self.get_employees_with_unmarked_attendance():
			frappe.throw(_("Cannot submit. Attendance is not marked for some employees."))

	def on_submit(self):
		self.set_status(update=True, status="Submitted")
		self.create_salary_slips()

	def validate_existing_salary_slips(self):
		if not self.employees:
			return

		existing_salary_slips = []
		SalarySlip = frappe.qb.DocType("Salary Slip")

		existing_salary_slips = (
			frappe.qb.from_(SalarySlip)
			.select(SalarySlip.employee, SalarySlip.name)
			.where(
				(SalarySlip.employee.isin([emp.employee for emp in self.employees]))
				& (SalarySlip.start_date == self.start_date)
				& (SalarySlip.end_date == self.end_date)
				& (SalarySlip.docstatus != 2)
			)
		).run(as_dict=True)

		if len(existing_salary_slips):
			msg = _("Salary Slip already exists for {0} for the given dates").format(
				comma_and([frappe.bold(d.employee) for d in existing_salary_slips])
			)
			msg += "<br><br>"
			msg += _("Reference: {0}").format(
				comma_and([get_link_to_form("Salary Slip", d.name) for d in existing_salary_slips])
			)
			frappe.throw(
				msg,
				title=_("Duplicate Entry"),
			)

	def validate_payroll_payable_account(self):
		payroll_payable_account_type = frappe.db.get_value(
			"Account", self.payroll_payable_account, "account_type"
		)
		if payroll_payable_account_type != "Payable":
			frappe.throw(
				_(
					"Account type should be set {0} for payroll payable account {1}, please set and try again"
				).format(
					frappe.bold("Payable"),
					frappe.bold(get_link_to_form("Account", self.payroll_payable_account)),
				)
			)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Salary Slip", "Journal Entry")

		self.delete_linked_salary_slips()
		self.cancel_linked_journal_entries()
		self.cancel_linked_payment_ledger_entries()

		# reset flags & update status
		self.db_set("salary_slips_created", 0)
		self.db_set("salary_slips_submitted", 0)
		self.set_status(update=True, status="Cancelled")
		self.db_set("error_message", "")

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def cancel(self):
		if len(self.get_linked_salary_slips()) > 50:
			msg = _("Payroll Entry cancellation is queued. It may take a few minutes")
			msg += "<br>"
			msg += _(
				"In case of any error during this background process, the system will add a comment about the error on this Payroll Entry and revert to the Submitted status"
			)
			frappe.msgprint(
				msg,
				indicator="blue",
				title=_("Cancellation Queued"),
			)
			self.queue_action("cancel", timeout=3000)
		else:
			self._cancel()

	def delete_linked_salary_slips(self):
		salary_slips = self.get_linked_salary_slips()

		# cancel & delete salary slips
		for salary_slip in salary_slips:
			if salary_slip.docstatus == 1:
				frappe.get_doc("Salary Slip", salary_slip.name).cancel()
			frappe.delete_doc("Salary Slip", salary_slip.name)

	def cancel_linked_journal_entries(self):
		journal_entries = frappe.get_all(
			"Journal Entry Account",
			{"reference_type": self.doctype, "reference_name": self.name, "docstatus": 1},
			pluck="parent",
			distinct=True,
		)

		# cancel Journal Entries
		for je in journal_entries:
			journal_entry_payment_ledgers = frappe.get_all(
				"Payment Ledger Entry",
				{"voucher_type": "Journal Entry", "voucher_no": je, "docstatus": 1},
				distinct=True,
			)
			# cancel linked payment ledger entry
			for pl in journal_entry_payment_ledgers:
				frappe.get_doc("Payment Ledger Entry", pl).cancel()

			frappe.get_doc("Journal Entry", je).cancel()

	def cancel_linked_payment_ledger_entries(self):
		payment_ledgers = frappe.get_all(
			"Payment Ledger Entry",
			{"against_voucher_type": self.doctype, "against_voucher_no": self.name, "docstatus": 1},
			distinct=True,
		)

		# cancel payment ledger entry
		for pl in payment_ledgers:
			frappe.get_doc("Payment Ledger Entry", pl).cancel()

	def get_linked_salary_slips(self):
		return frappe.get_all("Salary Slip", {"payroll_entry": self.name}, ["name", "docstatus"])

	def make_filters(self):
		filters = frappe._dict(
			company=self.company,
			branch=self.branch,
			department=self.department,
			designation=self.designation,
			grade=self.grade,
			currency=self.currency,
			start_date=self.start_date,
			end_date=self.end_date,
			payroll_payable_account=self.payroll_payable_account,
			salary_slip_based_on_timesheet=self.salary_slip_based_on_timesheet,
		)

		if not self.salary_slip_based_on_timesheet:
			filters.update(dict(payroll_frequency=self.payroll_frequency))

		return filters

	@frappe.whitelist()
	def fill_employee_details(self):
		filters = self.make_filters()
		employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)
		self.set("employees", [])

		if not employees:
			error_msg = _(
				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
			).format(
				frappe.bold(self.company),
				frappe.bold(self.currency),
				frappe.bold(self.payroll_payable_account),
			)
			if self.branch:
				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
			if self.department:
				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
			if self.designation:
				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
			if self.start_date:
				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
			if self.end_date:
				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
			frappe.throw(error_msg, title=_("No employees found"))

		self.set("employees", employees)
		self.number_of_employees = len(self.employees)
		self.update_employees_with_withheld_salaries()

		return self.get_employees_with_unmarked_attendance()

	def update_employees_with_withheld_salaries(self):
		withheld_salaries = get_salary_withholdings(self.start_date, self.end_date, pluck="employee")

		for employee in self.employees:
			if employee.employee in withheld_salaries:
				employee.is_salary_withheld = 1

	@frappe.whitelist()
	def create_salary_slips(self):
		"""
		Creates salary slip for selected employees if already not created
		"""
		self.check_permission("write")
		employees = [emp.employee for emp in self.employees]

		if employees:
			args = frappe._dict(
				{
					"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
					"payroll_frequency": self.payroll_frequency,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"company": self.company,
					"posting_date": self.posting_date,
					"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
					"payroll_entry": self.name,
					"exchange_rate": self.exchange_rate,
					"currency": self.currency,
				}
			)
			if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					create_salary_slips_for_employees,
					timeout=3000,
					employees=employees,
					args=args,
					publish_progress=False,
				)
				frappe.msgprint(
					_("Salary Slip creation is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				create_salary_slips_for_employees(employees, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
		Returns list of salary slips based on selected criteria
		"""

		ss = frappe.qb.DocType("Salary Slip")
		ss_list = (
			frappe.qb.from_(ss)
			.select(ss.name, ss.salary_structure)
			.where(
				(ss.docstatus == ss_status)
				& (ss.start_date >= self.start_date)
				& (ss.end_date <= self.end_date)
				& (ss.payroll_entry == self.name)
				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
			)
		).run(as_dict=as_dict)

		return ss_list

	@frappe.whitelist()
	def submit_salary_slips(self):
		self.check_permission("write")
		salary_slips = self.get_sal_slip_list(ss_status=0)

		if len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry:
			self.db_set("status", "Queued")
			frappe.enqueue(
				submit_salary_slips_for_employees,
				timeout=3000,
				payroll_entry=self,
				salary_slips=salary_slips,
				publish_progress=False,
			)
			frappe.msgprint(
				_("Salary Slip submission is queued. It may take a few minutes"),
				alert=True,
				indicator="blue",
			)
		else:
			submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

	def get_insurance_details_from_ssa(self, employee, salary_component):
		ssa = frappe.db.get_value(
			"Salary Structure Assignment",
			{
				"employee": employee,
				"docstatus": 1
			},
			"name"
		)
		if not ssa:
			return None, None  

		print(employee,ssa,salary_component,"employee,ssa,salary_component 0000000000000" )
		result = frappe.db.get_value(
			"Employee Insurance Deduction",
			{
				"parent": ssa,
				"salary_component": salary_component
			},
			["insurance_company", "salary_component"]
		)
		if not result:
			return None, None   # ✅ ALWAYS return tuple

		print(result,"resultsssssssssssssssssssssssssssssssssssssssssssssssss" )
		return result


	# def get_insurance_provider_account(
	# 	self,
	# 	provider,
	# 	salary_component
	# ):
	# 	provider_doc = frappe.get_cached_doc("Insurance Provider", provider)
	# 	comp_doc = frappe.get_cached_doc("Salary Component", salary_component)
	# 	for row in provider_doc.accounts:
	# 		acc_doc = frappe.get_cached_doc("Account", row.account)

	# 		filters = {
	# 			"parent": "Insurance Provider",
	# 		}
	# 		print(filters, "department match")
	# 		break  # stop at first department match

	# 	account = None
	# 	account = frappe.db.get_value("Salary Component Account", filters, "account", cache=True)
		
	# 	if not account:		
	# 		frappe.throw(
	# 			_("Please set proper Insurance account in Insurance Provider {0}")
	# 			.format(provider)
	# 		)
	# 	return account

	def get_insurance_provider_account(self, provider, salary_component):
		provider_doc = frappe.get_cached_doc("Insurance Provider", provider)

		for row in provider_doc.accounts:
			if row.account:
				return row.account

		frappe.throw(
			_("Please set proper Insurance account in Insurance Provider {0}")
			.format(provider)
		)


	def get_salary_component_account(self, salary_component, employee=None):
		print("get_salary_component_account calllllllllllllllllllllllllll")
		comp_doc = frappe.get_cached_doc("Salary Component", salary_component)
		# 🔹 INSURANCE OVERRIDE (Employee or Employer)
		if comp_doc.type == "Deduction" and (
			comp_doc.custom_is_this_insurance_component
			or comp_doc.custom_is_this_employers_insurance_component
		):
			provider, category = self.get_insurance_details_from_ssa(employee, salary_component)
			print(provider, category, "provider, category ==============")

			if provider:
				return self.get_insurance_provider_account(provider, salary_component)

		account = frappe.db.get_value(
			"Salary Component Account",
			{"parent": salary_component, "company": self.company},
			"account",
			cache=True,
		)

		if not account:
			frappe.throw(
				_("Please set account in Salary Component {0}").format(
					get_link_to_form("Salary Component", salary_component)
				)
			)

		return account

	def get_salary_components(self, component_type):
		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

		if salary_slips:
			ss = frappe.qb.DocType("Salary Slip")
			ssd = frappe.qb.DocType("Salary Detail")
			salary_components = (
				frappe.qb.from_(ss)
				.join(ssd)
				.on(ss.name == ssd.parent)
				.select(
					ssd.salary_component,
					ssd.amount,
					ssd.parentfield,
					ssd.additional_salary,
					ss.salary_structure,
					ss.employee,
				)
				.where(
					(ssd.parentfield == component_type)
					& (ss.name.isin([d.name for d in salary_slips]))
					& (
						(ssd.do_not_include_in_total == 0)
						| ((ssd.do_not_include_in_total == 1) & (ssd.do_not_include_in_accounts == 0))
					)
				)
			).run(as_dict=True)

			return salary_components

	def get_salary_component_total(
		self,
		component_type=None,
		employee_wise_accounting_enabled=False,
	):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}

			for item in salary_components:
				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
					item.employee, item.salary_structure
				)
				employee_advance = self.get_advance_deduction(component_type, item)

				for cost_center, percentage in employee_cost_centers.items():
					amount_against_cost_center = flt(item.amount) * percentage / 100

					if employee_advance:
						self.add_advance_deduction_entry(
							item, amount_against_cost_center, cost_center, employee_advance
						)
					else:
						# key = (item.salary_component, cost_center)
						# component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

						employee = [_.employee for _ in self.employees if _.employee == item.employee][0]
						key = (item.salary_component, cost_center, employee)
						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							component_type, item.employee, amount_against_cost_center
						)

			account_details = self.get_account(component_dict=component_dict)

			return account_details

	def get_advance_deduction(self, component_type: str, item: dict) -> str | None:
		if component_type == "deductions" and item.additional_salary:
			ref_doctype, ref_docname = frappe.db.get_value(
				"Additional Salary",
				item.additional_salary,
				["ref_doctype", "ref_docname"],
			)

			if ref_doctype == "Employee Advance":
				return ref_docname
		return

	def add_advance_deduction_entry(
		self,
		item: dict,
		amount: float,
		cost_center: str,
		employee_advance: str,
	) -> None:
		self._advance_deduction_entries.append(
			{
				"employee": item.employee,
				"account": self.get_salary_component_account(item.salary_component),
				"amount": amount,
				"cost_center": cost_center,
				"reference_type": "Employee Advance",
				"reference_name": employee_advance,
			}
		)

	def set_accounting_entries_for_advance_deductions(
		self,
		accounts: list,
		currencies: list,
		company_currency: str,
		accounting_dimensions: list,
		precision: int,
		payable_amount: float,
	):
		for entry in self._advance_deduction_entries:
			payable_amount = self.get_accounting_entries_and_payable_amount(
				entry.get("account"),
				entry.get("cost_center"),
				entry.get("amount"),
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="credit",
				accounts=accounts,
				party=entry.get("employee"),
				reference_type="Employee Advance",
				reference_name=entry.get("reference_name"),
				is_advance="Yes",
			)

		return payable_amount

	def set_employee_based_payroll_payable_entries(
		self, component_type, employee, amount, salary_structure=None
	):
		employee_details = self.employee_based_payroll_payable_entries.setdefault(employee, {})

		employee_details.setdefault(component_type, 0)
		employee_details[component_type] += amount

		if salary_structure and "salary_structure" not in employee_details:
			employee_details["salary_structure"] = salary_structure

	def get_payroll_cost_centers_for_employee(self, employee, salary_structure):
		if not hasattr(self, "employee_cost_centers"):
			self.employee_cost_centers = {}

		if not self.employee_cost_centers.get(employee):
			SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
			EmployeeCostCenter = frappe.qb.DocType("Employee Cost Center")
			assignment_subquery = (
				frappe.qb.from_(SalaryStructureAssignment)
				.select(SalaryStructureAssignment.name)
				.where(
					(SalaryStructureAssignment.employee == employee)
					& (SalaryStructureAssignment.salary_structure == salary_structure)
					& (SalaryStructureAssignment.docstatus == 1)
					& (SalaryStructureAssignment.from_date <= self.end_date)
				)
				.orderby(SalaryStructureAssignment.from_date, order=frappe.qb.desc)
				.limit(1)
			)
			cost_centers = dict(
				(
					frappe.qb.from_(EmployeeCostCenter)
					.select(EmployeeCostCenter.cost_center, EmployeeCostCenter.percentage)
					.where(EmployeeCostCenter.parent == assignment_subquery)
				).run(as_list=True)
			)

			if not cost_centers:
				default_cost_center, department = frappe.get_cached_value(
					"Employee", employee, ["payroll_cost_center", "department"]
				)

				if not default_cost_center and department:
					default_cost_center = frappe.get_cached_value(
						"Department", department, "payroll_cost_center"
					)

				if not default_cost_center:
					default_cost_center = self.cost_center

				cost_centers = {default_cost_center: 100}

			self.employee_cost_centers.setdefault(employee, cost_centers)

		return self.employee_cost_centers.get(employee, {})

	def get_account(self, component_dict=None, employee=None):
		account_dict = {}
		for key, amount in component_dict.items():
			component, cost_center, employee = key
			account = self.get_salary_component_account(component, employee)
			print(account,"account****************************")
			accounting_key = (account, cost_center)

			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

			print(account_dict,"account_dict+++++++++++++++++++++++++++")

		return account_dict

	def make_accrual_jv_entry(self, submitted_salary_slips):
		print(submitted_salary_slips,"call in make_accrual_jv_entry =========================")
		self.check_permission("write")
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		self.employee_based_payroll_payable_entries = {}
		self._advance_deduction_entries = []

		earnings = (
			self.get_salary_component_total(
				component_type="earnings",
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)
			or {}
		)
		print(earnings,"earnings")

		deductions = (
			self.get_salary_component_total(
				component_type="deductions",
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)
			or {}
		)
		print(deductions,"deductions ")

		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		print(earnings,deductions,"earnings,deductions 00000000000000000000000000")

		if earnings or deductions:
			print(earnings,deductions,"earnings,deductions 11111111111111111111111111")
			accounts = []
			currencies = []
			payable_amount = 0
			accounting_dimensions = get_accounting_dimensions() or []
			company_currency = erpnext.get_company_currency(self.company)

			payable_amount = self.get_payable_amount_for_earnings_and_deductions(
				accounts,
				earnings,
				deductions,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				employee_wise_accounting_enabled,
			)

			payable_amount = self.set_accounting_entries_for_advance_deductions(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
			)

			self.set_payable_amount_against_payroll_payable_account(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				self.payroll_payable_account,
				employee_wise_accounting_enabled,
			)

			# when party is not required, skip the validation in journal & gl entry
			self.make_journal_entry(
				accounts,
				currencies,
				self.payroll_payable_account,
				voucher_type="Journal Entry",
				user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
					self.start_date, self.end_date
				),
				submit_journal_entry=True,
				submitted_salary_slips=submitted_salary_slips,
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)

	def make_journal_entry(
		self,
		accounts,
		currencies,
		payroll_payable_account=None,
		voucher_type="Journal Entry",
		user_remark="",
		submitted_salary_slips: list | None = None,
		submit_journal_entry=False,
		employee_wise_accounting_enabled=False,
	) -> str:
		multi_currency = 0
		if len(currencies) > 1:
			multi_currency = 1

		print("make_journal_entry --------------------------")

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = voucher_type
		journal_entry.user_remark = user_remark
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.party_not_required = True if not employee_wise_accounting_enabled else False

		journal_entry.set("accounts", accounts)
		journal_entry.multi_currency = multi_currency

		if voucher_type == "Journal Entry":
			journal_entry.title = payroll_payable_account

		journal_entry.save(ignore_permissions=True)

		try:
			if submit_journal_entry:
				journal_entry.submit()

			if submitted_salary_slips:
				self.set_journal_entry_in_salary_slips(submitted_salary_slips, jv_name=journal_entry.name)

		except Exception as e:
			if type(e) in (str, list, tuple):
				frappe.msgprint(e)

			self.log_error("Journal Entry creation against Salary Slip failed")
			raise

		return journal_entry

	def get_payable_amount_for_earnings_and_deductions(
		self,
		accounts,
		earnings,
		deductions,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
		employee_wise_accounting_enabled,
	):
		# Earnings
		for acc_cc, amount in earnings.items():
			payable_amount = self.get_accounting_entries_and_payable_amount(
				acc_cc[0],
				acc_cc[1] or self.cost_center,
				amount,
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="debit",
				accounts=accounts,
			)

		# Deductions
		for acc_cc, amount in deductions.items():
			payable_amount = self.get_accounting_entries_and_payable_amount(
				acc_cc[0],
				acc_cc[1] or self.cost_center,
				amount,
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="credit",
				accounts=accounts,
			)

		return payable_amount

	def set_payable_amount_against_payroll_payable_account(
		self,
		accounts,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
		payroll_payable_account,
		employee_wise_accounting_enabled,
	):
		# Payable amount
		if employee_wise_accounting_enabled:
			"""
			employee_based_payroll_payable_entries = {
							'HREMP00004': {
											'earnings': 83332.0,
											'deductions': 2000.0
							},
							'HREMP00005': {
											'earnings': 50000.0,
											'deductions': 2000.0
							}
			}
			"""
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				payable_amount = (employee_details.get("earnings", 0) or 0) - (
					employee_details.get("deductions", 0) or 0
				)

				payable_amount = self.get_accounting_entries_and_payable_amount(
					payroll_payable_account,
					self.cost_center,
					payable_amount,
					currencies,
					company_currency,
					0,
					accounting_dimensions,
					precision,
					entry_type="payable",
					party=employee,
					accounts=accounts,
				)
		else:
			payable_amount = self.get_accounting_entries_and_payable_amount(
				payroll_payable_account,
				self.cost_center,
				payable_amount,
				currencies,
				company_currency,
				0,
				accounting_dimensions,
				precision,
				entry_type="payable",
				accounts=accounts,
			)

	def get_accounting_entries_and_payable_amount(
		self,
		account,
		cost_center,
		amount,
		currencies,
		company_currency,
		payable_amount,
		accounting_dimensions,
		precision,
		entry_type="credit",
		party=None,
		accounts=None,
		reference_type=None,
		reference_name=None,
		is_advance=None,
	):
		exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
			account, amount, company_currency, currencies
		)

		row = {
			"account": account,
			"exchange_rate": flt(exchange_rate),
			"cost_center": cost_center,
			"project": self.project,
		}

		if entry_type == "debit":
			payable_amount += flt(amount, precision)
			row.update(
				{
					"debit_in_account_currency": flt(amt, precision),
				}
			)
		elif entry_type == "credit":
			payable_amount -= flt(amount, precision)
			row.update(
				{
					"credit_in_account_currency": flt(amt, precision),
				}
			)
		else:
			row.update(
				{
					"credit_in_account_currency": flt(amt, precision),
					"reference_type": self.doctype,
					"reference_name": self.name,
				}
			)

		if party:
			row.update(
				{
					"party_type": "Employee",
					"party": party,
				}
			)

		if reference_type:
			row.update(
				{
					"reference_type": reference_type,
					"reference_name": reference_name,
					"is_advance": is_advance,
				}
			)

		self.update_accounting_dimensions(
			row,
			accounting_dimensions,
		)

		if amt:
			accounts.append(row)

		return payable_amount

	def update_accounting_dimensions(self, row, accounting_dimensions):
		for dimension in accounting_dimensions:
			row.update({dimension: self.get(dimension)})

		return row

	def get_amount_and_exchange_rate_for_journal_entry(self, account, amount, company_currency, currencies):
		conversion_rate = 1
		exchange_rate = self.exchange_rate
		account_currency = frappe.db.get_value("Account", account, "account_currency")

		if account_currency not in currencies:
			currencies.append(account_currency)

		if company_currency not in currencies:
			currencies.append(company_currency)

		if account_currency == company_currency:
			conversion_rate = self.exchange_rate
			exchange_rate = 1

		amount = flt(amount) * flt(conversion_rate)

		return exchange_rate, amount

	@frappe.whitelist()
	def has_bank_entries(self) -> dict[str, bool]:
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")

		bank_entries = (
			frappe.qb.from_(je)
			.inner_join(jea)
			.on(je.name == jea.parent)
			.select(je.name)
			.where(
				((je.voucher_type == "Bank Entry") | (je.voucher_type == "Cash Entry"))
				& (jea.reference_name == self.name)
				& (jea.reference_type == "Payroll Entry")
			)
		).run(as_dict=True)

		return {
			"has_bank_entries": bool(bank_entries),
			"has_bank_entries_for_withheld_salaries": not any(
				employee.is_salary_withheld for employee in self.employees
			),
		}

	@frappe.whitelist()
	def make_bank_entry(self, for_withheld_salaries=False):
		print("call in make_bank_entry========")
		self.check_permission("write")
		self.employee_based_payroll_payable_entries = {}
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)

		salary_slip_total = 0
		salary_details = self.get_salary_slip_details(for_withheld_salaries)

		for salary_detail in salary_details:
			statistical_component = frappe.db.get_value(
				"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
			)
			if not statistical_component:
				parent_field = salary_detail.parentfield
				if parent_field in ("earnings", "deductions"):
					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							salary_detail.parentfield,
							salary_detail.employee,
							salary_detail.amount,
							salary_detail.salary_structure,
						)
					if parent_field == "earnings":
						salary_slip_total += salary_detail.amount
					elif parent_field == "deductions":
						salary_slip_total -= salary_detail.amount

		total_loan_repayment = self.process_loan_repayments_for_bank_entry(salary_details) or 0
		salary_slip_total -= total_loan_repayment

		bank_entry = None

		if salary_slip_total > 0:
			remark = "withheld salaries" if for_withheld_salaries else "salaries"
			bank_entry = self.set_accounting_entries_for_bank_entry(
				salary_slip_total, remark, employee_wise_accounting_enabled
			)

			if for_withheld_salaries:
				link_bank_entry_in_salary_withholdings(salary_details, bank_entry.name)

		return bank_entry

	def get_salary_slip_details(self, for_withheld_salaries=False):
		SalarySlip = frappe.qb.DocType("Salary Slip")
		SalaryDetail = frappe.qb.DocType("Salary Detail")

		query = (
			frappe.qb.from_(SalarySlip)
			.join(SalaryDetail)
			.on(SalarySlip.name == SalaryDetail.parent)
			.select(
				SalarySlip.name,
				SalarySlip.employee,
				SalarySlip.salary_structure,
				SalarySlip.salary_withholding_cycle,
				SalaryDetail.salary_component,
				SalaryDetail.amount,
				SalaryDetail.parentfield,
			)
			.where(
				(SalarySlip.docstatus == 1)
				& (SalarySlip.start_date >= self.start_date)
				& (SalarySlip.end_date <= self.end_date)
				& (SalarySlip.payroll_entry == self.name)
				& (
					(SalaryDetail.do_not_include_in_total == 0)
					| (
						(SalaryDetail.do_not_include_in_total == 1)
						& (SalaryDetail.do_not_include_in_accounts == 0)
					)
				)
			)
		)

		if "lending" in frappe.get_installed_apps():
			query = query.select(SalarySlip.total_loan_repayment)

		if for_withheld_salaries:
			query = query.where(SalarySlip.status == "Withheld")
		else:
			query = query.where(SalarySlip.status != "Withheld")
		return query.run(as_dict=True)

	@if_lending_app_installed
	def process_loan_repayments_for_bank_entry(self, salary_details: list[dict]) -> float:
		unique_salary_slips = {row["employee"]: row for row in salary_details}.values()
		total_loan_repayment = sum(flt(slip.get("total_loan_repayment", 0)) for slip in unique_salary_slips)

		if self.employee_based_payroll_payable_entries:
			for salary_slip in unique_salary_slips:
				if salary_slip.get("total_loan_repayment"):
					self.set_employee_based_payroll_payable_entries(
						"total_loan_repayment",
						salary_slip.employee,
						salary_slip.total_loan_repayment,
						salary_slip.salary_structure,
					)

		return total_loan_repayment

	def set_accounting_entries_for_bank_entry(
		self, je_payment_amount, user_remark, employee_wise_accounting_enabled
	):
		payroll_payable_account = self.payroll_payable_account
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		accounts = []
		currencies = []
		company_currency = erpnext.get_company_currency(self.company)
		accounting_dimensions = get_accounting_dimensions() or []

		exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
			self.payment_account, je_payment_amount, company_currency, currencies
		)
		accounts.append(
			self.update_accounting_dimensions(
				{
					"account": self.payment_account,
					"bank_account": self.bank_account,
					"credit_in_account_currency": flt(amount, precision),
					"exchange_rate": flt(exchange_rate),
					"cost_center": self.cost_center,
				},
				accounting_dimensions,
			)
		)

		if self.employee_based_payroll_payable_entries:
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				je_payment_amount = (
					(employee_details.get("earnings", 0) or 0)
					- (employee_details.get("deductions", 0) or 0)
					- (employee_details.get("total_loan_repayment", 0) or 0)
				)

				if not je_payment_amount:
					continue

				exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
					self.payment_account, je_payment_amount, company_currency, currencies
				)

				cost_centers = self.get_payroll_cost_centers_for_employee(
					employee, employee_details.get("salary_structure")
				)

				for cost_center, percentage in cost_centers.items():
					amount_against_cost_center = flt(amount) * percentage / 100
					accounts.append(
						self.update_accounting_dimensions(
							{
								"account": payroll_payable_account,
								"debit_in_account_currency": flt(amount_against_cost_center, precision),
								"exchange_rate": flt(exchange_rate),
								"reference_type": self.doctype,
								"reference_name": self.name,
								"party_type": "Employee",
								"party": employee,
								"cost_center": cost_center,
							},
							accounting_dimensions,
						)
					)
		else:
			exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
				payroll_payable_account, je_payment_amount, company_currency, currencies
			)
			accounts.append(
				self.update_accounting_dimensions(
					{
						"account": payroll_payable_account,
						"debit_in_account_currency": flt(amount, precision),
						"exchange_rate": flt(exchange_rate),
						"reference_type": self.doctype,
						"reference_name": self.name,
						"cost_center": self.cost_center,
					},
					accounting_dimensions,
				)
			)

		return self.make_journal_entry(
			accounts,
			currencies,
			voucher_type="Cash Entry"
			if frappe.get_cached_value("Account", self.payment_account, "account_type") == "Cash"
			else "Bank Entry",
			user_remark=_("Payment of {0} from {1} to {2}").format(
				_(user_remark), self.start_date, self.end_date
			),
			employee_wise_accounting_enabled=employee_wise_accounting_enabled,
		)

	def set_journal_entry_in_salary_slips(self, submitted_salary_slips, jv_name=None):
		SalarySlip = frappe.qb.DocType("Salary Slip")
		(
			frappe.qb.update(SalarySlip)
			.set(SalarySlip.journal_entry, jv_name)
			.where(SalarySlip.name.isin([salary_slip.name for salary_slip in submitted_salary_slips]))
		).run()

	def set_start_end_dates(self):
		self.update(
			get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company)
		)

	@frappe.whitelist()
	def get_employees_with_unmarked_attendance(self) -> list[dict] | None:
		if not self.validate_attendance:
			return

		unmarked_attendance = []
		employee_details = self.get_employee_and_attendance_details()
		default_holiday_list = frappe.db.get_value(
			"Company", self.company, "default_holiday_list", cache=True
		)

		for emp in self.employees:
			details = next((record for record in employee_details if record.name == emp.employee), None)
			if not details:
				continue

			start_date, end_date = self.get_payroll_dates_for_employee(details)
			holidays = self.get_holidays_count(
				details.holiday_list or default_holiday_list, start_date, end_date
			)
			payroll_days = date_diff(end_date, start_date) + 1
			unmarked_days = payroll_days - (holidays + details.attendance_count)

			if unmarked_days > 0:
				unmarked_attendance.append(
					{
						"employee": emp.employee,
						"employee_name": emp.employee_name,
						"unmarked_days": unmarked_days,
					}
				)

		return unmarked_attendance

	def get_employee_and_attendance_details(self) -> list[dict]:
		"""Returns a list of employee and attendance details like
		[
				{
						"name": "HREMP00001",
						"date_of_joining": "2019-01-01",
						"relieving_date": "2022-01-01",
						"holiday_list": "Holiday List Company",
						"attendance_count": 22
				}
		]
		"""
		employees = [emp.employee for emp in self.employees]

		Employee = frappe.qb.DocType("Employee")
		Attendance = frappe.qb.DocType("Attendance")

		return (
			frappe.qb.from_(Employee)
			.left_join(Attendance)
			.on(
				(Employee.name == Attendance.employee)
				& (Attendance.attendance_date.between(self.start_date, self.end_date))
				& (Attendance.docstatus == 1)
			)
			.select(
				Employee.name,
				Employee.date_of_joining,
				Employee.relieving_date,
				Employee.holiday_list,
				Count(Attendance.name).as_("attendance_count"),
			)
			.where(Employee.name.isin(employees))
			.groupby(Employee.name)
		).run(as_dict=True)

	def get_payroll_dates_for_employee(self, employee_details: dict) -> tuple[str, str]:
		start_date = self.start_date
		if employee_details.date_of_joining > getdate(self.start_date):
			start_date = employee_details.date_of_joining

		end_date = self.end_date
		if employee_details.relieving_date and employee_details.relieving_date < getdate(self.end_date):
			end_date = employee_details.relieving_date

		return start_date, end_date

	def get_holidays_count(self, holiday_list: str, start_date: str, end_date: str) -> float:
		"""Returns number of holidays between start and end dates in the holiday list"""
		if not hasattr(self, "_holidays_between_dates"):
			self._holidays_between_dates = {}

		key = f"{start_date}-{end_date}-{holiday_list}"
		if key in self._holidays_between_dates:
			return self._holidays_between_dates[key]

		holidays = frappe.db.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])},
			fields=[{"COUNT": "*", "as": "holidays_count"}],
		)[0]

		if holidays:
			self._holidays_between_dates[key] = holidays.holidays_count

		return self._holidays_between_dates.get(key) or 0

	@frappe.whitelist()
	def create_overtime_slips(self):
		from hrms.hr.doctype.overtime_slip.overtime_slip import (
			create_overtime_slips_for_employees,
			filter_employees_for_overtime_slip_creation,
		)

		employee_list = [emp.employee for emp in self.employees]
		employees = filter_employees_for_overtime_slip_creation(self.start_date, self.end_date, employee_list)

		if employees:
			args = frappe._dict(
				{
					"posting_date": self.posting_date,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"company": self.company,
					"currency": self.currency,
					"payroll_entry": self.name,
				}
			)
			if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					create_overtime_slips_for_employees,
					timeout=3000,
					employees=employees,
					args=args,
				)
				frappe.msgprint(
					_("Overtime Slip creation is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				create_overtime_slips_for_employees(employees, args)

	@frappe.whitelist()
	def submit_overtime_slips(self):
		from hrms.hr.doctype.overtime_slip.overtime_slip import (
			submit_overtime_slips_for_employees,
		)

		overtime_slips = self.get_unsubmitted_overtime_slips()
		if overtime_slips:
			if len(overtime_slips) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					submit_overtime_slips_for_employees,
					timeout=3000,
					overtime_slips=overtime_slips,
					payroll_entry=self.name,
				)
				frappe.msgprint(
					_("Overtime Slip submission is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				submit_overtime_slips_for_employees(overtime_slips, self.name)

	@frappe.whitelist()
	def get_unsubmitted_overtime_slips(self, limit=None):
		OvertimeSlip = frappe.qb.DocType("Overtime Slip")
		query = (
			frappe.qb.from_(OvertimeSlip)
			.select(OvertimeSlip.name)
			.where((OvertimeSlip.docstatus == 0) & (OvertimeSlip.payroll_entry == self.name))
		)
		if limit:
			query = query.limit(limit)

		return query.run(pluck="name")

	@frappe.whitelist()
	def get_overtime_slip_details(self):
		from hrms.hr.doctype.overtime_slip.overtime_slip import filter_employees_for_overtime_slip_creation

		employee_eligible_for_overtime = unsubmitted_overtime_slips = []

		if frappe.db.get_single_value("Payroll Settings", "create_overtime_slip"):
			employees = [emp.employee for emp in self.employees]
			employee_eligible_for_overtime = filter_employees_for_overtime_slip_creation(
				self.start_date, self.end_date, employees
			)
			unsubmitted_overtime_slips = self.get_unsubmitted_overtime_slips(limit=1)

		return [len(employee_eligible_for_overtime) > 0, len(unsubmitted_overtime_slips) > 0]


def get_salary_structure(
	company: str, currency: str, salary_slip_based_on_timesheet: int, payroll_frequency: str
) -> list[str]:
	SalaryStructure = frappe.qb.DocType("Salary Structure")

	query = (
		frappe.qb.from_(SalaryStructure)
		.select(SalaryStructure.name)
		.where(
			(SalaryStructure.docstatus == 1)
			& (SalaryStructure.is_active == "Yes")
			& (SalaryStructure.company == company)
			& (SalaryStructure.currency == currency)
			& (SalaryStructure.salary_slip_based_on_timesheet == salary_slip_based_on_timesheet)
		)
	)

	if not salary_slip_based_on_timesheet:
		query = query.where(SalaryStructure.payroll_frequency == payroll_frequency)

	return query.run(pluck=True)


def get_filtered_employees(
	sal_struct,
	filters,
	searchfield=None,
	search_string=None,
	fields=None,
	as_dict=False,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.from_(Employee)
		.join(SalaryStructureAssignment)
		.on(Employee.name == SalaryStructureAssignment.employee)
		.where(
			(SalaryStructureAssignment.docstatus == 1)
			& (Employee.status != "Inactive")
			& (Employee.company == filters.company)
			& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
			& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
			& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
			& (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
			& (filters.end_date >= SalaryStructureAssignment.from_date)
		)
	)

	query = set_fields_to_select(query, fields)
	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
	query = set_filter_conditions(query, filters, qb_object=Employee)

	if not ignore_match_conditions:
		query = set_match_conditions(query=query, qb_object=Employee)

	if limit:
		query = query.limit(limit)

	if offset:
		query = query.offset(offset)

	return query.run(as_dict=as_dict)


def set_fields_to_select(query, fields: list[str] | None = None):
	default_fields = ["employee", "employee_name", "department", "designation"]

	if fields:
		query = query.select(*fields).distinct()
	else:
		query = query.select(*default_fields).distinct()

	return query


def set_searchfield(query, searchfield, search_string, qb_object):
	if searchfield:
		query = query.where(
			(qb_object[searchfield].like("%" + search_string + "%"))
			| (qb_object.employee_name.like("%" + search_string + "%"))
		)

	return query


def set_filter_conditions(query, filters, qb_object):
	"""Append optional filters to employee query"""
	if filters.get("employees"):
		query = query.where(qb_object.name.notin(filters.get("employees")))

	for fltr_key in ["branch", "department", "designation", "grade"]:
		if filters.get(fltr_key):
			query = query.where(qb_object[fltr_key] == filters[fltr_key])

	return query


def set_match_conditions(query, qb_object):
	match_conditions = get_match_cond("Employee", as_condition=False)

	for cond in match_conditions:
		if isinstance(cond, dict):
			for key, value in cond.items():
				if isinstance(value, list):
					query = query.where(qb_object[key].isin(value))
				else:
					query = query.where(qb_object[key] == value)

	return query


def remove_payrolled_employees(emp_list, start_date, end_date):
	SalarySlip = frappe.qb.DocType("Salary Slip")

	employees_with_payroll = (
		frappe.qb.from_(SalarySlip)
		.select(SalarySlip.employee)
		.where(
			(SalarySlip.docstatus == 1)
			& (SalarySlip.start_date == start_date)
			& (SalarySlip.end_date == end_date)
		)
	).run(pluck=True)

	return [emp_list[emp] for emp in emp_list if emp not in employees_with_payroll]


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

	if payroll_frequency == "Fortnightly":
		end_date = add_days(start_date, 13)

	if payroll_frequency == "Daily":
		end_date = start_date

	return frappe._dict({"start_date": start_date, "end_date": end_date})


def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		"monthly": {"months": 1},
		"fortnightly": {"days": 14},
		"weekly": {"days": 7},
		"daily": {"days": 1},
	}
	return frequency_dict.get(frequency_name)


@frappe.whitelist()
def get_end_date(start_date, frequency):
	start_date = getdate(start_date)
	frequency = frequency.lower() if frequency else "monthly"
	kwargs = get_frequency_kwargs(frequency) if frequency != "bimonthly" else get_frequency_kwargs("monthly")
	print(kwargs, "kwargs ==============")

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency != "bimonthly":
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date="")


def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		import calendar
		import datetime

		diff_mnt = cint(month) - cint(ysd.month)
		if diff_mnt < 0:
			diff_mnt = 12 - int(ysd.month) + cint(month)
		msd = ysd + relativedelta(months=diff_mnt)  # month start date
		month_days = cint(calendar.monthrange(cint(msd.year), cint(month))[1])  # days in month
		mid_start = datetime.date(msd.year, cint(month), 16)  # month mid start date
		mid_end = datetime.date(msd.year, cint(month), 15)  # month mid end date
		med = datetime.date(msd.year, cint(month), month_days)  # month end date
		return frappe._dict(
			{
				"year": msd.year,
				"month_start_date": msd,
				"month_end_date": med,
				"month_mid_start_date": mid_start,
				"month_mid_end_date": mid_end,
				"month_days": month_days,
			}
		)
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))


def log_payroll_failure(process, payroll_entry, error):
	error_log = frappe.log_error(
		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
	)
	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

	try:
		if isinstance(message_log, str):
			error_message = json.loads(message_log).get("message")
		else:
			error_message = message_log.get("message")
	except Exception:
		error_message = message_log

	error_message += "\n" + _("Check Error Log {0} for more details.").format(
		get_link_to_form("Error Log", error_log.name)
	)

	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})


def create_salary_slips_for_employees(employees, args, publish_progress=True):
	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)

	try:
		salary_slips_exist_for = get_existing_salary_slips(employees, args)
		count = 0

		employees = list(set(employees) - set(salary_slips_exist_for))
		for emp in employees:
			args.update({"doctype": "Salary Slip", "employee": emp})
			frappe.get_doc(args).insert()

			count += 1
			if publish_progress:
				frappe.publish_progress(
					count * 100 / len(employees),
					title=_("Creating Salary Slips..."),
				)

		payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})

		if salary_slips_exist_for:
			frappe.msgprint(
				_(
					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
				title=_("Message"),
				indicator="orange",
			)

	except Exception as e:
		if not frappe.in_test:
			frappe.db.rollback()
		log_payroll_failure("creation", payroll_entry, e)

	finally:
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep
		frappe.publish_realtime("completed_salary_slip_creation", user=frappe.session.user)


def show_payroll_submission_status(submitted, unsubmitted, payroll_entry):
	if not submitted and not unsubmitted:
		frappe.msgprint(
			_(
				"No salary slip found to submit for the above selected criteria OR salary slip already submitted"
			)
		)
	elif submitted and not unsubmitted:
		frappe.msgprint(
			_("Salary Slips submitted for period from {0} to {1}").format(
				payroll_entry.start_date, payroll_entry.end_date
			),
			title=_("Success"),
			indicator="green",
		)
	elif unsubmitted:
		frappe.msgprint(
			_("Could not submit some Salary Slips: {}").format(
				", ".join(get_link_to_form("Salary Slip", entry) for entry in unsubmitted)
			),
			title=_("Failure"),
			indicator="red",
		)


def get_existing_salary_slips(employees, args):
	SalarySlip = frappe.qb.DocType("Salary Slip")

	return (
		frappe.qb.from_(SalarySlip)
		.select(SalarySlip.employee)
		.distinct()
		.where(
			(SalarySlip.docstatus != 2)
			& (SalarySlip.company == args.company)
			& (SalarySlip.payroll_entry == args.payroll_entry)
			& (SalarySlip.start_date >= args.start_date)
			& (SalarySlip.end_date <= args.end_date)
			& (SalarySlip.employee.isin(employees))
		)
	).run(pluck=True)


def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
	try:
		submitted = []
		unsubmitted = []
		frappe.flags.via_payroll_entry = True
		count = 0

		for entry in salary_slips:
			salary_slip = frappe.get_doc("Salary Slip", entry[0])
			if salary_slip.net_pay < 0:
				unsubmitted.append(entry[0])
			else:
				try:
					salary_slip.submit()
					submitted.append(salary_slip)
				except frappe.ValidationError:
					unsubmitted.append(entry[0])

			count += 1
			if publish_progress:
				frappe.publish_progress(
					count * 100 / len(salary_slips), title=_("Submitting Salary Slips...")
				)

		if submitted:
			payroll_entry.make_accrual_jv_entry(submitted)
			payroll_entry.email_salary_slip(submitted)
			payroll_entry.db_set({"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""})

		show_payroll_submission_status(submitted, unsubmitted, payroll_entry)

	except Exception as e:
		if not frappe.in_test:
			frappe.db.rollback()
		log_payroll_failure("submission", payroll_entry, e)

	finally:
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep
		frappe.publish_realtime("completed_salary_slip_submission", user=frappe.session.user)

	frappe.flags.via_payroll_entry = False


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
	# nosemgrep: frappe-semgrep-rules.rules.frappe-using-db-sql
	return frappe.db.sql(
		f"""
		select name from `tabPayroll Entry`
		where `{searchfield}` LIKE %(txt)s
		and name not in
			(select reference_name from `tabJournal Entry Account`
				where reference_type="Payroll Entry")
		order by name limit %(start)s, %(page_len)s""",
		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
	)


def get_employee_list(
	filters: frappe._dict,
	searchfield=None,
	search_string=None,
	fields: list[str] | None = None,
	as_dict=True,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	sal_struct = get_salary_structure(
		filters.company,
		filters.currency,
		filters.salary_slip_based_on_timesheet,
		filters.payroll_frequency,
	)

	if not sal_struct:
		return []

	emp_list = get_filtered_employees(
		sal_struct,
		filters,
		searchfield,
		search_string,
		fields,
		as_dict=as_dict,
		limit=limit,
		offset=offset,
		ignore_match_conditions=ignore_match_conditions,
	)

	if as_dict:
		employees_to_check = {emp.employee: emp for emp in emp_list}
	else:
		employees_to_check = {emp[0]: emp for emp in emp_list}

	return remove_payrolled_employees(employees_to_check, filters.start_date, filters.end_date)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters)

	if not filters.payroll_frequency:
		frappe.throw(_("Select Payroll Frequency."))

	employee_list = get_employee_list(
		filters,
		searchfield=searchfield,
		search_string=txt,
		fields=["name", "employee_name"],
		as_dict=False,
		limit=page_len,
		offset=start,
	)

	return employee_list


def get_salary_withholdings(
	start_date: str,
	end_date: str,
	employee: str | None = None,
	pluck: str | None = None,
) -> list[str] | list[dict]:
	Withholding = frappe.qb.DocType("Salary Withholding")
	WithholdingCycle = frappe.qb.DocType("Salary Withholding Cycle")
	withheld_salaries = (
		frappe.qb.from_(Withholding)
		.join(WithholdingCycle)
		.on(WithholdingCycle.parent == Withholding.name)
		.select(
			Withholding.employee,
			Withholding.name.as_("salary_withholding"),
			WithholdingCycle.name.as_("salary_withholding_cycle"),
		)
		.where(
			(WithholdingCycle.from_date == start_date)
			& (WithholdingCycle.to_date == end_date)
			& (WithholdingCycle.docstatus == 1)
			& (WithholdingCycle.is_salary_released != 1)
		)
	)

	if employee:
		withheld_salaries = withheld_salaries.where(Withholding.employee == employee)

	if pluck:
		return withheld_salaries.run(pluck=pluck)
	return withheld_salaries.run(as_dict=True)
