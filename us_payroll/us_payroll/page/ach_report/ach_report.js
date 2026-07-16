frappe.pages["ach-report"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "ACH Report",
		single_column: true,
	});

	let payroll_entry;

	// Add a Payroll Entry field with formatted dropdown
	let field = page.add_field({
		label: "Payroll Entry",
		fieldname: "payroll_entry",
		fieldtype: "Link",
		options: "Payroll Entry",
		get_query: function () {
			return {
				filters: {
					docstatus: 1,
				},
			};
		},
		onchange: function () {
			payroll_entry = field.get_value();

			if (payroll_entry) {
				frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Payroll Entry",
						name: payroll_entry,
					},
					callback: function (r) {
						if (r.message) {
							let start_date = r.message.start_date;
							let end_date = r.message.end_date;

							// Customize dropdown display
							$(
								`[data-fieldname="payroll_entry"] .awesomplete ul li[data-value="${payroll_entry}"]`
							).html(`
                                <div>
                                    <strong>${payroll_entry}</strong><br>
                                    <span style="color: #888;">${start_date} - ${end_date}</span>
                                </div>
                            `);
						}
					},
				});
			}
		},
	});

	const urlParams = new URLSearchParams(window.location.search);
	var payroll_entry_value = urlParams.get("payroll_entry");
	field.set_value(payroll_entry_value);

	// Add a button to generate the ACH file
	page.set_primary_action("Generate ACH File", () => {
		if (!payroll_entry) {
			frappe.msgprint(__("Please select a Payroll Entry"));
			return;
		}

		frappe.call({
			method: "us_payroll.us_payroll.page.ach_report.ach_report.generate_ach_file",
			args: {
				payroll_entry: payroll_entry,
			},
			callback: function (r) {
				if (r.message) {
					frappe.msgprint(__("ACH File Generated Successfully"));

					// Automatically download the generated file
					const link = document.createElement("a");
					link.href = r.message;
					link.download = "ach_file.txt";
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			},
		});
	});
};
