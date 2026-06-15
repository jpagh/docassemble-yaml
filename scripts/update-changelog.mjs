import { readFileSync, writeFileSync } from "fs";
import { execSync } from "child_process";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const newVersion = readFileSync(join(root, "VERSION"), "utf-8").trim();

if (newVersion.includes("-")) {
  console.log(`Pre-release ${newVersion}; skipping CHANGELOG update`);
  process.exit(0);
}

const today = new Date().toISOString().slice(0, 10);

const unreleasedHeader = "## [Unreleased]";

const changelogPath = join(root, "CHANGELOG.md");
let changelog = readFileSync(changelogPath, "utf-8");

if (!changelog.includes(unreleasedHeader)) {
  console.error("No [Unreleased] section found in CHANGELOG.md");
  process.exit(1);
}

changelog = changelog.replace(unreleasedHeader, `## [${newVersion}] - ${today}`);

changelog = changelog.replace("# Changelog\n\n", `# Changelog\n\n## [Unreleased]\n\n`);

writeFileSync(changelogPath, changelog, "utf-8");

execSync("git add CHANGELOG.md", { cwd: root });

console.log(`CHANGELOG: [Unreleased] → [${newVersion}] - ${today}`);
