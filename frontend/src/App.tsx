import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dashboard } from "./features/research/dashboard";
import {
  cancelAllResearchTasks,
  chatResearchIntake,
  createResearchTask,
  fetchResearchTaskDetail,
  fetchResearchTasks,
} from "./features/research/api";
import type {
  IntakeMessage,
  ResearchIntakeChatResponse,
  ResearchRequirementDraft,
  ResearchTaskDetail,
} from "./features/research/types";

const EMPTY_REQUIREMENT_DRAFT: ResearchRequirementDraft = {
  market_topic: "",
  target_region: "",
  products: [],
  goals: [],
  constraints: {},
};

export function App() {
  const queryClient = useQueryClient();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [intakeMessages, setIntakeMessages] = useState<IntakeMessage[]>([]);
  const [draftRequirement, setDraftRequirement] = useState<ResearchRequirementDraft>(EMPTY_REQUIREMENT_DRAFT);
  const [missingFields, setMissingFields] = useState<string[]>(["target_region", "products", "goals"]);
  const [intakeReadyToStart, setIntakeReadyToStart] = useState(false);
  const [intakeFinalPrompt, setIntakeFinalPrompt] = useState("");

  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: fetchResearchTasks,
    refetchInterval: 10_000,
  });

  const taskDetailQuery = useQuery({
    queryKey: ["task", selectedTaskId],
    queryFn: () => fetchResearchTaskDetail(selectedTaskId!),
    enabled: Boolean(selectedTaskId),
    refetchInterval: () => {
      const detail = queryClient.getQueryData<ResearchTaskDetail>(["task", selectedTaskId]);
      if (!selectedTaskId) {
        return false;
      }
      return detail?.task.status === "running" || detail?.task.status === "queued" ? 5_000 : false;
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: createResearchTask,
    onSuccess: async ({ task_id }) => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setSelectedTaskId(task_id);
      setIntakeMessages([]);
      setDraftRequirement(EMPTY_REQUIREMENT_DRAFT);
      setMissingFields(["target_region", "products", "goals"]);
      setIntakeReadyToStart(false);
      setIntakeFinalPrompt("");
      await queryClient.invalidateQueries({ queryKey: ["task", task_id] });
    },
  });

  const chatIntakeMutation = useMutation({
    mutationFn: chatResearchIntake,
  });

  const cancelTasksMutation = useMutation({
    mutationFn: cancelAllResearchTasks,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      if (selectedTaskId) {
        await queryClient.invalidateQueries({ queryKey: ["task", selectedTaskId] });
      }
    },
  });

  const selectedTask = taskDetailQuery.data ?? null;
  const tasks = tasksQuery.data ?? [];

  const isPolling = useMemo(
    () => Boolean(selectedTask && (selectedTask.task.status === "running" || selectedTask.task.status === "queued")),
    [selectedTask],
  );
  const canCancel = useMemo(
    () => tasks.some((task) => task.status === "queued" || task.status === "running"),
    [tasks],
  );

  const handleSendIntakeMessage = async (content: string) => {
    const nextMessages = [...intakeMessages, { role: "user", content }];
    setIntakeMessages(nextMessages);
    const response: ResearchIntakeChatResponse = await chatIntakeMutation.mutateAsync({
      messages: nextMessages,
      draft_requirement: draftRequirement,
    });
    setIntakeMessages([...nextMessages, { role: "assistant", content: response.assistant_message }]);
    setDraftRequirement(response.draft_requirement);
    setMissingFields(response.missing_fields);
    setIntakeReadyToStart(response.ready_to_start);
    setIntakeFinalPrompt(response.final_prompt);
  };

  const handleStartResearch = () => {
    if (!intakeReadyToStart || !intakeFinalPrompt.trim()) {
      return;
    }
    createTaskMutation.mutate(intakeFinalPrompt.trim());
  };

  return (
    <Dashboard
      tasks={tasks}
      selectedTask={selectedTask}
      isSubmitting={createTaskMutation.isPending}
      isChatting={chatIntakeMutation.isPending}
      isCancelling={cancelTasksMutation.isPending}
      isPolling={isPolling}
      canCancel={canCancel}
      taskListError={tasksQuery.error instanceof Error ? tasksQuery.error.message : null}
      intakeMessages={intakeMessages}
      intakeReadyToStart={intakeReadyToStart}
      onSendIntakeMessage={handleSendIntakeMessage}
      onStartResearch={handleStartResearch}
      onCancelAllTasks={() => cancelTasksMutation.mutate()}
      onSelectTask={setSelectedTaskId}
    />
  );
}
