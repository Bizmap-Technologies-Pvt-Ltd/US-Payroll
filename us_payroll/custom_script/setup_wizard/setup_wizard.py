import frappe

def setup_wizard_complete(args=None):
    company = frappe.defaults.get_global_default("company")
    abbr = frappe.db.get_value("Company", company, "abbr")

    # Update Salary Structure to actual company
    if frappe.db.exists("Salary Structure", "Standard Salary Template"):
        frappe.db.set_value("Salary Structure", "Standard Salary Template", "company", company)

 #    # Update Salary Components to actual company and accounts
 #    components = frappe.get_all("Salary Component", fields=["name", "salary_component"])
 #    for comp in components:
 #        # set company
 #        # frappe.db.set_value("Salary Component", comp.name, "company", company)

 #        # map account type based on component
 #        if comp.salary_component in ["Hourly", "Overtime", "Salary"]:
 #            account_name = f"Expense Account"
 #            account_type = "Expense"
 #            parent = f"Expenses - {abbr}"
        
 #        elif comp.salary_component in ["FIT", "Dental", "Social Security Tax - Employee", "Social Security Tax - Employer", 
	# 								   "Medicare Tax EE", "Medicare Tax ER", "TMRS (Employee)", "TMRS (Employer)"]:
 #            account_name = f"Liability Account"
 #            account_type = "Liability"
 #            parent = f"Current Liabilities - {abbr}"
        
 #        else:
 #            account_name = f"Misc Expense - {abbr}"
 #            account_type = "Expense"
 #            parent = f"Expenses - {abbr}"

 #        # create account if missing
 #        if not frappe.db.exists("Account", {"account_name": account_name, "company": company}):
 #            doc = frappe.get_doc({
 #                "doctype": "Account",
 #                "account_name": account_name,
 #                "company": company,
 #                "account_type": account_type,
 #                "parent_account": parent
 #            })
 #            doc.insert(ignore_permissions=True)

 #        # update salary component accounts child table
 #        frappe.db.sql("""
 #            DELETE FROM `tabSalary Component Account`
 #            WHERE parent=%s
 #        """, comp.name)

 #        sca = frappe.get_doc({
 #            "doctype": "Salary Component Account",
 #            "parent": comp.name,
 #            "company": company,
 #            "account": account_name
 #        })
 #        sca.insert(ignore_permissions=True)

 #    # frappe.db.commit()

	# frappe.db.set_value("System Settings", "System Settings", "setup_wizard_completed", 1)
	# frappe.db.commit()

