import {
  image,
  preserve,
  project,
  service,
  type RailwayContext,
  type ServiceConfigInput,
} from "railway/iac";

export const PROJECT_ID = "5b6dc7c5-1bb0-47b3-9409-5cdf574a34ba";
export const PROJECT_NAME = "joyful-quietude";
export const PRODUCTION_ID = "56977cda-fbff-4a31-82c3-a88502eacf59";
export const SERVICE_NAME = "MetodoBaseWeb";
export const partial = "metodobase-web";

const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const SHA256 = /^[a-f0-9]{64}$/;
const COMMIT = /^[a-f0-9]{40}$/;
const VARIABLE_NAME = /^[A-Z][A-Z0-9_]*$/;
const IMMUTABLE_IMAGE = /^[a-z0-9][a-z0-9._-]*(?::[0-9]+)?\/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$/;

export const REQUIRED_SECRETS = [
  "DATABASE_URL", "MIGRATOR_DATABASE_URL", "WEB_SECRET_KEY", "METODO_BASE_SALT",
] as const;

export interface ReviewedTarget {
  name: string;
  id: string;
  kind: "existing" | "isolated";
  serviceId: string;
  configEtag: string;
  /** Hash of the separately reviewed, redacted import. Never variable values. */
  importSha256: string;
  /** This exact inventory comes from the import, not the old audit subset. */
  variableNames: string[];
  /** Imported service settings, excluding variables and external resources. */
  serviceSettings: ServiceConfigInput;
  /** Config as Code was detached by a separately authorized adoption. */
  legacyConfigDetached: boolean;
}

export interface CandidateReview {
  schemaVersion: 1;
  projectId: string;
  candidateImage: string;
  sourceCommit: string;
  imageEvidenceSha256: string;
  targets: ReviewedTarget[];
}

function requireCondition(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

export function buildCandidate(ctx: RailwayContext, review: CandidateReview) {
  requireCondition(ctx.command === "plan", "Prepared definition only supports plan; release adoption is still pending.");
  requireCondition(review?.schemaVersion === 1, "A reviewed import manifest is required.");
  requireCondition(ctx.projectId === PROJECT_ID && review.projectId === PROJECT_ID &&
    ctx.projectName === PROJECT_NAME, "Unexpected Railway project.");
  requireCondition(IMMUTABLE_IMAGE.test(review.candidateImage), "Use a tested registry image pinned by sha256 digest.");
  requireCondition(!review.candidateImage.includes("..") && !review.candidateImage.includes("//"), "Invalid image repository.");
  requireCondition(COMMIT.test(review.sourceCommit) && SHA256.test(review.imageEvidenceSha256), "Candidate source and image evidence are required.");
  requireCondition(Array.isArray(review.targets) && review.targets.length > 0, "An existing reviewed target is required.");
  requireCondition(new Set(review.targets.map(t => t.name)).size === review.targets.length &&
    new Set(review.targets.map(t => t.id)).size === review.targets.length, "Ambiguous target inventory.");
  const target = review.targets.find(t => t.name === ctx.environment && t.id === ctx.environmentId);
  requireCondition(target, "Target environment was not imported and reviewed.");
  requireCondition(UUID.test(target.id) && UUID.test(target.serviceId), "Target IDs are required.");
  requireCondition(target.name === "production"
    ? target.kind === "existing" && target.id === PRODUCTION_ID && target.serviceId === "66552210-e97e-47f3-946b-87ab0674ae75"
    : target.kind === "isolated" && target.id !== PRODUCTION_ID, "Target kind or identity mismatch.");
  requireCondition(target.legacyConfigDetached === true, "Legacy Config as Code adoption is not complete.");
  requireCondition(typeof target.configEtag === "string" && target.configEtag.length > 0 &&
    SHA256.test(target.importSha256), "A redacted import with its configuration etag is required.");
  requireCondition(Array.isArray(target.variableNames) && target.variableNames.length > 0 &&
    target.variableNames.every(name => VARIABLE_NAME.test(name)) &&
    new Set(target.variableNames).size === target.variableNames.length, "Invalid complete variable-name inventory.");
  requireCondition(REQUIRED_SECRETS.every(name => target.variableNames.includes(name)), "Prepare separate app/migrator credentials and required secrets before planning.");
  requireCondition(target.serviceSettings && typeof target.serviceSettings === "object" &&
    !Array.isArray(target.serviceSettings), "Imported service settings are required.");
  requireCondition(!("env" in target.serviceSettings) && !("variables" in target.serviceSettings), "Imported variable values are prohibited.");
  requireCondition(!target.serviceSettings.configFile, "Legacy configuration must be detached before IaC planning.");
  requireCondition(!target.serviceSettings.volumeMounts || Object.keys(target.serviceSettings.volumeMounts).length === 0,
    "Mounted storage requires a separate reviewed import; never drop or invent a volume here.");
  requireCondition(!target.serviceSettings.domains && !target.serviceSettings.networking,
    "Networking requires an explicit imported-resource review; no domains are created by this candidate.");
  const supportedSettings = new Set([
    "source", "root", "rootDirectory", "build", "deploy", "run", "start", "startCommand",
    "preDeploy", "preDeployCommand", "healthcheck", "healthcheckPath", "healthcheckTimeout",
    "replicas", "regions", "configFile", "volumeMounts",
  ]);
  requireCondition(Object.keys(target.serviceSettings).every(name => supportedSettings.has(name)),
    "Imported settings exceed the reviewed CLI compatibility surface.");

  // Preserve every imported name. This does not create credentials or validate
  // their roles: db_bootstrap and production startup enforce that contract.
  const env = Object.fromEntries(target.variableNames.map(name => [name, preserve()]));
  const web = service(SERVICE_NAME, {
    ...target.serviceSettings,
    source: image(review.candidateImage),
    preDeploy: "python db_bootstrap.py",
    start: "/app/entrypoint.sh",
    healthcheck: "/health/ready",
    healthcheckTimeout: 120,
    replicas: 1,
    deploy: {
      ...target.serviceSettings.deploy,
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
    env: { ...env, METODOBASE_ENV: "production" },
  });
  return project(PROJECT_NAME, { resources: [web] });
}
