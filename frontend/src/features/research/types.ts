export interface ResearchTaskSummary {
  task_id: string;
  prompt: string;
  status: string;
  summary: string | null;
  created_at: string;
}

export interface ResearchProduct {
  product_name: string;
  source_type: string;
  input_order: number;
}

export interface ResearchPlatform {
  platform_name: string;
  platform_domain: string;
  platform_url?: string | null;
  platform_summary?: string | null;
  discover_round: number;
  platform_type: string;
  source?: string;
}

export interface StageStatus {
  workflow_name: string;
  stage_name: string;
  status: string;
  message: string | null;
  retry_count: number;
  detail_json?: Record<string, unknown> | null;
}

export interface PriceReportRow {
  product_name: string;
  platform_name: string;
  normalized_price: number;
  currency: string;
  source?: string;
  attempt_count?: number;
}

export interface PriceReport {
  average_price: number;
  highest_price: number;
  lowest_price: number;
  sample_size: number;
  platform_count: number;
  fallback_used: boolean;
  warnings: string[];
  source_breakdown: Record<string, number>;
  platform_source_breakdown?: Record<string, number>;
  rows: PriceReportRow[];
}

export interface MarketAnalysis {
  revenue_model_text: string;
  competition_text: string;
  build_plan_text: string;
  summary_json: {
    risks: string[];
    opportunities: string[];
    data_quality?: string[];
  };
}

export interface ResearchTaskDetail {
  task: ResearchTaskSummary;
  products: ResearchProduct[];
  platforms: ResearchPlatform[];
  price_report: PriceReport | null;
  market_analysis: MarketAnalysis | null;
  stages: StageStatus[];
}
