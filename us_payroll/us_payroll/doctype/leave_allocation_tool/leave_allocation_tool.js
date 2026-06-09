// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

/* global erpnext */

frappe.ui.form.on("Leave Allocation Tool", {
	onload: function (frm) {
		frm.trigger("hide_add_row_btn");
		frm.trigger("set_fiscal_year_dates");
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.trigger("hide_add_row_btn");

		if (frm.fields_dict.get_employees) {
			frm.fields_dict.get_employees.$wrapper
				.find("button")
				.removeClass("btn-default btn-xs")
				.addClass("btn-primary");
		}

		if (frm.fields_dict.generate_leave_allocation_records) {
			frm.fields_dict.generate_leave_allocation_records.$wrapper
				.find("button")
				.removeClass("btn-default btn-xs")
				.addClass("btn-primary");
		}
	},

	hide_add_row_btn: function (frm) {
		$('*[data-fieldname="leave_allocation_details"]').find(".grid-add-row").remove();
		$('*[data-fieldname="leave_allocation_details"]').find(".grid-row-check").remove();
	},

	set_fiscal_year_dates: function (frm) {
		if (!frm.doc.from_date)
			frm.set_value(
				"from_date",
				erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1]
			);
		if (!frm.doc.to_date)
			frm.set_value(
				"to_date",
				erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2]
			);
	},

	get_departmentwise_employees: function (frm) {
		if (!frm.doc.leave_type) {
			frappe.throw(__("Please select leave type."));
		}

		frappe.call({
			method: "us_payroll.us_payroll.doctype.leave_allocation_tool.leave_allocation_tool.get_employees",
			args: {
				department: frm.doc.department || null,
				leave_type: frm.doc.leave_type,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date,
			},
			callback: function (r) {
				if (r.message) {
					frm.clear_table("leave_allocation_details");
					r.message.forEach((emp) => {
						let row = frm.add_child("leave_allocation_details");
						row.employee = emp.name;
						row.employee_name = emp.employee_name;
						row.department_id = emp.custom_department_name;
						row.department = emp.custom_department_number;
						row.leave_type = frm.doc.leave_type;

						if (frm.doc.leave_type == "PTO") {
							row.balanced_leaves = emp.balanced_pto_leaves;
							row.total_leaves_allocated = emp.total_leaves_allocated_pto;
						} else {
							row.balanced_leaves = emp.balanced_ct_leaves;
							row.total_leaves_allocated = emp.total_leaves_allocated_ct;
						}
					});

					frm.refresh_field("leave_allocation_details");
				}
			},
		});
	},

	get_employees: function (frm) {
		frm.trigger("get_departmentwise_employees");
	},

	generate_leave_allocation_records: function (frm) {
		if (!frm.doc.leave_allocation_details || frm.doc.leave_allocation_details.length === 0) {
			frappe.msgprint(__("No employees found in table."));
			return;
		}

		frappe.call({
			method: "us_payroll.us_payroll.doctype.leave_allocation_tool.leave_allocation_tool.generate_leave_allocations",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				if (!r.message) return;
				let messages = [];
				if (r.message.created && r.message.created.length > 0) {
					r.message.created.forEach((c) => {
						messages.push(
							`${c.leave_type} Leave Allocation record created for the employee ${c.employee}.`
						);
					});
				}

				if (r.message.skipped && r.message.skipped.length > 0) {
					r.message.skipped.forEach((s) => {
						messages.push(
							`${s.leave_type} Leave Allocation record updated for the employee ${s.employee}.`
						);
					});
				}

				frappe.msgprint(messages.join("<br>"));
			},
		});
	},
});

frappe.ui.form.on("Leave Allocation Details", {
	new_leaves_allocated: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.new_leaves_allocated) {
			let updated_allocated_leaves = row.new_leaves_allocated + row.total_leaves_allocated;
			console.log(updated_allocated_leaves, "updated_allocated_leaves");
			frappe.model.set_value(cdt, cdn, "total_leaves_allocated", updated_allocated_leaves);
		}
	},
});
