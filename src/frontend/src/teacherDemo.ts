// Placeholder question data for the teacher demo screens only. Never import from student code.
export const questions = [
  {
    id: "responsibility",
    text: "What should a well-designed function have?",
    options: [
      "A single, focused responsibility",
      "As many responsibilities as possible",
      "No descriptive name",
    ],
    answer: "A single, focused responsibility",
    explanation:
      "One focused responsibility makes a function easier to understand, test and change.",
  },
  {
    id: "regression",
    text: "Why do we keep automated tests alongside our code?",
    options: [
      "To make the repository larger",
      "To catch regressions when code changes",
      "To avoid ever reviewing code",
    ],
    answer: "To catch regressions when code changes",
    explanation:
      "Tests protect expected behaviour and can catch regressions introduced by later changes.",
  },
  {
    id: "loop",
    text: "What does this Python code print?",
    code: "values = [1, 2, 3]\nprint(len(values))",
    options: ["1", "2", "3"],
    answer: "3",
    explanation:
      "len returns the number of items. The list contains three items.",
  },
];
