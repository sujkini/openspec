import type { TaskExecution, TaskStatus } from "@/types";

const TASK_STATUS_ICONS: Record<TaskStatus, string> = {
  passed: "✅",
  failed: "❌",
  running: "🔄",
  pending: "⏳",
  waiting: "🟡",
  skipped: "⏭️",
};

interface TaskRowProps {
  task: TaskExecution;
}

function VerificationBadge({ metadata }: { metadata?: Record<string, unknown> | null }) {
  if (!metadata) return null;

  const badges: { label: string; ok: boolean }[] = [];

  if (metadata.build_status !== undefined) {
    badges.push({
      label: "Build",
      ok: metadata.build_status === "passed" || metadata.build_status === true,
    });
  }
  if (metadata.test_status !== undefined) {
    badges.push({
      label: "Test",
      ok: metadata.test_status === "passed" || metadata.test_status === true,
    });
  }
  if (metadata.verify_status !== undefined) {
    badges.push({
      label: "Verify",
      ok: metadata.verify_status === "passed" || metadata.verify_status === true,
    });
  }

  if (badges.length === 0) return null;

  return (
    <span className="ml-2 inline-flex gap-1">
      {badges.map((b) => (
        <span
          key={b.label}
          className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
            b.ok
              ? "bg-green-900/40 text-green-400 border border-green-700/50"
              : "bg-red-900/40 text-red-400 border border-red-700/50"
          }`}
        >
          {b.ok ? "✓" : "✗"} {b.label}
        </span>
      ))}
    </span>
  );
}

export default function TaskRow({ task }: TaskRowProps) {
  const icon = TASK_STATUS_ICONS[task.status] ?? "⏳";

  return (
    <tr className="border-b border-terminal-border/30 hover:bg-terminal-surface/20 transition-colors">
      <td className="px-4 py-1.5 text-xs pl-16">
        <span className="text-terminal-muted mr-1">⤷</span>
        <span className="font-mono">{task.task_id}</span>
        {task.task_title && (
          <span className="text-terminal-muted ml-1 truncate max-w-[200px] inline-block align-bottom">
            — {task.task_title}
          </span>
        )}
      </td>
      <td className="px-4 py-1.5 text-xs">
        {icon}{" "}
        <span
          className={
            task.status === "passed"
              ? "text-terminal-green"
              : task.status === "failed"
              ? "text-terminal-red"
              : task.status === "waiting"
              ? "text-terminal-yellow"
              : "text-terminal-text"
          }
        >
          {task.status.toUpperCase()}
        </span>
        <VerificationBadge metadata={task.metadata_json} />
      </td>
      <td className="px-4 py-1.5 text-xs text-center">
        {task.self_correction_loops > 0
          ? `${task.self_correction_loops} fix${task.self_correction_loops > 1 ? "es" : ""}`
          : "—"}
      </td>
      <td className="px-4 py-1.5 text-xs text-center text-terminal-muted">—</td>
      <td className="px-4 py-1.5 text-xs text-center font-mono">
        {task.tokens_in > 0 || task.tokens_out > 0
          ? `${formatTokens(task.tokens_in)} / ${formatTokens(task.tokens_out)}`
          : "—"}
      </td>
      <td className="px-4 py-1.5 text-xs text-terminal-muted">
        {task.agent_id || "—"}
      </td>
    </tr>
  );
}

function formatTokens(n: number): string {
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}
