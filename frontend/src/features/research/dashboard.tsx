import { useState } from "react";

import { PriceChartsPanel } from "./price_charts";
import type { ResearchTaskDetail, ResearchTaskSummary, StageStatus } from "./types";

import "./dashboard.css";

interface DashboardProps {
  tasks: ResearchTaskSummary[];
  selectedTask: ResearchTaskDetail | null;
  isSubmitting: boolean;
  isCancelling: boolean;
  isPolling: boolean;
  canCancel: boolean;
  onSubmit: (prompt: string) => void;
  onCancelAllTasks: () => void;
  onSelectTask: (taskId: string) => void;
}

const WORKFLOW_LABELS: Record<string, string> = {
  price_research: "价格调研",
  market_analysis: "市场分析",
};

const STAGE_LABELS: Record<string, string> = {
  llm_select_products: "大模型识别产品",
  parse_product_intent: "解析产品意图",
  select_products: "确定调研产品",
  llm_select_final_platforms: "大模型筛选平台",
  discover_platforms: "发现平台",
  crawl_prices_parallel: "抓取价格",
  normalize_prices: "标准化价格",
  analyze_prices: "分析价格",
  llm_summarize_price_risks: "总结价格风险",
  extract_business_topic: "提取商业主题",
  analyze_revenue_model: "分析盈利模式",
  analyze_competition_and_outlook: "分析竞争与前景",
  build_from_zero_plan: "从零构建方案",
  llm_build_from_zero_plan: "大模型生成构建方案",
};

