export type Role = "student" | "teacher" | "admin";
export const roles: Role[] = ["student", "teacher", "admin"];
export const names: Record<Role, string> = {
  student: "Alex",
  teacher: "Jamie",
  admin: "Morgan",
};
export const navigation: Record<
  Role,
  { path: string; label: string; icon: string }[]
> = {
  student: [
    { path: "overview", label: "Overview", icon: "overview" },
    { path: "materials", label: "Study materials", icon: "book" },
    { path: "practice", label: "Practice", icon: "code" },
    { path: "inbox", label: "Inbox", icon: "inbox" },
  ],
  teacher: [
    { path: "overview", label: "Overview", icon: "overview" },
    { path: "materials", label: "Materials library", icon: "book" },
    { path: "generate", label: "AI content studio", icon: "sparkles" },
    { path: "review", label: "Review & publish", icon: "review" },
    { path: "practice", label: "Practice sets", icon: "code" },
    { path: "inbox", label: "Inbox", icon: "inbox" },
  ],
  admin: [
    { path: "overview", label: "Analytics", icon: "overview" },
    { path: "forms", label: "Feedback forms", icon: "forms" },
    { path: "responses", label: "Feedback insights", icon: "sparkles" },
    { path: "announcements", label: "Announcements", icon: "inbox" },
    { path: "users", label: "People & access", icon: "people" },
    { path: "usage", label: "AI usage", icon: "usage" },
  ],
};
export const lessons = [
  {
    id: "clean-code",
    title: "Small functions, clear intentions",
    topic: "Clean code",
    description: "Write code your future self will thank you for.",
    duration: "12 min",
    chapter: "03",
    tone: "blue",
    progress: 65,
    sourceStatus: "Published",
    updated: "Today",
  },
  {
    id: "testing",
    title: "Tests that give you confidence",
    topic: "Software testing",
    description: "Build a safety net, one useful test at a time.",
    duration: "18 min",
    chapter: "04",
    tone: "purple",
    progress: 0,
    sourceStatus: "Draft",
    updated: "Yesterday",
  },
  {
    id: "git",
    title: "A better way to work together",
    topic: "Version control",
    description: "Branches, commits and thoughtful collaboration.",
    duration: "15 min",
    chapter: "05",
    tone: "green",
    progress: 0,
    sourceStatus: "Draft",
    updated: "Yesterday",
  },
];
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
export const feedback = [
  {
    id: "FB-024",
    author: "Student 024",
    tag: "AI companion",
    quote:
      "The hints help me think it through instead of just copying an answer.",
    sentiment: "Positive",
  },
  {
    id: "FB-025",
    author: "Teacher 008",
    tag: "Content studio",
    quote:
      "I would like to see the original material next to the generated notes.",
    sentiment: "Suggestion",
  },
  {
    id: "FB-026",
    author: "Student 031",
    tag: "Practice",
    quote:
      "It would help to have a clearer explanation after submitting the set.",
    sentiment: "Suggestion",
  },
];
export const weeklyActivity = [42, 68, 51, 85, 62, 95, 74];
