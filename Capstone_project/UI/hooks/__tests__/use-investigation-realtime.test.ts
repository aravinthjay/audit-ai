import { describe, expect, it } from "vitest";
import { messageFromRealtimeEvent } from "@/hooks/use-investigation-realtime";

describe("investigation realtime", () => {
  it("formats known events and ignores websocket acknowledgements", () => {
    expect(messageFromRealtimeEvent({ type: "ack" })).toBeNull();
    expect(
      messageFromRealtimeEvent({
        type: "pipeline_stage",
        from_stage: "collecting_evidence",
        to_stage: "agent_debate",
      }),
    ).toBe("Pipeline moved from collecting_evidence to agent_debate.");
    expect(
      messageFromRealtimeEvent({
        type: "debate_message",
        speaker: "challenger",
        round: 2,
      }),
    ).toBe("challenger posted debate round 2.");
  });
});
