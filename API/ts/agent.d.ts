declare namespace agent {
  // The turn as a chain of tasks on the AI thread. `ai.say` and
  // `ai.click` append the player's turn, submit the provider request and
  // sleep with `ai.model_reply`. `ai.model_reply` submits each tool call
  // of a reply and sleeps with `ai.tool_reply`, storing nothing yet;
  // `ai.tool_reply` stores that reply and its tool results together in
  // one transaction and submits the next provider request. A reply with
  // no tool calls is stored and ends the turn with `TurnEnd`. No stored
  // call lacks its result. In debug mode the queue log is the transcript
  // of the turn.
  function handlers_register(
    store: substrate.Store,
    clients: mcp.ClientSet,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
  ): void;

  // The system prompt: the analyst's prompt document, then the current
  // universe's prompt document when the scripts have made one.
  function prompt_build(store: substrate.Store): provider.ChatMessage[];
}
