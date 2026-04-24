import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { useService } from "@web/core/utils/hooks";
import { today } from "@web/core/l10n/dates";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";


export class PickCurrencyDate extends Component {
    static template = "PickCurrencyDate";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        updateField: { type: String },
    };

    setup() {
        this.orm = useService("orm");
        const resModel = this.props.record?.resModel || null;
        const updateField = this.props.updateField || null;
        this.dateTimePicker = useDateTimePicker({
            target: 'datetime-picker-target',
            onApply: async (date) => {
                const record = this.props.record
                if (resModel && updateField) {
                    const rate = await this.orm.call(
                        resModel,
                        'get_currency_rate',
                        [record.resId, record.data.company_id[0], record.data.currency_id[0], date],
                    );
                    this.props.record.update({ [updateField]: rate });
                    await this.props.record.save();
                }
            },
            get pickerProps() {
                return {
                    type: 'date',
                    value: today(),
                };
            },
        });
    }
}

export const pickCurrencyDate = {
    component: PickCurrencyDate,
    extractProps: ({ attrs }) => {
        const { update_field: updateField } = attrs;
        return {
            updateField
        };
    },
}

registry.category("view_widgets").add("pick_currency_date",  pickCurrencyDate);
