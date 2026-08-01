import { parse } from "smol-toml";

export function parsePyproject(text) {
  const data = parse(text);
  const version = data.project?.version ?? "unknown";
  const deps = Array.isArray(data.project?.dependencies) ? data.project.dependencies : [];
  return { version, deps };
}
