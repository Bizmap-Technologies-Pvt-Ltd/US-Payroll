import frappe

# Whitelist of allowed templates (static, bundled with app)
ALLOWED_TEMPLATES = {
	"employee_gross_earning": "us_payroll/us_payroll/report/employee_gross_earning/employee_gross_earning.html",
	"payroll_detail_report_by_posted_date": "us_payroll/us_payroll/report/payroll_detail_report_by_posted_date/payroll_detail_report_by_posted_date.html",
	# add other report templates here
}

def safe_render(template_key: str, context: dict) -> str:
	"""
	Render a Jinja template from a static whitelist.
	Prevents user-controlled template injection.
	"""
	if template_key not in ALLOWED_TEMPLATES:
		raise ValueError(f"Template '{template_key}' is not whitelisted")

	template_path = ALLOWED_TEMPLATES[template_key]

	# Explicitly suppress Semgrep warning here with justification
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	return frappe.render_template(template_path, context)
