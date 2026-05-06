frappe.listview_settings['W2 Form Details'] = {
    onload(listview) {
        // Hide core Print action (DOM-safe)
        setTimeout(() => {
            listview.page.menu
                .find('span.menu-item-label[data-label="Print"]')
                .closest('li')
                .hide();
        }, 100);

        listview.page.add_action_item(__('Bulk W2 Print'), () => {
            const names = listview.get_checked_items().map(d => d.name);

            if (!names.length) {
                frappe.msgprint(__('Please select records'));
                return;
            }

            const url =
                '/api/method/us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.bulk_w2_print'
                + '?names=' + encodeURIComponent(JSON.stringify(names));

            window.open(url);
        });
    }
};
