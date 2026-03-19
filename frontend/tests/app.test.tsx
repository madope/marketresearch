import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "../src/features/research/dashboard";
import type { ResearchTaskDetail, ResearchTaskSummary } from "../src/features/research/types";

vi.mock("echarts", () => ({
  init: () => ({
    setOption: vi.fn(),
    dispose: vi.fn(),
  }),
}));

const taskSummaries: ResearchTaskSummary[] = [
  {
    task_id: "task-2",
    prompt: "调研电动牙刷",
    status: "completed",
    summary: "完成电动牙刷调研",
    created_at: "2026-03-16T16:00:00Z",
  },
];

const detail: ResearchTaskDetail = {
  task: taskSummaries[0],
  products: [
    { product_name: "电动牙刷 标准款", source_type: "category_inferred", input_order: 1 },
  ],
  platforms: [
    { platform_name: "京东", platform_domain: "jd.com", discover_round: 1, platform_type: "marketplace" },
  ],
  stages: [
    {
      workflow_name: "price_research",
      stage_name: "llm_select_products",
      status: "fallback",
      message: "模型调用失败，已降级到 fallback 数据",
      retry_count: 0,
      detail_json: {
        provider: "volcengine",
        method: "json",
        prompt: "请识别用户输入中的产品",
        result: {
          intent_type: "category",
          products: ["电动牙刷 标准款"],
        },
      },
    },
    {
      workflow_name: "market_analysis",
      stage_name: "analyze_revenue_model",
      status: "error",
      message: "模型请求失败：upstream timeout",
      retry_count: 0,
    },
    {
      workflow_name: "price_research",
      stage_name: "analyze_prices",
      status: "completed",
      message: "已生成价格报表：均价 199，最高价 259，最低价 169",
      retry_count: 0,
    },
  ],
  price_report: {
    average_price: 199,
    highest_price: 259,
    lowest_price: 169,
    sample_size: 2,
    row_count: 3,
    platform_count: 5,
    fallback_used: true,
    warnings: ["部分平台页面未识别出有效价格"],
    source_breakdown: { markdown_llm_price: 2, markdown_llm_unpriced: 1 },
    charts: {
      product_platform_prices: {
        products: ["电动牙刷 Pro", "电动牙刷 标准款"],
        series: [
          { platform_name: "京东", values: [null, 199] },
          { platform_name: "淘宝", values: [null, 189] },
        ],
      },
      platform_average_prices: [
        { platform_name: "京东", average_price: 199, sample_size: 1 },
        { platform_name: "淘宝", average_price: 189, sample_size: 1 },
      ],
      coverage_matrix: {
        products: ["电动牙刷 Pro", "电动牙刷 标准款"],
        platforms: ["京东", "淘宝"],
        cells: [
          { product_name: "电动牙刷 Pro", platform_name: "京东", has_price: false, price: null, product_url: "https://jd.com/item/3" },
          { product_name: "电动牙刷 Pro", platform_name: "淘宝", has_price: false, price: null, product_url: "" },
          { product_name: "电动牙刷 标准款", platform_name: "京东", has_price: true, price: 199, product_url: "https://jd.com/item/1" },
          { product_name: "电动牙刷 标准款", platform_name: "淘宝", has_price: true, price: 189, product_url: "https://taobao.com/item/2" },
        ],
      },
      source_breakdown: [
        { source: "markdown_llm_price", count: 2 },
        { source: "markdown_llm_unpriced", count: 1 },
      ],
      product_price_ranges: [
        { product_name: "电动牙刷 标准款", min_price: 189, max_price: 199, average_price: 194, sample_size: 2 },
      ],
    },
    rows: [
      {
        product_name: "电动牙刷 标准款",
        platform_name: "京东",
        platform_domain: "jd.com",
        product_url: "https://jd.com/item/1",
        normalized_price: 199,
        currency: "CNY",
        source: "markdown_llm_price",
      },
      {
        product_name: "电动牙刷 标准款",
        platform_name: "淘宝",
        platform_domain: "taobao.com",
        product_url: "https://taobao.com/item/2",
        normalized_price: 189,
        currency: "CNY",
        source: "markdown_llm_price",
      },
      {
        product_name: "电动牙刷 Pro",
        platform_name: "京东",
        platform_domain: "jd.com",
        product_url: "https://jd.com/item/3",
        normalized_price: null,
        currency: "CNY",
        source: "markdown_llm_unpriced",
        notes: "抓到网页但未识别出价格",
      },
    ],
  },
  market_analysis: {
    revenue_model_text: "通过商品销售获利",
    competition_text: "竞争激烈",
    build_plan_text: "从供应链开始",
    summary_json: { risks: ["平台抓取存在回退"], opportunities: [] },
  },
};

const runningDetail: ResearchTaskDetail = {
  task: {
    ...taskSummaries[0],
    status: "running",
    summary: null,
  },
  products: [
    { product_name: "宠物烘干箱 标准款", source_type: "category_inferred", input_order: 1 },
  ],
  platforms: [],
  stages: [
    {
      workflow_name: "price_research",
      stage_name: "discover_platforms",
      status: "running",
      message: "执行中",
      retry_count: 0,
      detail_json: {
        node_name: "discover_platforms",
        status: "running",
      },
    },
    {
      workflow_name: "market_analysis",
      stage_name: "extract_business_topic",
      status: "completed",
      message: "已提取商业主题：调研宠物烘干箱市场",
      retry_count: 0,
    },
    {
      workflow_name: "price_research",
      stage_name: "llm_select_products",
      status: "completed",
      message: "已识别候选产品",
      retry_count: 0,
    },
    {
      workflow_name: "price_research",
      stage_name: "parse_product_intent",
      status: "completed",
      message: "识别结果：category，共识别 5 个候选产品",
      retry_count: 0,
    },
    {
      workflow_name: "price_research",
      stage_name: "select_products",
      status: "completed",
      message: "已确定调研产品",
      retry_count: 0,
    },
  ],
  price_report: null,
  market_analysis: null,
};

