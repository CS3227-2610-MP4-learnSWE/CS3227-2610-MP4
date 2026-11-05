import { createContext, useContext, useState, type ReactNode } from "react";
import { initialMessages, type Role, type DemoMessage } from "./data";

type DemoState = {
  messages: Record<Role, DemoMessage[]>;
  read: (role: Role, id: string) => void;
};
const Context = createContext<DemoState | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Record<Role, DemoMessage[]>>({
    student: initialMessages.map((m) => ({ ...m })),
    teacher: initialMessages.map((m) => ({ ...m })),
    admin: [],
  });
  const value: DemoState = {
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
