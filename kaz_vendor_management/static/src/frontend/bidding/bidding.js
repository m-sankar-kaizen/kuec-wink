/** @odoo-module **/
import { Component, useEffect, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry"
import { rpc } from "@web/core/network/rpc";

export const TENDER_STATES = {
    draft: "Draft",
    pre_qualify: "Pre-Qualify",
    evaluation: "Evaluation",
    bid_evaluated: "Evaluated",
    bafo_selected: "BAFO Selected",
    awarded: "Awarded",
    rejected: "Rejected",
}

export class Bidding extends Component {
    static template = "Bidding";
    setup() {
        this.state = useState({
            tenderBid: {},
            writeRFQLines: [],
            writeAttachmentLines: [],
            warningMessage: "",
            details: "",
            disableSubmit: false,
        });
        onWillStart(async () => await this.fetchData())
    }

    get tenderBid() {
        return this.state.tenderBid?.tender_bid_rfq_line_ids?.map(line => {
            return {
                ...line,
                total: line.price_unit * line.qty
            }
        })
    }
    get tenderBidAttachment() {
        return this.state.tenderBid?.tender_bid_required_attachment_ids ? this.state.tenderBid?.tender_bid_required_attachment_ids : []
    }

    get totalValue() {
        const lines = this.props.active_bid ? this.tenderBid : this.writeRFQLines;
        if (!lines || !lines.length) return 0;
        return lines.reduce((sum, line) => sum + (line.total || 0), 0);
    }

    get bidState() {
        const state = this.state.tenderBid.state ? this.state.tenderBid.state : "draft";
        return Object.keys(TENDER_STATES).includes(state) ? TENDER_STATES[state] : 'N/A';
    }

    get displayName() {
        return this.props.active_bid ? this.state.tenderBid.name : "New";
    }

    get tenderLineProps(){
        return this.props.tender_lines;
    }

    get writeRFQLines() {
        return this.state.writeRFQLines;
    }

    async fetchData() {
        if (this.props.active_bid) {
            this.state.tenderBid = await rpc('/fetch/tender/bid', {
                tender_bid_id: this.props.active_bid,
                user_id: this.props.user_id,
                company_id: this.props.company_id,
            })
        }
        else {
            this.state.writeRFQLines = this.tenderLineProps.map(line => {
                return {
                    ...line,
                    user_qty: 0,
                    user_price_unit: 0,
                    total: 0,
                    show_qty_warning: false,
                    show_price_warning: false,
                }
            })
            this.state.writeAttachmentLines = this.props.required_attachments.map(line => {
                return {
                    ...line,
                    file_name: false,
                    attachment_id: false,
                }
            })
        }
    }

    onFileChange(id, ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = () => {
            const base64data = reader.result.split(',')[1];
            const attachment = this.state.writeAttachmentLines.find(line => line.id == id)
            if (attachment) {
                attachment.file_name = file.name;
                attachment.attachment_id = base64data;
            }
        };
        reader.readAsDataURL(file);
    }


    get isReadOnly() {
        return this.props.is_readonly;
    }

    updateQty(lineId, value) {
        value = parseFloat(value);
        const rfqLine = this.state.writeRFQLines.find(line => line.id === lineId);
        if (rfqLine) {
            rfqLine.user_qty = value;
            rfqLine.total = value * rfqLine.user_price_unit;
            rfqLine.show_qty_warning = rfqLine.user_qty <= 0
            rfqLine.show_price_warning = rfqLine.user_price_unit <= 0
        }
        this.state.warningMessage = ""
    }

    updatePrice(lineId, value) {
        value = parseFloat(value);
        const rfqLine = this.state.writeRFQLines.find(line => line.id === lineId);
        if (rfqLine) {
            rfqLine.user_price_unit = value;
            rfqLine.total = value * rfqLine.user_qty;
            rfqLine.show_qty_warning = rfqLine.user_qty <= 0
            rfqLine.show_price_warning = rfqLine.user_price_unit <= 0
        }
        this.state.warningMessage = ""
    }

    async submitForm() {
        if (this.state.disableSubmit) {
            return;
        }
        this.state.disableSubmit = true;
        const invalidLines = this.state.writeRFQLines.filter(line =>
            !line.user_qty || !line.user_price_unit
        );

        if (invalidLines.length) {
            this.state.warningMessage = "Please fill Qty and Unit Price for all items before submitting."
            return;
        }

        const invalidAttachment = this.state.writeAttachmentLines.filter(line => !line.attachment_id )

        if (invalidAttachment.length) {
            this.state.warningMessage = "Please Attach the required Attachments."
            return;
        }

        const response = await rpc('/submit/bid', {
            tender_rfq_id: this.props.tender_id,
            user_id: this.props.user_id,
            tender_bid_rfq_line_ids: this.writeRFQLines,
            tender_bid_required_attachment_ids: this.state.writeAttachmentLines,
            company_id: this.props.company_id,
            currency_id: this.props.currency_id.id,

        })

        if (response.success) {
            window.location.href = `/tender/${this.props.tender_id}/bid/${response.tender_bid}`;
            return;
        }
        else {
            this.state.warningMessage = response.message
            this.state.details = response.details ?? "";
        }
        this.state.disableSubmit = false;

    }

}

registry.category("public_components").add("Bidding", Bidding);
