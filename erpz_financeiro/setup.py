import frappe
import json, os

def setup_desktop_and_sidebar():
    icon_name = "ERPZ Financeiro"
    icon_data = {
        "label": "ERPZ Financeiro",
        "icon": "wallet",
        "icon_type": "Link",
        "link_type": "Workspace Sidebar",
        "link_to": "ERPZ Financeiro",
        "parent_icon": "",
        "hidden": 0,
        "standard": 1,
        "app": "erpz_financeiro",
        "idx": 11
    }

    if frappe.db.exists("Desktop Icon", icon_name):
        frappe.db.set_value("Desktop Icon", icon_name, icon_data)
    else:
        doc = frappe.new_doc("Desktop Icon")
        doc.name = icon_name
        doc.update(icon_data)
        doc.insert(ignore_permissions=True)

    # Sync Workspace Sidebar
    sb_file = "/home/frappe/frappe-bench/apps/erpz_financeiro/erpz_financeiro/workspace_sidebar/erpz_financeiro.json"
    if os.path.exists(sb_file):
        with open(sb_file, "r", encoding="utf-8") as fp:
            sb_data = json.load(fp)

        if frappe.db.exists("Workspace Sidebar", "ERPZ Financeiro"):
            sb = frappe.get_doc("Workspace Sidebar", "ERPZ Financeiro")
            sb.items = []
            for it in sb_data.get("items", []):
                sb.append("items", it)
            sb.save(ignore_permissions=True)
        else:
            sb = frappe.new_doc("Workspace Sidebar")
            sb.update(sb_data)
            sb.insert(ignore_permissions=True)

def after_install():
    pass

def after_migrate():
    setup_desktop_and_sidebar()
    frappe.db.commit()
