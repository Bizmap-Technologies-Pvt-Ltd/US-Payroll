import frappe
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period_days,
	get_period_factor,
)

def get_benefit_component_amount(
	employee, start_date, end_date, salary_component, sal_struct, payroll_frequency, payroll_period
):
	if not payroll_period:
		frappe.msgprint(
			_("Start and end dates not in a valid Payroll Period, cannot calculate {0}").format(
				salary_component
			)
		)
		return False

	# Considering there is only one application for a year
	benefit_application = frappe.db.sql(
		"""
		select name
		from `tabEmployee Benefit Application`
		where
			payroll_period=%(payroll_period)s
			and employee=%(employee)s
			and docstatus = 1
	""",
		{"employee": employee, "payroll_period": payroll_period.name},
	)

	current_benefit_amount = 0.0
	component_max_benefit, depends_on_payment_days = frappe.db.get_value(
		"Salary Component", salary_component, ["max_benefit_amount", "depends_on_payment_days"]
	)

	benefit_amount = 0
	if benefit_application:
		benefit_amount = frappe.db.get_value(
			"Employee Benefit Application Detail",
			{"parent": benefit_application[0][0], "earning_component": salary_component},
			"amount",
		)
	elif component_max_benefit:
		benefit_amount = get_benefit_amount_based_on_pro_rata(sal_struct, component_max_benefit)

	current_benefit_amount = 0
	if benefit_amount:
		total_sub_periods = get_period_factor(
			employee, start_date, end_date, payroll_frequency, payroll_period, depends_on_payment_days
		)[0]

		current_benefit_amount = benefit_amount / total_sub_periods

	return current_benefit_amount


def get_benefit_amount_based_on_pro_rata(sal_struct, component_max_benefit):
	max_benefits_total = 0
	benefit_amount = 0
	for d in sal_struct.get("earnings"):
		if d.is_flexible_benefit == 1:
			component = frappe.db.get_value(
				"Salary Component",
				d.salary_component,
				["max_benefit_amount", "pay_against_benefit_claim"],
				as_dict=1,
			)
			if not component.pay_against_benefit_claim:
				max_benefits_total += component.max_benefit_amount

	if max_benefits_total > 0:
		benefit_amount = sal_struct.max_benefits * component.max_benefit_amount / max_benefits_total
		if benefit_amount > component_max_benefit:
			benefit_amount = component_max_benefit

	return benefit_amount