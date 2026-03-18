import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dashboard } from "./features/research/dashboard";
import {
  cancelAllResearchTasks,
  createResearchTask,
  fetchResearchTaskDetail,
  fetchResearchTasks,
} from "./features/research/api";
import type { ResearchTaskDetail } from "./features/research/types";

export function App() {
  const queryClient = useQueryClient();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

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
      await queryClient.invalidateQueries({ queryKey: ["task", task_id] });
    },
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

  return (
    <Dashboard
      tasks={tasks}
      selectedTask={selectedTask}
      isSubmitting={createTaskMutation.isPending}
      isCancelling={cancelTasksMutation.isPending}
      isPolling={isPolling}
      canCancel={canCancel}
      onSubmit={(prompt) => createTaskMutation.mutate(prompt)}
      onCancelAllTasks={() => cancelTasksMutation.mutate()}
      onSelectTask={setSelectedTaskId}
    />
  );
}
