frappe.ui.form.on("Leave Allocation", {
	onload: function (frm) {
		frm.trigger("set_fiscal_year_dates");
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

	new_leaves_allocated: function (frm) {
		if (!frm.__islocal && frm.doc.new_leaves_allocated) {
			frappe.call({
				method: "us_payroll.custom_script.leave_allocation.get_old_leave_allocation_amount",
				args: {
					employee: frm.doc.employee,
					amount: parseFloat(frm.doc.new_leaves_allocated),
				},
				callback: function (r) {
					let res = r.message;
					if (res.status === "exists_different_amount") {
						frappe.confirm(
							`Previous allocation was ${res.existing_amount} for employee ${frm.doc.employee}. Do you want to update it to ${res.new_amount}?`,
							function () {
								show_popup_for_reason(frm, res.existing_amount, res.new_amount);
							},
							function () {
								frm.set_value(
									"new_leaves_allocated",
									parseFloat(res.existing_amount)
								);
								frappe.msgprint("Operation cancelled.");
							}
						);
					} else if (res.status === "created") {
						frm.save();
					}
				},
			});
		}
	},
});

function show_popup_for_reason(frm, existing_amount, new_amount) {
	let dialog = new frappe.ui.Dialog({
		title: "Reason for Change",
		fields: [
			{
				label: "Reason",
				fieldname: "reason",
				fieldtype: "Small Text",
				reqd: 1,
			},
			{
				label: "New amount",
				fieldname: "new_amount",
				fieldtype: "Currency",
				default: new_amount,
				read_only: 1,
			},
		],
		primary_action_label: "Submit",
		primary_action(values) {
			frappe.call({
				method: "us_payroll.custom_script.leave_allocation.update_allocated_leaves",
				args: {
					employee: frm.doc.employee,
					amount: new_amount,
					reason: values.reason,
					existing_amount: existing_amount,
				},
				callback: function (res) {
					frm.set_value("custom_allocation_change_reason", values.reason);
					frm.set_value("custom_previous_leaves_allocated", existing_amount);
					frm.set_value("new_leaves_allocated", parseFloat(values.new_amount));

					frappe.msgprint("Leave allocation updated successfully.");
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}
