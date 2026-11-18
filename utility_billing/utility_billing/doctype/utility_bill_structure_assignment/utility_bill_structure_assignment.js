frappe.ui.form.on('Utility Bill Structure Assignment', {
    async refresh(frm) {
        frm.set_query('utility_bill_structure', () => ({filters: {docstatus: 1, company: frm.doc.company}}));
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Change Bill Structure'), () => {
                frappe.prompt([
                    {fieldname: 'new_structure', fieldtype: 'Link', options: 'Utility Bill Structure', label: __('New Bill Structure'), reqd: 1,
                     get_query: () => ({filters: {docstatus: 1, company: frm.doc.company, name: ['!=', frm.doc.utility_bill_structure]}})},
                    {fieldname: 'effective_date', fieldtype: 'Date', label: __('Effective Date'), reqd: 1, default: frappe.datetime.get_today()}
                ], values => frm.call('change_structure', values).then(r => {
                    if (r.message) frappe.set_route('Form', 'Utility Bill Structure Assignment', r.message);
                }), __('Change Bill Structure'), __('Create Assignment'));
            });
            const structure = await frappe.db.get_doc('Utility Bill Structure', frm.doc.utility_bill_structure);
            if (structure.metered_billing) {
                frm.add_custom_button(__('Create Meter Reading'), () => {
                    frappe.new_doc('Meter Reading', {customer: frm.doc.customer, company: frm.doc.company,
                        property: frm.doc.property, date: frappe.datetime.get_today()});
                });
            } else if (frm.doc.billing_auto_repeat) {
                frm.add_custom_button(__('View Billing Schedule'), () => frappe.set_route('Form', 'Auto Repeat', frm.doc.billing_auto_repeat));
            } else {
                frm.add_custom_button(__('Start Billing'), () => {
                    frappe.prompt([
                        {fieldname: 'billing_date', fieldtype: 'Date', label: __('First Billing Date'), reqd: 1,
                         default: frm.doc.start_date > frappe.datetime.get_today() ? frm.doc.start_date : frappe.datetime.get_today()},
                        {fieldname: 'reference_doctype', fieldtype: 'Select', label: __('Create'),
                         options: 'Sales Invoice\nSales Order', default: 'Sales Invoice', reqd: 1}
                    ], values => frm.call('start_billing', values).then(r => {
                        if (r.message) frappe.set_route('Form', r.message.doctype, r.message.name);
                    }), __('Start Monthly Billing'), __('Create Bill and Schedule'));
                });
            }
        }
    }
});
