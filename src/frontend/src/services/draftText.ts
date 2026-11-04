// Python str.strip also recognises these four control whitespace characters.
export function strip(text: string) {
  const whitespace = (char: string) =>
    /\p{White_Space}/u.test(char) ||
    [28, 29, 30, 31].includes(char.charCodeAt(0));
  let start = 0;
  let end = text.length;
  while (start < end && whitespace(text[start])) start++;
  while (end > start && whitespace(text[end - 1])) end--;
  return text.slice(start, end);
}
export const normalise = (text: string) => strip(text.replace(/\r\n?/g, "\n"));
export const count = (text: string) => Array.from(text).length;
export const invalidText = (text: string) =>
  text.includes("\0") || /[\ud800-\udfff]/u.test(text);
