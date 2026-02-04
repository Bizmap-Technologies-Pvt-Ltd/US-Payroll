
frappe.ui.form.on('Salary Structure Assignment', {
	
    setup: function(frm) {
		frm.set_query("salary_component", "custom_employee_insurance_deduction", function (doc, cdt, cdn) {
			return {
					filters: {
						type: "Deduction",
                        custom_insurance_component:true					}
			};
		})
	},

});


