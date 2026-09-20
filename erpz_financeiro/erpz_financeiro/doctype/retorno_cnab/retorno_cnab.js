frappe.ui.form.on('Retorno CNAB', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Processar Arquivo de Retorno'), function() {
                frappe.dom.freeze(__('Lendo arquivo e baixando faturas liquidadas no ERPNext...'));
                frm.call({
                    method: 'processar_arquivo_retorno',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Retorno Processado com Sucesso'),
                                indicator: 'green',
                                message: `<b>Títulos Processados:</b> ${r.message.titulos_processados}<br><b>Total Liquidado:</b> R$ ${r.message.total_liquidado.toFixed(2)}`
                            });
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    }
});
