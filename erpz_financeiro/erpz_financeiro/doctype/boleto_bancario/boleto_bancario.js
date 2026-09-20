frappe.ui.form.on('Boleto Bancario', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Imprimir Boleto (PDF)'), function() {
                window.open('/api/method/erpz_financeiro.erpz_financeiro.doctype.boleto_bancario.boleto_bancario.baixar_boleto_pdf?docname=' + encodeURIComponent(frm.doc.name));
            }).addClass('btn-primary');

            if (frm.doc.status !== 'Liquidado / Pago') {
                frm.add_custom_button(__('Registrar Pagamento Manual'), function() {
                    frappe.prompt([
                        { fieldname: 'valor_pago', fieldtype: 'Currency', label: __('Valor Pago (R$)'), default: frm.doc.valor_documento, reqd: 1 },
                        { fieldname: 'data_pagamento', fieldtype: 'Date', label: __('Data do Pagamento'), default: frappe.datetime.get_today(), reqd: 1 }
                    ], function(values) {
                        frappe.dom.freeze(__('Baixando boleto e registrando recebimento no ERPNext...'));
                        frm.call({
                            method: 'registrar_liquidacao',
                            doc: frm.doc,
                            args: values,
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                frm.reload_doc();
                                if (r.message && r.message.success) {
                                    frappe.show_alert({ message: __('Boleto baixado com sucesso!'), indicator: 'green' });
                                }
                            }
                        });
                    }, __('Liquidação de Boleto'), __('Confirmar Baixa'));
                });
            }
        }
    }
});
