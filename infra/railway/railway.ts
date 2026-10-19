import { readFileSync } from "node:fs";
import { defineRailway } from "railway/iac";
import { buildCandidate, type CandidateReview } from "./candidate.ts";

// Explicit --file only. No auto-discovered .railway/railway.ts is installed.
export { partial } from "./candidate.ts";

export default defineRailway((ctx) => {
  const manifest = process.env.METODOBASE_RAILWAY_REVIEW_MANIFEST;
  if (!manifest) throw new Error("Set a reviewed local import manifest; no release target or digest is supplied by default.");
  const review = JSON.parse(readFileSync(manifest, "utf8")) as CandidateReview;
  return buildCandidate(ctx, review);
});
