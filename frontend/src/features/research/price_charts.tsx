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

  const rowUnitLookup = new Map(
    priceReport.rows.map((row) => [
      `${row.product_name}::${row.platform_name}`,
      String(row.price_unit || "").trim() || "件",
    ]),
  );

  const platformUnitLookup = new Map(
    priceReport.charts?.platform_average_prices.map((item) => {
      const units = new Set(
        priceReport.rows
          .filter((row) => row.platform_name === item.platform_name && row.normalized_price !== null && row.normalized_price !== undefined)
          .map((row) => String(row.price_unit || "").trim() || "件"),
      );
      return [item.platform_name, units.size === 1 ? Array.from(units)[0] : "多单位"] as const;
    }) ?? [],
  );

  const formatPriceWithUnit = (value: number | null | undefined, unit?: string | null) => {
    if (value === null || value === undefined) {
      return "无价格";
    }
    const normalizedUnit = String(unit || "").trim() || "件";
    return `${value} 元/${normalizedUnit}`;
  };

  const productPriceOption =
    priceReport.charts?.product_platform_prices.products.length &&
    priceReport.charts.product_platform_prices.series.length
      ? {
          tooltip: {
            trigger: "axis",
            formatter: (params: Array<{ seriesName: string; axisValue: string; data: number | null }>) => {
              const lines = params.map((item) =>
                `${item.seriesName}: ${formatPriceWithUnit(item.data, rowUnitLookup.get(`${item.axisValue}::${item.seriesName}`))}`,
              );
              return [params[0]?.axisValue ?? "", ...lines].filter(Boolean).join("<br/>");
            },
          },
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

  const productPriceRangeOption = priceReport.charts?.product_price_ranges.length
    ? {
        tooltip: {
          trigger: "axis",
        },
        legend: { textStyle: { color: "#dffcff" } },
        grid: { left: 56, right: 20, top: 42, bottom: 42 },
        xAxis: {
          type: "category",
          data: priceReport.charts.product_price_ranges.map((item) => item.product_name),
          axisLabel: { color: "#dffcff", rotate: 16 },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: "#dffcff" },
        },
        series: [
          {
            name: "最低价",
            type: "line",
            smooth: true,
            data: priceReport.charts.product_price_ranges.map((item) => item.min_price),
          },
          {
            name: "平均价",
            type: "line",
            smooth: true,
            data: priceReport.charts.product_price_ranges.map((item) => item.average_price),
          },
          {
            name: "最高价",
            type: "line",
            smooth: true,
            data: priceReport.charts.product_price_ranges.map((item) => item.max_price),
          },
        ],
      }
    : null;

  return (
    <div className="chart-grid">
      <ChartCard title="商品平台价格对比" option={productPriceOption} emptyMessage="暂无可用价格对比数据。" />
      <ChartCard title="商品价格统计" option={productPriceRangeOption} emptyMessage="暂无商品价格统计数据。" />
    </div>
  );
}
