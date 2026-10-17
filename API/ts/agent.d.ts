declare namespace agent {
  // The turn loop on the AI thread. One `turn_run` per player action:
  // append the turn, call the provider with the tools, run each tool
  // call through the MCP clients, repeat until a reply has no tool
  // calls, write the scene and world documents touched, render.
  class Agent {
    constructor(
      model: provider.Provider,
      clients: mcp.ClientSet,
      store: substrate.StoreProxy,
      tasks: queue.TaskQueue,
      chat_model: string
    );
    // Loads the world document and the current scene's prompt.
    agent_open(): Promise<lines.DocRef>;
    turn_run(input: lines.AiSay | lines.AiClick): Promise<lines.TurnEnd>;
    // Replaces turns 1 to `through` of the scene with one summary turn.
    turns_compact(scene: lines.DocRef, through: number, summary: string): Promise<void>;
  }
}
