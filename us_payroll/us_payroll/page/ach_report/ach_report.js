frappe.pages['ach-report'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Payroll ACH',
		single_column: true
	});
}