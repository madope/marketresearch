import type {
  IntakeMessage,
  ResearchIntakeChatResponse,
  ResearchRequirementDraft,
  ResearchTaskDetail,
  ResearchTaskSummary,
  StageStatus,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function createResearchTask(prompt: string): Promise<{ task_id: string; status: string }> {
  return request("/research-tasks", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function cancelAllResearchTasks(): Promise<{ status: string; cancelled_count: number }> {
  return request("/research-tasks/cancel-all", {
    method: "POST",
  });
}

export async function fetchResearchTasks(): Promise<ResearchTaskSummary[]> {
  return request("/research-tasks");
}

export async function fetchResearchTaskDetail(taskId: string): Promise<ResearchTaskDetail> {
  return request(`/research-tasks/${taskId}`);
}

export async function fetchResearchTaskStatus(
  taskId: string,
): Promise<{ task_id: string; status: string; stages: StageStatus[] }> {
  return request(`/research-tasks/${taskId}/status`);
}

export async function chatResearchIntake(payload: {
  messages: IntakeMessage[];
  draft_requirement: ResearchRequirementDraft;
}): Promise<ResearchIntakeChatResponse> {
  return request("/research-intake/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
