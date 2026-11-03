/** Anonymous demo mode is on unless the build sets VITE_ENABLE_DEMO_ACCESS=false. Presentation only. */
export function demoAccessEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_DEMO_ACCESS !== "false";
}
