import { useEffect, useRef, useState } from "react";

import { PriceChartsPanel } from "./price_charts";
import type {
  IntakeMessage,
  ResearchTaskDetail,
  ResearchTaskSummary,
  StageStatus,
} from "./types";

import "./dashboard.css";

interface DashboardProps {
  tasks: ResearchTaskSummary[];
  selectedTask: ResearchTaskDetail | null;
  isSubmitting: boolean;
  isChatting: boolean;
  isCancelling: boolean;
  isPolling: boolean;
  canCancel: boolean;
  taskListError: string | null;
  intakeMessages: IntakeMessage[];
  intakeReadyToStart: boolean;
  onSendIntakeMessage: (message: string) => void | Promise<void>;
  onStartResearch: () => void;
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

function formatPriceWithUnit(value: number | null | undefined, unit?: string | null) {
  if (value === null || value === undefined) {
    return "--";
  }
  const normalizedUnit = String(unit || "").trim() || "件";
  return `${value} 元/${normalizedUnit}`;
}

function renderMarkdownBlocks(content: string) {
  const lines = content.split(/\r?\n/);
  const blocks: Array<
    | { type: "heading"; level: number; text: string }
    | { type: "list"; items: string[] }
    | { type: "paragraph"; text: string }
  > = [];

  let currentList: string[] = [];
  let currentParagraph: string[] = [];

  const flushList = () => {
    if (currentList.length) {
      blocks.push({ type: "list", items: currentList });
      currentList = [];
    }
  };

  const flushParagraph = () => {
    if (currentParagraph.length) {
      blocks.push({ type: "paragraph", text: currentParagraph.join(" ") });
      currentParagraph = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      flushParagraph();
      continue;
    }

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (headingMatch) {
      flushList();
      flushParagraph();
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      continue;
    }

    const listMatch = /^[-*]\s+(.*)$/.exec(line);
    if (listMatch) {
      flushParagraph();
      currentList.push(listMatch[1].trim());
      continue;
    }

    currentParagraph.push(line);
  }

  flushList();
  flushParagraph();

  return blocks.map((block, index) => {
    if (block.type === "heading") {
      if (block.level <= 2) {
        return (
          <h4 key={`heading-${index}`} className="markdown-block-heading">
            {block.text}
          </h4>
        );
      }
      return (
        <h5 key={`heading-${index}`} className="markdown-block-subheading">
          {block.text}
        </h5>
      );
    }
    if (block.type === "list") {
      return (
        <ul key={`list-${index}`} className="markdown-block-list">
          {block.items.map((item, itemIndex) => (
            <li key={`item-${index}-${itemIndex}`}>{item}</li>
          ))}
        </ul>
      );
    }
    return (
      <p key={`paragraph-${index}`} className="markdown-block-paragraph">
        {block.text}
      </p>
    );
  });
}

export function Dashboard({
  tasks,
  selectedTask,
  isSubmitting,
  isChatting,
  isCancelling,
  isPolling,
  canCancel,
  taskListError,
  intakeMessages,
  intakeReadyToStart,
  onSendIntakeMessage,
  onStartResearch,
  onCancelAllTasks,
  onSelectTask,
}: DashboardProps) {
  const [chatInput, setChatInput] = useState("");
  const [expandedStageKey, setExpandedStageKey] = useState<string | null>(null);
  const stageListRef = useRef<HTMLDivElement | null>(null);
  const chatListRef = useRef<HTMLDivElement | null>(null);
  const progressStages: StageStatus[] = selectedTask?.stages ?? [];

  const getWorkflowLabel = (workflowName: string) => WORKFLOW_LABELS[workflowName] ?? workflowName;
  const getStageLabel = (stageName: string) => STAGE_LABELS[stageName] ?? stageName;

  const formatStageDetail = (stage: StageStatus) => {
    if (stage.detail_json) {
      return JSON.stringify(stage.detail_json, null, 2);
    }
    return stage.message ?? "";
  };

  const scrollToLatest = (node: HTMLDivElement | null) => {
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  };

  const updateStageScrollState = () => {
    const node = stageListRef.current;
    if (!node) {
      return;
    }
  };

  useEffect(() => {
    scrollToLatest(stageListRef.current);
  }, [progressStages, expandedStageKey, selectedTask]);

  useEffect(() => {
    scrollToLatest(chatListRef.current);
  }, [intakeMessages, isChatting]);

  return (
    <div className="dashboard-shell">
      <aside className="history-panel">
        <div className="panel-header">
          <h2>历史任务</h2>
        </div>
        <div className="history-list">
          {taskListError && <p className="history-error">历史任务加载失败</p>}
          {tasks.map((task) => (
            <button key={task.task_id} className="history-card" onClick={() => onSelectTask(task.task_id)}>
              <span className={`status-chip status-${task.status}`}>{task.status}</span>
              <strong>{task.prompt}</strong>
              <small>{task.summary ?? "等待结果"}</small>
            </button>
          ))}
          {!taskListError && !tasks.length && <p className="empty-state">暂无历史任务。</p>}
        </div>
      </aside>

      <main className="workspace-panel">
        <section className="hero-panel">
          <div>
            <h1>市场调研助手</h1>
            <p className="lead">输入调研需求，为您分析价格报表与商业模式</p>
          </div>
        </section>

        <section className="panel-grid">
          <section className="glass-panel progress-panel">
            <div className="panel-header">
              <h2>任务进度</h2>
            </div>
            <div className="stage-list" ref={stageListRef} onScroll={updateStageScrollState}>
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

          <section className="glass-panel intake-panel">
            <div className="panel-header">
              <h2>开始调研</h2>
            </div>
            <div className="intake-chat-shell">
              <div className="intake-chat-list" ref={chatListRef}>
                {intakeMessages.length ? (
                  intakeMessages.map((message, index) => (
                    <div
                      key={`${message.role}-${index}`}
                      className={`chat-bubble chat-bubble-${message.role}`}
                    >
                      <span className="chat-role">{message.role === "assistant" ? "澄清助手" : "你"}</span>
                      <p>{message.content}</p>
                    </div>
                  ))
                ) : (
                  <p className="empty-state"></p>
                )}
              </div>
            </div>
            <form
              className="prompt-form prompt-form-panel"
              onSubmit={(event) => {
                event.preventDefault();
                const trimmed = chatInput.trim();
                if (!trimmed) {
                  return;
                }
                void onSendIntakeMessage(trimmed);
                setChatInput("");
              }}
            >
              <textarea
                id="research-prompt"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="例如：我想调研中国大陆宠物烘干箱市场，重点看价格和平台"
                rows={3}
              />
              <div className="chat-submit-row">
                <button type="submit" className="hero-action-button chat-send-button" disabled={isChatting || isSubmitting || isCancelling}>
                  {isChatting ? "发送中..." : "发送"}
                </button>
              </div>
              <div className="hero-actions">
                <button
                  type="button"
                  className="hero-action-button"
                  disabled={!intakeReadyToStart || isSubmitting || isCancelling}
                  onClick={onStartResearch}
                >
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
                <span className="hero-status-text">
                  {isPolling ? "当前任务进行中" : intakeReadyToStart ? "可开始调研" : "先继续澄清需求"}
                </span>
              </div>
            </form>
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
              <h2>价格分析图表</h2>
            </div>
            <PriceChartsPanel priceReport={selectedTask?.price_report ?? null} />
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
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
                      <td>{formatPriceWithUnit(row.normalized_price, row.price_unit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!selectedTask?.price_report?.rows?.length && <p className="empty-state">暂无价格明细。</p>}
            </div>
          </section>

          <section className="glass-panel span-two">
            <div className="panel-header">
              <h2>市场分析</h2>
            </div>
            {selectedTask?.market_analysis ? (
              <div className="analysis-grid">
                <article>
                  <h3>商业模式</h3>
                  <div className="markdown-content">{renderMarkdownBlocks(selectedTask.market_analysis.revenue_model_text)}</div>
                </article>
                <article>
                  <h3>竞争与前景</h3>
                  <div className="markdown-content">{renderMarkdownBlocks(selectedTask.market_analysis.competition_text)}</div>
                </article>
                <article>
                  <h3>如何从零开始</h3>
                  <div className="markdown-content">{renderMarkdownBlocks(selectedTask.market_analysis.build_plan_text)}</div>
                </article>
                {!!selectedTask.market_analysis.summary_json.data_quality?.length && (
                  <article>
                    <h3>数据质量提示</h3>
                    <div className="markdown-content">
                      {renderMarkdownBlocks(selectedTask.market_analysis.summary_json.data_quality.map((item) => `- ${item}`).join("\n"))}
                    </div>
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
