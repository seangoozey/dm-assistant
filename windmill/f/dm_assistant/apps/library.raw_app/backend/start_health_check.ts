import * as wmill from "windmill-client";

export async function main(): Promise<string> {
  return wmill.runScriptByPathAsync("f/dm_assistant/jobs/campaign_core_health");
}
