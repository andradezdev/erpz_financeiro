frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__('Gerar Boleto Bancário'), function() {
                frappe.db.get_list('Configuracao Conta Bancaria', {
                    filters: { empresa: frm.doc.company },
                    fields: ['name', 'banco', 'banco_nome']
                }).then(contas => {
                    if (!contas || contas.length === 0) {
                        frappe.msgprint(__('Nenhuma Conta Bancária de Cobrança configurada para a empresa {0}. Cadastre uma no menu ERPZ Financeiro.', [frm.doc.company]));
                        return;
                    }

                    let options = contas.map(c => c.name).join('\n');
                    frappe.prompt([
                        {
                            fieldname: 'conta_bancaria',
                            fieldtype: 'Select',
                            label: __('Conta Bancária de Cobrança'),
                            options: options,
                            default: contas[0].name,
                            reqd: 1
                        },
                        {
                            fieldname: 'vencimento',
                            fieldtype: 'Date',
                            label: __('Data de Vencimento do Boleto'),
                            default: frm.doc.due_date || frappe.datetime.add_days(frappe.datetime.get_today(), 5),
                            reqd: 1
                        }
                    ], function(values) {
                        frappe.dom.freeze(__('Gerando Boleto Bancário com Código de Barras e PIX...'));
                        frappe.call({
                            method: 'erpz_financeiro.services.boleto.gerar_boleto_de_fatura',
                            args: {
                                sales_invoice: frm.doc.name,
                                conta_bancaria: values.conta_bancaria,
                                data_vencimento: values.vencimento
                            },
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                if (r.message && r.message.boleto) {
                                    frappe.show_alert({ message: __('Boleto gerado com sucesso!'), indicator: 'green' });
                                    window.open('/api/method/erpz_financeiro.erpz_financeiro.doctype.boleto_bancario.boleto_bancario.baixar_boleto_pdf?docname=' + encodeURIComponent(r.message.boleto));
                                }
                            }
                        });
                    }, __('Emitir Boleto Bancário'), __('Gerar Boleto'));
                });
            }, __('Ações Financeiras')).addClass('btn-primary');
        }
    }
});
