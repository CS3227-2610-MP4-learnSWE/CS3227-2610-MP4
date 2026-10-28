import { createContext, useContext, useState, type ReactNode } from "react";
import { initialMessages, type Role, type DemoMessage } from "./data";

type DemoState = {
  completed: string[];
  toggleCompleted: (id: string) => void;
  answers: Record<string, string>;
  answer: (id: string, value: string) => void;
  submitted: boolean;
  submit: () => void;
  resetPractice: () => void;
  messages: Record<Role, DemoMessage[]>;
  read: (role: Role, id: string) => void;
};
const Context = createContext<DemoState | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [completed, setCompleted] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [messages, setMessages] = useState<Record<Role, DemoMessage[]>>({
    student: initialMessages.map((m) => ({ ...m })),
    teacher: initialMessages.map((m) => ({ ...m })),
    admin: [],
  });
  const value: DemoState = {
    completed,
    toggleCompleted: (id) =>
      setCompleted((items) =>
        items.includes(id)
          ? items.filter((item) => item !== id)
          : [...items, id],
      ),
    answers,
    answer: (id, value) => setAnswers((items) => ({ ...items, [id]: value })),
    submitted,
    submit: () => setSubmitted(true),
    resetPractice: () => {
      setSubmitted(false);
      setAnswers({});
    },
    messages,
    read: (role, id) =>
      setMessages((items) => ({
        ...items,
        [role]: items[role].map((m) =>
          m.id === id ? { ...m, unread: false } : m,
        ),
      })),
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useDemo() {
  const state = useContext(Context);
  if (!state) throw new Error("DemoProvider is required");
  return state;
}
