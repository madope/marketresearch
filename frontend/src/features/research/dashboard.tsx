import { useState } from "react";

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
          <form
            className="prompt-form"
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
              rows={4}
            />
            <div className="hero-actions">
              <button type="submit" disabled={isSubmitting || isCancelling}>
                {isSubmitting ? "提交中..." : "开始调研"}
              </button>
              <button type="button" className="secondary-button" disabled={!canCancel || isCancelling} onClick={onCancelAllTasks}>
                {isCancelling ? "中止中..." : "中止调研"}
              </button>
              <span>{isPolling ? "当前任务进行中" : "等待新任务"}</span>
            </div>
          </form>
        </section>

        <section className="panel-grid">
          <section className="glass-panel">
            <div className="panel-header">
              <p className="eyebrow">Workflow</p>
              <h2>任务进度</h2>
            </div>
            <div className="stage-list">
              {progressStages.map((stage) => (
                (() => {
                  const stageKey = `${stage.workflow_name}-${stage.stage_name}`;
                  const isExpanded = expandedStageKey === stageKey;
                  const canShowDetails =
                    stage.status !== "running" && (Boolean(stage.message) || Boolean(stage.detail_json));

                  return (
                    <div
                      key={stageKey}
                      className={`stage-row stage-status-${stage.status} ${isExpanded ? "stage-row-expanded" : ""}`}
                    >
                      <span>{stage.workflow_name}</span>
                      <div className="stage-body">
                        <div className="stage-header">
                          <strong>{stage.stage_name}</strong>
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
              <p className="eyebrow">Snapshot</p>
              <h2>价格概览</h2>
            </div>
            {selectedTask?.price_report ? (
              <>
                {selectedTask.price_report.warnings.length > 0 && (
                  <div className="warning-list">
                    {selectedTask.price_report.warnings.map((warning) => (
                      <p key={warning} className="warning-chip">
                        {warning}
                      </p>
                    ))}
                  </div>
                )}
                <div className="metric-grid">
                  <div className="metric-card">
                    <span>均价</span>
                    <strong>¥{selectedTask.price_report.average_price}</strong>
                  </div>
                  <div className="metric-card">
                    <span>最高价</span>
                    <strong>¥{selectedTask.price_report.highest_price}</strong>
                  </div>
                  <div className="metric-card">
                    <span>最低价</span>
                    <strong>¥{selectedTask.price_report.lowest_price}</strong>
                  </div>
                  <div className="metric-card">
                    <span>样本量</span>
                    <strong>{selectedTask.price_report.sample_size}</strong>
                  </div>
                </div>
              </>
            ) : (
              <p className="empty-state">暂无价格报表。</p>
            )}
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
                    <th>价格</th>
                    <th>币种</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTask?.price_report?.rows?.map((row, index) => (
                    <tr key={`${row.product_name}-${row.platform_name}-${index}`}>
                      <td>{row.product_name}</td>
                      <td>{row.platform_name}</td>
                      <td>{row.normalized_price}</td>
                      <td>{row.currency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!selectedTask?.price_report?.rows?.length && <p className="empty-state">暂无价格明细。</p>}
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
