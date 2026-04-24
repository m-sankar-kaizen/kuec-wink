/** @odoo-module **/
import { Component, useEffect, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MIN = 0;
const MAX = 100;

export class RatingBar extends Component {
    static template = "ratingBar";
    static props = {
        ...standardFieldProps,
        withCommand: { type: Boolean, optional: true },
        autosave: { type: Boolean, optional: true },
    };

    setup() {
        console.log(this)
        this.state = useState({
            score: 6,
            hoverScore: null,
            isDragging: false,
        })
        this.barRef = useRef('bar')
    }

    updateScoreFromEvent(clientX) {
        if (!this.barRef.el) return;
        const rect = this.barRef.el.getBoundingClientRect();
        const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
        const percentage = (x / rect.width);
        const rawValue = MIN + (percentage * (MAX - MIN));
        return Math.round(rawValue * 10) / 10;
      };

    get rating() {
        return this.props.record.data[this.props.name] || 0.0;
    }

    get formattedRating() {
        return this.rating.toFixed(1)
    }

    get formattedHoverScore() {
        return this.state.hoverScore?.toFixed(1) || 0.0
    }

    get currentPercent() {
        return ((this.rating - MIN) / (MAX - MIN)) * 100;
    }

    get hoverPercent() {
        const { hoverScore } = this.state;
        return hoverScore !== null ? ((hoverScore - MIN) / (MAX - MIN)) * 100 : null;
    }

    get color() {
        const value = this.rating;
        if (value < 25) return '#ef4444'; // Red
        if (value < 50) return '#f97316'; // Orange
        if (value < 75) return '#eab308'; // Yellow
        return '#22c55e'; // Green
    };

    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
    }

    setHoverScore(score) {
        this.state.hoverScore = score;
    }

    handleMouseDown(e) {
        if (!this.props.readonly) {
            this.state.isDragging = true;
            const newScore = this.updateScoreFromEvent(e.clientX);
            if (newScore !== undefined) this.updateRecord(newScore);
        }
    }

    handleBarHover(e) {
        if (!this.props.readonly) {
            if (this.state.isDragging) return; // Don't show hover effect while dragging
            const newScore = this.updateScoreFromEvent(e.clientX);
            this.setHoverScore(newScore);
        }
    }

    handleBarLeave() {
        this.setHoverScore(null);
    }

    handleMouseUp() {
        this.state.isDragging = false;
    };

}

export const ratingBar = {
    component: RatingBar,
    displayName: _t("Rating Bar"),
    supportedTypes: ["float"],
    extractProps({ options, viewType }, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
            autosave: "autosave" in options ? !!options.autosave : true,
        };
    },
};

registry.category("fields").add("rating_bar", ratingBar);
