/** @odoo-module */

import { Component } from "@odoo/owl";

export class KpiCard extends Component {
    static template = "KpiCard";
    static defaultProps = {
        iconClass: 'fa-building',
        bgColor: 'orange',
        value: 0,
        text: "",
    }

    setup() {
    }

}
