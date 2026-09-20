frappe.ui.form.on('Remessa CNAB', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Gerar Arquivo de Remessa (.REM)'), function() {
                frappe.dom.freeze(__('Gerando arquivo posicional CNAB...'));
                frm.call({
                    method: 'gerar_arquivo_remessa',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Arquivo CNAB Gerado com Sucesso'),
                                indicator: 'green',
                                message: `<b>Arquivo:</b> ${r.message.file_name}<br><br><a href="${r.message.file_url}" target="_blank" class="btn btn-primary btn-sm">Baixar Arquivo .REM</a>`
                            });
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    }
});
