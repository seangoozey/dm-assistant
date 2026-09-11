import * as wmill from "windmill-client";

export async function main(candidate_ids: string[]): Promise<string> {
  if (candidate_ids.length < 1 || candidate_ids.length > 50) {
    throw new Error("candidate_ids must contain 1 to 50 items");
  }
  return wmill.runScriptByPathAsync("f/dm_assistant/jobs/candidate_extraction", {
    candidate_ids,
  });
}
