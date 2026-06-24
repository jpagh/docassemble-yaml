import { runTests as runExtensionTests } from "./extension.test";
import { runTests as runServerLifecycleTests } from "./server-lifecycle.test";
import { runTests as runConfigTests } from "./config.test";
import { runTests as runDiagnosticsTests } from "./diagnostics.test";

export async function run(): Promise<void> {
  const errors: unknown[] = [];

  for (const [name, run] of [
    ["Extension", runExtensionTests],
    ["Server lifecycle", runServerLifecycleTests],
    ["Config", runConfigTests],
    ["Diagnostics", runDiagnosticsTests],
  ] as const) {
    try {
      await run();
    } catch (e) {
      errors.push(e);
      console.error(`Suite "${name}" failed, continuing with next suite...`);
    }
  }

  if (errors.length > 0) {
    throw new Error(`${errors.length} suite(s) failed.`);
  }
}
