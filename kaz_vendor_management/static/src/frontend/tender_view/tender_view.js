/** @odoo-module **/
import { Component, useEffect, useState, onWillStart, markup } from "@odoo/owl";
import { registry } from "@web/core/registry"
import { rpc } from "@web/core/network/rpc";
import { STATE_VALUES } from "../tender/tender_item";

export class TenderView extends Component {
    static template = "TenderView";
    static components = {};
    setup() {
        this.state = useState({
            partner: false,
            tender: {},
            user: [],
            categories: [],
            rfqLines: []
        })
        onWillStart(async () => await this.fetchData());
    }

    async fetchData() {
        await this.loadBasic();
        await this.fetchTender();
    }

    async loadBasic() {
        const response = await rpc('/get/tender/basic-info', {
            company_id: this.props.company_id,
            user_id: this.props.user_id,
        })
        this.state.categories = response.partner_categories;
        this.state.user = response.user;
    }

    async fetchTender() {
        const response = await rpc('/fetch/tender', {
            tender_id: this.props.tender_id,
            user_id: this.props.user_id,
            company_id: this.props.company_id,
        })
        this.state.partner = response.partner;
        this.state.tender = response.tender;
        this.state.rfqLines = response.tender?.tender_rfq_line_ids;
    }

    get tender() {
        return this.state.tender;
    }

    get displayName() {
        return `${this.tender.name} #${this.tender.version}`;
    }

    get displayTitle() {
        return this.tender.title;
    }

    get isExclusive() {
        return this.tender.is_exclusive;
    }

    get portalDescription() {
        const description =  this.tender.portal_description
        if (description) {
            return markup(description)
        }
        return ""
    }

    get evaluationCriteria() {
        const description =  this.tender.evaluation_criteria;
        if (description) {
            return markup(description)
        }
        return ""
    }

    get parentTender() {
        return this.tender.tender_rfq_id;
    }

    get bafoTenders() {
        return (this.tender.tender_rfq_ids || []).sort(
            (a, b) => (a.version || 0) - (b.version || 0)
        );
    }

    getState(state) {
        return Object.keys(STATE_VALUES).includes(state) ? STATE_VALUES[state] : 'N/A';
    }

    get documents() {
        return this.tender.tender_rfq_document_ids;
    }

    get activeBid() {
        return this.props.tender_bid;
    }

    get isReadonly() {
        return this.tender.state !== 'active' || this.activeBid.id;
    }

}

registry.category("public_components").add("TenderView", TenderView);

