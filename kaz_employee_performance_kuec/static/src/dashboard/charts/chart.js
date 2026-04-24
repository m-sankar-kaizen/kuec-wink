/** @odoo-module */
import { Component, useRef, onMounted } from "@odoo/owl";
import { makeChartValue } from"../utils/makeChartValue";
import { useBus } from "@web/core/utils/hooks";

export class Chart extends Component {
    static template = "Chart";
    static defaultProps = {
        chartHeight: 350,
        chartWidth: 350,
    }
    setup() {
        this.ref = useRef('root')
        this.chart = null;
        useBus(
            this.env.bus,
            "RE_RENDER",
            this.reRender.bind(this)
        );
        onMounted(this.renderChart)
    }

    delayedReRender() {
        if (this.chart) {
            this.chart.dispose();  // remove old chart instance
            this.chart = null;
        }
        this.renderChart()
    }

    reRender() {
        setTimeout(() => this.delayedReRender(), 1)
    }

    renderChart() {
        const chartDom = this.ref.el;
        if (!chartDom) return;

        const data = this.props.data ? this.props.data : [];
        const additionalOptions = this.props.additionalOptions ? this.props.additionalOptions : {};
        const option = new makeChartValue(data, this.props.chartMethod, additionalOptions).getData();

        // Dynamically adjust chart height
        chartDom.style.height = `${this.props.chartHeight}px`;
        chartDom.style.width = `${this.props.chartWidth}px`

        this.chart = echarts.init(chartDom);
        this.chart.setOption(option);
    }
}