export type Role = "student" | "teacher" | "admin";
/** Roles offered by the anonymous demo shortcut and switcher; the admin area has no demo. */
export const demoRoles: Role[] = ["student", "teacher"];
export const names: Record<Role, string> = {
  student: "Alex",
  teacher: "Jamie",
  admin: "Morgan",
};
export const navigation: Record<
  Role,
  { path: string; label: string; icon: string; landing?: string }[]
> = {
  student: [
    { path: "overview", label: "Overview", icon: "overview" },
    { path: "materials", label: "Study materials", icon: "book" },
    { path: "practice", label: "Practice", icon: "code" },
    { path: "progress", label: "Progress", icon: "overview" },
    { path: "inbox", label: "Inbox", icon: "inbox" },
  ],
  teacher: [
    { path: "overview", label: "Overview", icon: "overview" },
    { path: "materials", label: "Materials library", icon: "book" },
    { path: "generate", label: "AI content studio", icon: "sparkles" },
    { path: "review", label: "Published content", icon: "review" },
    { path: "inbox", label: "Inbox", icon: "inbox" },
  ],
  admin: [
    { path: "analytics", label: "Feature Analytics", icon: "usage" },
    {
      path: "feedback-hub",
      label: "Feedback hub",
      icon: "forms",
      landing: "forms",
    },
    { path: "users", label: "Users", icon: "people" },
    { path: "courses", label: "Courses", icon: "book" },
  ],
};
export const initialMessages = [
  {
    id: "survey",
    title: "Help shape your learning experience",
    sender: "learnSWE team",
    time: "10:30 AM",
    category: "Survey",
    unread: true,
    body: "We’re exploring ways to make learning feel more intuitive. Tell us what is working and what we can improve. This sample survey takes about two minutes.",
    survey: true,
  },
  {
    id: "update",
    title: "A little more guidance, a lot more clarity",
    sender: "Morgan · Admin",
    time: "Yesterday",
    category: "Product update",
    unread: true,
    body: "Your feedback inspired a hints-first study companion. It helps you work through a question without jumping straight to the answer. This is a sample announcement.",
    survey: false,
  },
  {
    id: "welcome",
    title: "Welcome to a space for progress",
    sender: "learnSWE team",
    time: "Monday",
    category: "Welcome",
    unread: false,
    body: "Learning software engineering is a journey. Start with a lesson, try a practice set and ask for a hint whenever you need a nudge. You’ve got this.",
    survey: false,
  },
];
export type DemoMessage = (typeof initialMessages)[number];
