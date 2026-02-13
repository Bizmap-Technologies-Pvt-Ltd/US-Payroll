
frappe.ui.form.on('Salary Structure Assignment', {
	
    setup: function(frm) {
		frm.set_query("salary_component", "custom_employee_insurance_deduction", function (doc, cdt, cdn) {
			return {
					filters: {
						type: "Deduction",
                        custom_insurance_component: 1	
                    }
			};
		});

		frm.set_query("salary_component", "custom_employee_earnings", function (doc, cdt, cdn) {
			return {
					filters: {
						type: "Earning"                    
                    }
			};
		});
	},

});

frappe.ui.form.on('Employee Insurance Deduction', {   // child doctype
    salary_component(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.salary_component) return;

        frappe.db.get_value(
            "Salary Component",
            row.salary_component,
            [
                "custom_is_employer_component",
                "do_not_include_in_total",
                "custom_is_this_insurance_component",
                "custom_is_this_employers_insurance_component",
                "custom_insurance_component",
                "custom_is_this_pretax_component",
                "custom_is_this_fit_component",
                "custom_federal_income_tax_and_additional_withholdings"
            ]
        ).then(r => {
            if (!r || !r.message) return;

            const data = r.message;

            // Explicit mapping: Salary Component → Child Table
            const field_map = {
                custom_is_employer_component: "is_employer_component",
                do_not_include_in_total: "do_not_include_in_total",
                custom_is_this_insurance_component: "is_this_employees_insurance_component",
                custom_is_this_employers_insurance_component: "is_this_employers_insurance_component",
                custom_insurance_component: "insurance_component",
                custom_is_this_pretax_component: "is_this_pre_tax_component",
                custom_is_this_fit_component: "is_this_income_tax_slab_component",
                custom_federal_income_tax_and_additional_withholdings:
                    "federal_income_tax_and_additional_withholdings"
            };

            Object.keys(field_map).forEach(sc_field => {
                frappe.model.set_value(
                    cdt,
                    cdn,
                    field_map[sc_field],
                    data[sc_field]
                );
            });
        });
    }
});


