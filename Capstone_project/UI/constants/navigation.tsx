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
    label: "Main",
    items: [
      { label: "Dashboard", href: routes.dashboard, icon: LayoutDashboard },
      { label: "Upload data", href: routes.intake, icon: FileUp },
      { label: "Cases", href: routes.investigations, icon: FolderKanban },
      { label: "Case workspace", href: routes.workspace, icon: Target },
    ],
  },
  {
    label: "Review a case",
    items: [
      { label: "AI debate", href: routes.debate, icon: MessagesSquare },
      { label: "Evidence", href: routes.evidence, icon: FileSearch },
      { label: "Fact check", href: routes.verification, icon: CheckSquare },
      { label: "My review", href: routes.review, icon: UserCheck },
      { label: "Step-by-step replay", href: routes.replay, icon: Play },
    ],
  },
  {
    label: "Results & setup",
    items: [
      { label: "Reports", href: routes.reports, icon: FileText },
      { label: "Activity log", href: routes.auditLogs, icon: ShieldCheck },
      { label: "Analytics", href: routes.analytics, icon: BarChart3 },
      { label: "Quality scores", href: routes.evaluation, icon: FlaskConical },
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

