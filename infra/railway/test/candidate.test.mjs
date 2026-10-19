import assert from "node:assert/strict";
import { test } from "node:test";
import { createRailwayContext, project, validateGraph } from "railway/iac";
import definition, { partial } from "../railway.ts";
import { buildCandidate, PROJECT_ID, PROJECT_NAME, PRODUCTION_ID } from "../candidate.ts";

// Entirely synthetic release/import evidence. These identifiers never create
// a target, image, secret, ownership claim, or provider-side plan.
const isolatedId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const isolatedServiceId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
function fixture(environment = "production") {
  const production = environment === "production";
  const target = {
    name: environment,
    id: production ? PRODUCTION_ID : isolatedId,
    kind: production ? "existing" : "isolated",
    serviceId: production ? "66552210-e97e-47f3-946b-87ab0674ae75" : isolatedServiceId,
    configEtag: "synthetic-not-a-live-etag",
    importSha256: "1".repeat(64),
    variableNames: ["DATABASE_URL", "MIGRATOR_DATABASE_URL", "WEB_SECRET_KEY", "METODO_BASE_SALT", "EXISTING_IMPORTED_SETTING"],
    serviceSettings: { deploy: { drainingSeconds: 42, preDeployCommand: ["synthetic-old-migration"], startCommand: "synthetic-old-start", healthcheckPath: "/synthetic-old-health", numReplicas: 1 } },
    legacyConfigDetached: true,
  };
  return {
    ctx: createRailwayContext({ command: "plan", projectId: PROJECT_ID, projectName: PROJECT_NAME, environment, environmentId: target.id }),
    review: { schemaVersion: 1, projectId: PROJECT_ID, candidateImage: `ghcr.io/example/synthetic@sha256:${"a".repeat(64)}`, sourceCommit: "2".repeat(40), imageEvidenceSha256: "3".repeat(64), targets: [target] },
    target,
  };
}

for (const environment of ["production", "isolated-synthetic"]) {
  test(`SDK evaluates ${environment} settings without external resources`, () => {
    const { ctx, review } = fixture(environment);
    const result = buildCandidate(ctx, review);
    assert.equal(partial, "metodobase-web");
    assert.equal(result.name, PROJECT_NAME);
    assert.equal(result.resources.length, 1);
    const web = result.resources[0];
    assert.equal(web.type, "service");
    assert.equal(web.name, "MetodoBaseWeb");
    assert.equal(web.source.image, review.candidateImage);
    assert.deepEqual(web.deploy.preDeployCommand, ["python db_bootstrap.py"]);
    assert.equal(web.deploy.startCommand, "/app/entrypoint.sh");
    assert.equal(web.deploy.healthcheckPath, "/health/ready");
    assert.equal(web.deploy.healthcheckTimeout, 120);
    assert.equal(web.deploy.restartPolicyMaxRetries, 5);
    assert.equal(web.deploy.numReplicas, 1);
    assert.equal(web.deploy.drainingSeconds, 42);
    for (const [name, variable] of Object.entries(web.variables)) {
      if (name === "METODOBASE_ENV") assert.deepEqual(variable, { type: "literal", value: "production" });
      else assert.deepEqual(variable, { type: "preserve" });
    }
    assert.equal(Object.keys(web.variables).length, 6);
    assert.equal(web.volumeMounts, undefined);
    assert.equal(web.networking, undefined);
    assert.deepEqual(validateGraph({ version: 1, project: { name: result.name }, environments: [{ name: environment }], resources: result.resources, edges: [] }), []);
  });
}

for (const [label, change, message] of [
  ["apply command", f => { f.ctx.command = "apply"; }, /only supports plan/],
  ["wrong project", f => { f.ctx.projectId = isolatedId; }, /Unexpected Railway project/],
  ["unknown environment", f => { f.ctx.environment = "unknown"; }, /not imported/],
  ["production ID reused by isolated", f => { f.target.name = "isolated-synthetic"; f.target.kind = "isolated"; f.ctx.environment = f.target.name; }, /identity mismatch/],
  ["legacy configuration active", f => { f.target.legacyConfigDetached = false; }, /adoption is not complete/],
  ["empty digest", f => { f.review.candidateImage = ""; }, /pinned by sha256/],
  ["mutable image", f => { f.review.candidateImage = "ghcr.io/example/app:latest"; }, /pinned by sha256/],
  ["tag plus digest", f => { f.review.candidateImage = `ghcr.io/example/app:latest@sha256:${"a".repeat(64)}`; }, /pinned by sha256/],
  ["registry credential", f => { f.review.candidateImage = `user:password@registry.example/app@sha256:${"a".repeat(64)}`; }, /pinned by sha256/],
  ["no image evidence", f => { f.review.imageEvidenceSha256 = ""; }, /image evidence/],
  ["no imported etag", f => { f.target.configEtag = ""; }, /configuration etag/],
  ["no migrator secret", f => { f.target.variableNames = f.target.variableNames.filter(n => n !== "MIGRATOR_DATABASE_URL"); }, /separate app\/migrator/],
  ["duplicate variable", f => { f.target.variableNames.push("DATABASE_URL"); }, /variable-name inventory/],
  ["inline variable", f => { f.target.serviceSettings.env = { DATABASE_URL: "forbidden-synthetic-inline" }; }, /variable values are prohibited/],
  ["legacy config path", f => { f.target.serviceSettings.configFile = "railway.toml"; }, /must be detached/],
  ["unreviewed mounted storage", f => { f.target.serviceSettings.volumeMounts = { "/data": { volumeId: "synthetic" } }; }, /Mounted storage/],
  ["unreviewed domain", f => { f.target.serviceSettings.domains = ["synthetic.invalid"]; }, /Networking/],
  ["newer tracing setting", f => { f.target.serviceSettings.tracing = { enabled: true }; }, /compatibility surface/],
  ["unknown imported setting", f => { f.target.serviceSettings.unrecognizedSyntheticSetting = true; }, /compatibility surface/],
  ["duplicate target", f => { f.review.targets.push({ ...f.target }); }, /Ambiguous target/],
]) {
  test(`rejects ${label}`, () => {
    const f = fixture();
    change(f);
    assert.throws(() => buildCandidate(f.ctx, f.review), message);
  });
}

test("authoring file supplies no default target, digest, or release", () => {
  const previous = process.env.METODOBASE_RAILWAY_REVIEW_MANIFEST;
  delete process.env.METODOBASE_RAILWAY_REVIEW_MANIFEST;
  try { assert.throws(() => definition(fixture().ctx, project), /no release target or digest/); }
  finally {
    if (previous === undefined) delete process.env.METODOBASE_RAILWAY_REVIEW_MANIFEST;
    else process.env.METODOBASE_RAILWAY_REVIEW_MANIFEST = previous;
  }
});
