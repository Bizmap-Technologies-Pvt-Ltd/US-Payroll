frappe.pages['tmrs-ach'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'TMRS ACH',
		single_column: true
	});


	// Add Company field (hidden)
	page.add_field({
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options: "Company",
		reqd: 1,
		default: frappe.defaults.get_user_default("Company"),
		hidden: 1
	});

	// Add Year field
	page.add_field({
		fieldname: "year",
		label: __("Year"),
		fieldtype: "Link",
		options: "Fiscal Year",
		reqd: 1,
		default: (new Date()).getFullYear().toString()
	});

	// Add Month field
	page.add_field({
		fieldname: "month",
		label: __("Month"),
		fieldtype: "Select",
		options: [
			"", "January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		]
	});




	// const urlParams = new URLSearchParams(window.location.search);
 //    var payroll_entry_value = urlParams.get('payroll_entry'); 
 //    field.set_value(payroll_entry_value)


	// Add a button to generate the ACH file based on Year and Month
	page.set_primary_action('Generate TMRS ACH File', () => {
		let year = page.fields_dict.year.get_value();
		let month = page.fields_dict.month.get_value();

		console.log(year, month, "year month ==========");

		if (!year || !month) {
			frappe.msgprint(__('Please select both Year and Month'));
			return;
		}

		frappe.call({
			method: 'us_payroll.us_payroll.page.tmrs_ach.tmrs_ach.get_tmrs_report_data',
			args: {
				year: year,
				month: month
			},
			callback: function(r) {
				console.log(r, "rrrrrrrrrrrrrrrrrrrrrr ============");
				if (r.message && r.message.file_url) {
					frappe.msgprint(__('TMRS ACH File Generated Successfully'));

					// Automatically download the generated file
					const link = document.createElement('a');
					link.href = r.message.file_url;
					link.download = 'tmrs_ach_file.txt';
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			}
		});
	});

}