export function Dashboard({
  tasks,
  selectedTask,
  isSubmitting,
  isCancelling,
  isPolling,
  canCancel,
  onSubmit,
  onCancelAllTasks,
  onSelectTask,
}: DashboardProps) {
  const [prompt, setPrompt] = useState("");
  const [expandedStageKey, setExpandedStageKey] = useState<string | null>(null);
  const progressStages: StageStatus[] = selectedTask?.stages ?? [];

  const getWorkflowLabel = (workflowName: string) => WORKFLOW_LABELS[workflowName] ?? workflowName;
  const getStageLabel = (stageName: string) => STAGE_LABELS[stageName] ?? stageName;

  const formatStageDetail = (stage: StageStatus) => {
    if (stage.detail_json) {
      return JSON.stringify(stage.detail_json, null, 2);
    }
    return stage.message ?? "";
  };

  return (
    <div className="dashboard-shell">
      <aside className="history-panel">
        <div className="panel-header">
          <p className="eyebrow">Timeline</p>
          <h2>历史任务</h2>
        </div>
        <div className="history-list">
          {tasks.map((task) => (
            <button key={task.task_id} className="history-card" onClick={() => onSelectTask(task.task_id)}>
              <span className={`status-chip status-${task.status}`}>{task.status}</span>
              <strong>{task.prompt}</strong>
              <small>{task.summary ?? "等待结果"}</small>
            </button>
          ))}
        </div>
      </aside>

      <main className="workspace-panel">
        <section className="hero-panel">
          <div>
            <p className="eyebrow">Command Center</p>
            <h1>市场调研工作台</h1>
            <p className="lead">输入调研需求，触发 LangGraph 工作流，查看价格报表与商业模式分析。</p>
          </div>
        </section>

        <section className="panel-grid">
          <section className="glass-panel">
            <div className="panel-header">
              <p className="eyebrow">Workflow</p>
              <h2>任务进度</h2>
            </div>
            <div className="stage-list">
              {progressStages.map((stage, index) => (
                (() => {
                  const stageKey = `${stage.workflow_name}-${stage.stage_name}-${stage.status}-${stage.message ?? ""}-${index}`;
                  const isExpanded = expandedStageKey === stageKey;
                  const canShowDetails =
                    stage.status !== "running" && (Boolean(stage.message) || Boolean(stage.detail_json));

                  return (
                    <div
                      key={stageKey}
                      className={`stage-row stage-status-${stage.status} ${isExpanded ? "stage-row-expanded" : ""}`}
                    >
                      <span>{getWorkflowLabel(stage.workflow_name)}</span>
                      <div className="stage-body">
                        <div className="stage-header">
                          <strong>{getStageLabel(stage.stage_name)}</strong>
                          {canShowDetails && (
                            <button
                              type="button"
                              className="stage-toggle"
                              onClick={() => setExpandedStageKey(isExpanded ? null : stageKey)}
                            >
                              {isExpanded ? "收起详情" : "查看详情"}
                            </button>
                          )}
                        </div>
                        {stage.message && <p className="stage-message">{stage.message}</p>}
                        {isExpanded && canShowDetails && (
                          <div className="stage-detail-panel">
                            <p className="stage-detail-label">步骤详情</p>
                            <pre className="stage-detail-content">{formatStageDetail(stage)}</pre>
                          </div>
                        )}
                      </div>
                      <small className={`stage-status-label stage-status-label-${stage.status}`}>{stage.status}</small>
                    </div>
                  );
                })()
              ))}
              {!selectedTask && <p className="empty-state">提交任务后，这里会显示工作流进度。</p>}
            </div>
          </section>

          <section className="glass-panel">
            <div className="panel-header">
              <p className="eyebrow">Command</p>
              <h2>发起调研</h2>
            </div>
            <form
              className="prompt-form prompt-form-panel"
              onSubmit={(event) => {
                event.preventDefault();
                const trimmed = prompt.trim();
                if (!trimmed) {
                  return;
                }
                onSubmit(trimmed);
                setPrompt("");
              }}
            >
              <label htmlFor="research-prompt">调研需求</label>
              <textarea
                id="research-prompt"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="例如：调研中国大陆宠物烘干箱市场"
                rows={3}
              />
              <div className="hero-actions">
                <button type="submit" className="hero-action-button" disabled={isSubmitting || isCancelling}>
                  {isSubmitting ? "提交中..." : "开始调研"}
                </button>
                <button
                  type="button"
                  className="hero-action-button secondary-button"
                  disabled={!canCancel || isCancelling}
                  onClick={onCancelAllTasks}
                >
                  {isCancelling ? "中止中..." : "中止调研"}
                </button>
                <span className="hero-status-text">{isPolling ? "当前任务进行中" : "等待新任务"}</span>
              </div>
            </form>
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
              <p className="eyebrow">Charts</p>
              <h2>价格分析图表</h2>
            </div>
            <PriceChartsPanel priceReport={selectedTask?.price_report ?? null} />
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
              <p className="eyebrow">Results</p>
              <h2>价格表格</h2>
            </div>
            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>产品</th>
                    <th>平台</th>
                    <th>价格页 URL</th>
                    <th>价格</th>
                    <th>来源</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTask?.price_report?.rows?.map((row, index) => (
                    <tr key={`${row.product_name}-${row.platform_name}-${index}`}>
                      <td>{row.product_name}</td>
                      <td>{row.platform_name}</td>
                      <td>
                        {row.product_url ? (
                          <a href={row.product_url} target="_blank" rel="noreferrer">
                            {row.product_url}
                          </a>
                        ) : (
                          "--"
                        )}
                      </td>
                      <td>{row.normalized_price ?? "--"}</td>
                      <td>{row.source ?? "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!selectedTask?.price_report?.rows?.length && <p className="empty-state">暂无价格明细。</p>}
            </div>
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
              <p className="eyebrow">Intelligence</p>
              <h2>市场分析</h2>
            </div>
            {selectedTask?.market_analysis ? (
              <div className="analysis-grid">
                <article>
                  <h3>如何赚钱</h3>
                  <p>{selectedTask.market_analysis.revenue_model_text}</p>
                </article>
                <article>
                  <h3>竞争与前景</h3>
                  <p>{selectedTask.market_analysis.competition_text}</p>
                </article>
                <article>
                  <h3>从 0 构建</h3>
                  <p>{selectedTask.market_analysis.build_plan_text}</p>
                </article>
                {!!selectedTask.market_analysis.summary_json.data_quality?.length && (
                  <article>
                    <h3>数据质量提示</h3>
                    <p>{selectedTask.market_analysis.summary_json.data_quality.join("；")}</p>
                  </article>
                )}
              </div>
            ) : (
              <p className="empty-state">暂无市场分析。</p>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
