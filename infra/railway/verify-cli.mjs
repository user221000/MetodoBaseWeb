import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { isAbsolute } from "node:path";
import { execFileSync } from "node:child_process";

const pinned = JSON.parse(readFileSync(new URL("./tooling.json", import.meta.url), "utf8")).cli;
const executable = process.argv[2];
if (!executable || !isAbsolute(executable)) throw new Error("Supply the absolute path to the existing native Railway executable.");
if (process.platform !== "win32" || process.arch !== "x64") throw new Error("This manifest only pins the observed Windows x64 executable.");
const sha256 = createHash("sha256").update(readFileSync(executable)).digest("hex");
if (sha256 !== pinned.sha256) throw new Error("Railway executable differs from the reviewed bytes; do not run it through this verifier.");
const options = { encoding: "utf8", windowsHide: true, timeout: 10000 };
const version = execFileSync(executable, ["--version"], options).trim();
if (version !== `railway ${pinned.version}`) throw new Error("Unexpected native Railway CLI version.");
const help = execFileSync(executable, ["config", "plan", "--help"], options);
for (const flag of ["--file", "--detailed-exit-code", "--out", "--source-tree"]) {
  if (!help.includes(flag)) throw new Error("Required plan option is unavailable.");
}
process.stdout.write(JSON.stringify({ version, sha256, platform: process.platform, arch: process.arch,
  commands: ["--version", "config plan --help"], providerStateRead: false, planExecuted: false, applyExecuted: false }, null, 2) + "\n");
