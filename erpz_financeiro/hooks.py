app_name = "erpz_financeiro"
app_title = "ERPZ Financeiro"
app_publisher = "ERPZ"
app_description = "Gestão Financeira, Cobrança Bancária CNAB 240/400, Boletos Registrados e PIX Dinâmico"
app_email = "dev@erpz.io"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["frappe", "erpnext"]

after_install = "erpz_financeiro.setup.after_install"
after_migrate = "erpz_financeiro.setup.after_migrate"

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js"
}
