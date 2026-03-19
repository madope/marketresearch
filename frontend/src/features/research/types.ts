export interface ResearchTaskSummary {
  task_id: string;
  prompt: string;
  status: string;
  summary: string | null;
  created_at: string;
}

export interface IntakeMessage {
  role: string;
  content: string;
}

export interface ResearchRequirementDraft {
  market_topic: string;
  target_region: string;
  products: string[];
  goals: string[];
  constraints: Record<string, unknown>;
}

export interface ResearchIntakeChatResponse {
  assistant_message: string;
  draft_requirement: ResearchRequirementDraft;
  missing_fields: string[];
  ready_to_start: boolean;
  final_prompt: string;
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
  platform_domain?: string;
  product_url?: string | null;
  normalized_price: number | null;
  currency: string;
  price_unit?: string | null;
  source?: string;
  notes?: string;
  attempt_count?: number;
}

export interface ProductPlatformPriceSeries {
  platform_name: string;
  values: Array<number | null>;
}

export interface CoverageCell {
  product_name: string;
  platform_name: string;
  has_price: boolean;
  price: number | null;
  product_url: string;
}

export interface PriceReportCharts {
  product_platform_prices: {
    products: string[];
    series: ProductPlatformPriceSeries[];
  };
  platform_average_prices: Array<{
    platform_name: string;
    average_price: number;
    sample_size: number;
  }>;
  coverage_matrix: {
    products: string[];
    platforms: string[];
    cells: CoverageCell[];
  };
  source_breakdown: Array<{
    source: string;
    count: number;
  }>;
  product_price_ranges: Array<{
    product_name: string;
    min_price: number;
    max_price: number;
    average_price: number;
    sample_size: number;
  }>;
}

export interface PriceReport {
  average_price: number;
  highest_price: number;
  lowest_price: number;
  sample_size: number;
  row_count?: number;
  platform_count: number;
  fallback_used: boolean;
  warnings: string[];
  source_breakdown: Record<string, number>;
  platform_source_breakdown?: Record<string, number>;
  charts?: PriceReportCharts;
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
