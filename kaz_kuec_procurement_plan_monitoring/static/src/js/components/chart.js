/** @odoo-module */
import { Component, useRef, onMounted, onWillUpdateProps } from "@odoo/owl";
import { makeChartValue } from "./makeChartValue";

export class Chart extends Component {
    static template = "ProcurementChart";
    setup() {
        this.ref = useRef('root')
        this.chart = null;
        onMounted(this.renderChart)
        onWillUpdateProps((props) => {
            if (this.chart) {
                this.chart.dispose();  // remove old chart instance
                this.chart = null;
            }
            this.props.chartMethod = props.chartMethod;
            this.renderChart()
        })
    }

    renderChart() {
        const chartDom = this.ref.el;
        if (!chartDom) return;

        const body = this.props.body || [];
        const option = new makeChartValue(body, this.props.chartMethod).getData();

        // Dynamically adjust chart height
        const isPieChart = this.props.type === 'pie';
        const chartHeight = isPieChart
            ? 250  // fixed height for pie charts
            : Math.max(body.length * 40, 300); // dynamic for bar

        chartDom.style.height = `${chartHeight}px`;

        this.chart = echarts.init(chartDom);
        this.chart.setOption(option);
    }
}