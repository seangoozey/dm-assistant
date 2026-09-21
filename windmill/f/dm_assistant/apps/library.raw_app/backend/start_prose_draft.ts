import * as wmill from "windmill-client";

export async function main(command: unknown): Promise<string> {
  if (typeof command !== "object" || command === null) {
    throw new Error("command must be the prose draft command object");
  }
  return wmill.runScriptByPathAsync("f/dm_assistant/jobs/prose_draft", { command });
}
