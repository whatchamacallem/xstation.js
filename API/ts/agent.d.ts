declare namespace agent {
  // The turn as a chain of tasks on the AI thread. `ai.say` and
  // `ai.click` append the player's turn, submit the provider request and
  // sleep with `ai.model_reply`; `ai.model_reply` stores the assistant
  // turn, submits each tool call and sleeps with `ai.tool_reply`;
  // `ai.tool_reply` submits the next provider request or, when the
  // reply had no tool calls, ends the turn with `TurnEnd`. The queue
  // log is the transcript of the turn.
  function handlers_register(
    store: substrate.Store,
    clients: mcp.ClientSet,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo
  ): void;

  // The system prompt: the analyst's prompt document, then the current
  // universe's prompt document when the scripts have made one.
  function prompt_build(store: substrate.Store): provider.ChatMessage[];
}
