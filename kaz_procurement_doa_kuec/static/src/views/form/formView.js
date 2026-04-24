/** @odoo-module */
import { registry } from "@web/core/registry";
import { useEffect } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

export class ReadonlyFormController extends FormController {
    setup() {
        super.setup();
        useEffect(readonly => {
            this.model.root.config.mode = readonly ? 'readonly' : 'edit';
        }, () => [this.model.root.data.is_readonly])
    }
}

registry.category("views").add("readonly_form_view", {
    ...formView,
    Controller: ReadonlyFormController,
});
