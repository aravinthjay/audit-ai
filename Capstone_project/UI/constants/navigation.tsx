import {
  BarChart3,
  BookOpen,
  FileUp,
  FlaskConical,
  CheckSquare,
  FileSearch,
  FileText,
  FolderKanban,
  LayoutDashboard,
  MessagesSquare,
  Play,
  Settings,
  ShieldCheck,
  Target,
  UserCheck,
} from "lucide-react";
import { routes } from "@/constants/routes";

export const navigationSections = [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", href: routes.dashboard, icon: LayoutDashboard },
      { label: "Case intake", href: routes.intake, icon: FileUp },
      { label: "Investigations", href: routes.investigations, icon: FolderKanban },
      { label: "Workspace", href: routes.workspace, icon: Target },
    ],
  },
  {
    label: "Investigation",
    items: [
      { label: "Debate viewer", href: routes.debate, icon: MessagesSquare },
      { label: "Evidence explorer", href: routes.evidence, icon: FileSearch },
      { label: "Verification", href: routes.verification, icon: CheckSquare },
      { label: "Human review", href: routes.review, icon: UserCheck },
      { label: "Replay", href: routes.replay, icon: Play },
    ],
  },
  {
    label: "Output",
    items: [
      { label: "Reports", href: routes.reports, icon: FileText },
      { label: "Audit logs", href: routes.auditLogs, icon: ShieldCheck },
      { label: "Analytics", href: routes.analytics, icon: BarChart3 },
      { label: "RAGAS evaluation", href: routes.evaluation, icon: FlaskConical },
      { label: "Knowledge base", href: routes.knowledgeBase, icon: BookOpen },
      { label: "Settings", href: routes.settings, icon: Settings },
    ],
  },
] as const;

export const commandItems = navigationSections.flatMap((section) =>
  section.items.map((item) => ({
    ...item,
    section: section.label,
  })),
);

