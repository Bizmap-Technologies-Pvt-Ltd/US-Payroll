frappe.ui.form.on("Salary Component", {
	refresh: function (frm) {
		frm.trigger("set_flag");
	},

	custom_is_this_insurance_component: function (frm) {
		if (frm.doc.custom_is_this_insurance_component) {
			frm.set_value("custom_insurance_component", 1);
		} else {
			frm.set_value("custom_insurance_component", 0);
		}
		frm.refresh_field("custom_insurance_component");
	},

	custom_is_this_employers_insurance_component: function (frm) {
		if (frm.doc.custom_is_this_employers_insurance_component) {
			frm.set_value("custom_insurance_component", 1);
		} else {
			frm.set_value("custom_insurance_component", 0);
		}
		frm.refresh_field("custom_insurance_component");
	},

	set_flag: function (frm) {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Salary Structure",
				filters: { docstatus: 1 },
				fields: ["name"],
			},
			callback: function (res) {
				if (res.message && res.message.length > 0) {
					res.message.forEach((structure) => {
						// Get full Salary Structure doc
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Salary Structure",
								name: structure.name,
							},
							callback: function (r) {
								if (r.message && r.message.deductions) {
									let updated = false;

									r.message.deductions.forEach((deduction) => {
										if (deduction.salary_component === frm.doc.name) {
											deduction.do_not_include_in_total =
												frm.doc.do_not_include_in_total;

											updated = true;
										}
									});

									if (updated) {
										frappe.call({
											method: "frappe.client.save",
											args: {
												doc: r.message,
											},
											callback: function (saveRes) {
												console.log(
													"Updated Salary Structure:",
													saveRes.message.name
												);
											},
										});
									}
								}
							},
						});
					});
				}
			},
		});
	},
});
