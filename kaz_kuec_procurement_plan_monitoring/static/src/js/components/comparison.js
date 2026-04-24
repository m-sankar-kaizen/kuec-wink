/* @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Chart } from "./chart";

export class Comparison extends Component {
    static template = "Comparison";
    static components = {Chart};

    setup() {
        this.state = useState({
            activeTab: this.props.tabs[0].key
        })
    }

    switchTab(tab) {
        this.state.activeTab = tab;
    }

    get chartProps() {
        return {
            body: this.props.body,
            chartMethod: this.state.activeTab,
            type: 'comparison'
        }
    }
}
