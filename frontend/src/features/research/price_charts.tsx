import { useEffect, useRef } from "react";
import * as echarts from "echarts";

import type { PriceReport } from "./types";

interface PriceChartsPanelProps {
  priceReport: PriceReport | null;
}

function ChartCard({
  title,
  option,
  emptyMessage,
}: {
  title: string;
  option: echarts.EChartsCoreOption | null;
  emptyMessage: string;
}) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!chartRef.current || !option) {
      return;
    }
    const chart = echarts.init(chartRef.current);
    chart.setOption(option);
    return () => chart.dispose();
  }, [option]);

  return (
    <article className="chart-card">
      <h3>{title}</h3>
      {option ? (
        <div className="chart-canvas" ref={chartRef} aria-label={title} role="img" />
      ) : (
        <p className="empty-state">{emptyMessage}</p>
      )}
    </article>
  );
}

export function PriceChartsPanel({ priceReport }: PriceChartsPanelProps) {
  if (!priceReport) {
    return <p className="empty-state">暂无价格分析图表。</p>;
  }

  const productPriceOption =
    priceReport.charts?.product_platform_prices.products.length &&
    priceReport.charts.product_platform_prices.series.length
      ? {
          tooltip: { trigger: "axis" },
          legend: { textStyle: { color: "#dffcff" } },
          grid: { left: 48, right: 20, top: 42, bottom: 56 },
          xAxis: {
            type: "category",
            data: priceReport.charts.product_platform_prices.products,
            axisLabel: { color: "#dffcff", rotate: 20 },
          },
          yAxis: {
            type: "value",
            axisLabel: { color: "#dffcff" },
          },
          series: priceReport.charts.product_platform_prices.series.map((series) => ({
            name: series.platform_name,
            type: "bar",
            data: series.values,
          })),
        }
      : null;

  const platformAverageOption = priceReport.charts?.platform_average_prices.length
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: 80, right: 20, top: 24, bottom: 24 },
        xAxis: {
          type: "value",
          axisLabel: { color: "#dffcff" },
        },
        yAxis: {
          type: "category",
          data: priceReport.charts.platform_average_prices.map((item) => item.platform_name),
          axisLabel: { color: "#dffcff" },
        },
        series: [
          {
            type: "bar",
            data: priceReport.charts.platform_average_prices.map((item) => item.average_price),
          },
        ],
      }
    : null;

  const coverageOption =
    priceReport.charts?.coverage_matrix.products.length && priceReport.charts.coverage_matrix.platforms.length
      ? {
          tooltip: { trigger: "item" },
          grid: { left: 70, right: 20, top: 28, bottom: 50 },
          xAxis: {
            type: "category",
            data: priceReport.charts.coverage_matrix.platforms,
            axisLabel: { color: "#dffcff", rotate: 18 },
          },
          yAxis: {
            type: "category",
            data: priceReport.charts.coverage_matrix.products,
            axisLabel: { color: "#dffcff" },
          },
          visualMap: {
            min: 0,
            max: 1,
            calculable: false,
            orient: "horizontal",
            left: "center",
            bottom: 0,
            inRange: {
              color: ["#132846", "#36e7ff"],
            },
            textStyle: { color: "#dffcff" },
          },
          series: [
            {
              type: "heatmap",
              data: priceReport.charts.coverage_matrix.cells.map((cell) => [
                priceReport.charts?.coverage_matrix.platforms.indexOf(cell.platform_name) ?? 0,
                priceReport.charts?.coverage_matrix.products.indexOf(cell.product_name) ?? 0,
                cell.has_price ? 1 : 0,
              ]),
              label: {
                show: true,
                color: "#03111f",
                formatter: ({ value }: { value: [number, number, number] }) => (value[2] ? "有价" : "无价"),
              },
            },
          ],
        }
      : null;

  const sourceBreakdownOption = priceReport.charts?.source_breakdown.length
    ? {
        tooltip: { trigger: "item" },
        grid: { left: 56, right: 20, top: 24, bottom: 50 },
        xAxis: {
          type: "category",
          data: priceReport.charts.source_breakdown.map((item) => item.source),
          axisLabel: { color: "#dffcff", rotate: 18 },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: "#dffcff" },
        },
        series: [
          {
            type: "bar",
            data: priceReport.charts.source_breakdown.map((item) => item.count),
          },
        ],
      }
    : null;

  return (
    <div className="chart-grid">
      <ChartCard title="商品平台价格对比" option={productPriceOption} emptyMessage="暂无可用价格对比数据。" />
      <ChartCard title="平台均价对比" option={platformAverageOption} emptyMessage="暂无平台均价数据。" />
      <ChartCard title="商品平台覆盖热力图" option={coverageOption} emptyMessage="暂无平台覆盖数据。" />
      <ChartCard title="抓取来源分布" option={sourceBreakdownOption} emptyMessage="暂无来源分布数据。" />
    </div>
  );
}
