frappe.pages["unemployment-ach"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Unemployment ACH",
		single_column: true,
	});

	page.add_field({
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options: "Company",
		reqd: 1,
		default: frappe.defaults.get_user_default("Company"),
		hidden: 1,
	});

	page.add_field({
		fieldname: "year",
		label: __("Year"),
		fieldtype: "Link",
		options: "Fiscal Year",
		reqd: 1,
		default: new Date().getFullYear().toString(),
	});

	page.add_field({
		fieldname: "quarter",
		label: __("Quarter"),
		fieldtype: "Select",
		options: ["", "Quarter1", "Quarter2", "Quarter3", "Quarter4"],
	});

	page.set_primary_action("Generate Unemployment ACH File", () => {
		let year = page.fields_dict.year.get_value();
		let quarter = page.fields_dict.quarter.get_value();

		if (!year || !quarter) {
			frappe.msgprint(__("Please select both Year and Quarter"));
			return;
		}

		frappe.call({
			method: "us_payroll.us_payroll.page.unemployment_ach.unemployment_ach.get_unemployment_report_data",
			args: {
				year: year,
				quarter: quarter,
			},
			callback: function (r) {
				if (r.message && r.message.file_url) {
					frappe.msgprint(__("Unemployment ACH File Generated Successfully"));
					const link = document.createElement("a");
					link.href = r.message.file_url;
					link.download = "unemployment_ach_file.txt";
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			},
		});
	});
};
