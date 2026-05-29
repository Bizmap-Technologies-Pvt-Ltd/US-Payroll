
frappe.ui.form.on('Salary Structure Assignment', {
	
	setup: function(frm) {

		frm.set_query('salary_component', 'custom_earnings', function() {
			return {
					filters: {
						type: "earning"
					}
			};
		})

		frm.set_query('salary_component', 'custom_deductions', function() {
			return {
					filters: {
						type: "deduction"
					}
			};
		})
		frm.trigger("set_default_company");


		frm.set_query("salary_component", "custom_employee_insurance_deduction", function (doc, cdt, cdn) {
			return {
					filters: {
						type: "Deduction",
						custom_insurance_component: 1	
					}
			};
		});

		frm.set_query("earning_component", "custom_employee_earnings", function (doc, cdt, cdn) {
			return {
					filters: {
						type: "Earning",
						custom_is_variable_earning: 1                   
					}
			};
		});
	},

	refresh:function(frm){
		frm.trigger("set_default_company");
	},

	onload:function(frm){
		frm.trigger("set_default_company");
	},

	validate:function(frm){
		frm.trigger("set_default_company");
	},

	set_default_company:function(frm){
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: 'us_payroll.custom_script.salary_structure_assignment.get_global_defaults_values',
				args: {
					doctype: "Global Defaults",                 
				},
				callback: function(r) {
					if (r.message) {
						default_company = r.message.company
						frm.set_value('company', default_company);
					}
				}
			});
		}
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.db.get_doc('Employee', frm.doc.employee).then(emp => {
				frm.set_value("income_tax_slab", emp.custom_filing_method);
			});
		}
	},

	salary_structure: function(frm) {
		if (frm.doc.salary_structure) {
			// Fetch data from the Salary Structure doctype
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Salary Structure',
					name: frm.doc.salary_structure
				},
				callback: function(r) {
					if (r.message) {
						const salary_structure = r.message;
						frm.clear_table('custom_earnings');
						frm.clear_table('custom_deductions');

						// Copy earnings from Salary Structure to custom_earnings
						if (salary_structure.earnings) {
							salary_structure.earnings.forEach(earning => {
								let row = frm.add_child('custom_earnings');
								row.salary_component = earning.salary_component;
								row.amount = earning.amount;
								row.abbr = earning.abbr;
								row.year_to_date = earning.year_to_date;
								row.additional_salary = earning.additional_salary;
								row.is_recurring_additional_salary = earning.is_recurring_additional_salary;
								row.statistical_component = earning.statistical_component;
								row.depends_on_payment_days = earning.depends_on_payment_days;
								row.exempted_from_income_tax = earning.exempted_from_income_tax;
								row.is_tax_applicable = earning.is_tax_applicable;
								row.is_flexible_benefit = earning.is_flexible_benefit;
								row.variable_based_on_taxable_salary = earning.variable_based_on_taxable_salary;
								row.do_not_include_in_total = earning.do_not_include_in_total;
								row.do_not_include_in_accounts = earning.do_not_include_in_accounts;
								row.deduct_full_tax_on_selected_payroll_date = earning.deduct_full_tax_on_selected_payroll_date;
								row.condition = earning.condition;
								row.amount_based_on_formula = earning.amount_based_on_formula;
								row.formula = earning.formula;
								row.default_amount = earning.default_amount;
								row.additional_amount = earning.additional_amount;
								row.tax_on_flexible_benefit = earning.tax_on_flexible_benefit;
								row.tax_on_additional_salary = earning.tax_on_additional_salary;
							});
						}

						// Copy deductions from Salary Structure to custom_deductions
						if (salary_structure.deductions) {
							salary_structure.deductions.forEach(deduction => {
								let row = frm.add_child('custom_deductions');
								row.salary_component = deduction.salary_component;
								row.amount = deduction.amount;
								row.abbr = deduction.abbr;
								row.year_to_date = deduction.year_to_date;
								row.additional_salary = deduction.additional_salary;
								row.is_recurring_additional_salary = deduction.is_recurring_additional_salary;
								row.statistical_component = deduction.statistical_component;
								row.depends_on_payment_days = deduction.depends_on_payment_days;
								row.exempted_from_income_tax = deduction.exempted_from_income_tax;
								row.is_tax_applicable = deduction.is_tax_applicable;
								row.is_flexible_benefit = deduction.is_flexible_benefit;
								row.variable_based_on_taxable_salary = deduction.variable_based_on_taxable_salary;
								row.do_not_include_in_total = deduction.do_not_include_in_total;
								row.do_not_include_in_accounts = deduction.do_not_include_in_accounts;
								row.deduct_full_tax_on_selected_payroll_date = deduction.deduct_full_tax_on_selected_payroll_date;
								row.condition = deduction.condition;
								row.amount_based_on_formula = deduction.amount_based_on_formula;
								row.formula = deduction.formula;
								row.default_amount = deduction.default_amount;
								row.additional_amount = deduction.additional_amount;
								row.tax_on_flexible_benefit = deduction.tax_on_flexible_benefit;
								row.tax_on_additional_salary = deduction.tax_on_additional_salary;
							});
						}
						frm.refresh_field('custom_earnings');
						frm.refresh_field('custom_deductions');
					}
				}
			});
		} else {
			// Clear the child tables if no salary structure is selected
			frm.clear_table('custom_earnings');
			frm.clear_table('custom_deductions');
			frm.refresh_field('custom_earnings');
			frm.refresh_field('custom_deductions');
		}
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
				"do_not_include_in_accounts",
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
				do_not_include_in_accounts: "do_not_include_in_accounts",
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
	},

	tax_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		
		if (row.tax_type === "Before Tax") {
			row.is_this_pre_tax_component = 1;   // check
		} else if (row.tax_type === "After Tax") {
			row.is_this_pre_tax_component = 0;   // uncheck
		}
		frm.refresh_field("custom_employee_insurance_deduction");
	}

});