describe("Dashboard", () => {
  it("renders task history and result panels", () => {
    render(
      <Dashboard
        tasks={taskSummaries}
        selectedTask={detail}
        isSubmitting={false}
        isCancelling={false}
        isPolling={false}
        canCancel={false}
        onSubmit={vi.fn()}
        onCancelAllTasks={vi.fn()}
        onSelectTask={vi.fn()}
      />,
    );

    expect(screen.getByText("历史任务")).toBeInTheDocument();
    expect(screen.getByText("发起调研")).toBeInTheDocument();
    expect(screen.getByText("价格分析图表")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "市场分析" })).toBeInTheDocument();
    expect(screen.getByText("完成电动牙刷调研")).toBeInTheDocument();
    expect(screen.getByText("模型调用失败，已降级到 fallback 数据")).toBeInTheDocument();
    expect(screen.getByText("模型请求失败：upstream timeout")).toBeInTheDocument();
    expect(screen.getByText("fallback")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("已生成价格报表：均价 199，最高价 259，最低价 169")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://jd.com/item/1" })).toBeInTheDocument();
  });

  it("submits prompt input", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <Dashboard
        tasks={[]}
        selectedTask={null}
        isSubmitting={false}
        isCancelling={false}
        isPolling={false}
        canCancel={false}
        onSubmit={onSubmit}
        onCancelAllTasks={vi.fn()}
        onSelectTask={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("调研需求"), "调研宠物烘干箱");
    await user.click(screen.getByRole("button", { name: "开始调研" }));

    expect(onSubmit).toHaveBeenCalledWith("调研宠物烘干箱");
  });

  it("shows completed stages and real running stages for active task", () => {
    render(
      <Dashboard
        tasks={taskSummaries}
        selectedTask={runningDetail}
        isSubmitting={false}
        isCancelling={false}
        isPolling={true}
        canCancel={true}
        onSubmit={vi.fn()}
        onCancelAllTasks={vi.fn()}
        onSelectTask={vi.fn()}
      />,
    );

    expect(screen.getByText("已提取商业主题：调研宠物烘干箱市场")).toBeInTheDocument();
    expect(screen.getByText("已确定调研产品")).toBeInTheDocument();
    expect(screen.getByText("发现平台")).toBeInTheDocument();
    expect(screen.getByText("执行中")).toBeInTheDocument();
    expect(screen.getAllByText("running")).toHaveLength(1);
    expect(screen.queryByText("分析盈利模式")).not.toBeInTheDocument();
  });

  it("cancels all active tasks from the hero panel", async () => {
    const user = userEvent.setup();
    const onCancelAllTasks = vi.fn();

    render(
      <Dashboard
        tasks={taskSummaries}
        selectedTask={runningDetail}
        isSubmitting={false}
        isCancelling={false}
        isPolling={true}
        canCancel={true}
        onSubmit={vi.fn()}
        onCancelAllTasks={onCancelAllTasks}
        onSelectTask={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "中止调研" }));

    expect(onCancelAllTasks).toHaveBeenCalledTimes(1);
  });

  it("toggles full stage message details for completed stages", async () => {
    const user = userEvent.setup();

    render(
      <Dashboard
        tasks={taskSummaries}
        selectedTask={detail}
        isSubmitting={false}
        isCancelling={false}
        isPolling={false}
        canCancel={false}
        onSubmit={vi.fn()}
        onCancelAllTasks={vi.fn()}
        onSelectTask={vi.fn()}
      />,
    );

    expect(screen.queryByText("步骤详情")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "查看详情" })[0]);

    expect(screen.getByText("步骤详情")).toBeInTheDocument();
    expect(screen.getByText(/"provider": "volcengine"/, { selector: "pre" })).toBeInTheDocument();
    expect(screen.getByText(/"method": "json"/, { selector: "pre" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "收起详情" }));

    expect(screen.queryByText("步骤详情")).not.toBeInTheDocument();
  });

  it("renders duplicate stage names with their own messages instead of reusing stale rows", () => {
    const duplicateStageDetail: ResearchTaskDetail = {
      ...detail,
      stages: [
        {
          workflow_name: "price_research",
          stage_name: "llm_select_final_platforms",
          status: "error",
          message: "火山方舟 web search 请求失败：Connection error.",
          retry_count: 0,
        },
        {
          workflow_name: "price_research",
          stage_name: "llm_select_final_platforms",
          status: "error",
          message: "火山方舟 web search 请求失败：Request timed out.",
          retry_count: 0,
        },
      ],
    };

    render(
      <Dashboard
        tasks={taskSummaries}
        selectedTask={duplicateStageDetail}
        isSubmitting={false}
        isCancelling={false}
        isPolling={false}
        canCancel={false}
        onSubmit={vi.fn()}
        onCancelAllTasks={vi.fn()}
        onSelectTask={vi.fn()}
      />,
    );

    expect(screen.getByText("火山方舟 web search 请求失败：Connection error.")).toBeInTheDocument();
    expect(screen.getByText("火山方舟 web search 请求失败：Request timed out.")).toBeInTheDocument();
    expect(screen.getAllByText("大模型筛选平台")).toHaveLength(2);
  });
});
