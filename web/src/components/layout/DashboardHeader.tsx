interface DashboardHeaderProps {
  branch: string;
}

export default function DashboardHeader({ branch }: DashboardHeaderProps) {
  return (
    <header className="bg-terminal-surface border-b border-terminal-border px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-terminal-accent font-bold text-sm tracking-wider">
          [SDLC OBSERVABILITY]
        </span>
        <span className="text-terminal-text font-bold text-sm">
          AGENTIC AI DEVELOPMENT PIPELINE DASHBOARD
        </span>
      </div>
      {branch && (
        <div className="text-terminal-muted text-xs">
          Branch:{" "}
          <span className="text-terminal-accent font-medium">{branch}</span>
        </div>
      )}
    </header>
  );
}
