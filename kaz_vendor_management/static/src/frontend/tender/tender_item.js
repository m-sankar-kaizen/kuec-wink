/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export const STATE_VALUES = {
    active: 'Active',
    closed: 'Closed',
    under_review: 'Under Review',
    bafo: 'BAFO',
    awarded: 'Awarded',
}

export class TenderItem extends Component {
    static template = "TenderItem";
    static defaultProps = {
        user: {},
    }
    setup() {
        this.state = useState({
            open: false,
        })
    }

    get hasAccess() {
        const partnerId = this.props.user?.partner_id?.[0];
        if (!this.props.partner_ids || this.props.partner_ids.length === 0) {
            return true;
        }
        return partnerId ? this.props.partner_ids.includes(partnerId) : false;
    }

    toggleTenderButton() {
        this.state.open = !this.state.open
    }

    getState(state) {
        return Object.keys(STATE_VALUES).includes(state) ? STATE_VALUES[state] : 'N/A';
    }

}