// The turn as a chain of tasks on the AI thread. `ai.say` and `ai.click`
// append the player's turn, submit the provider request and sleep with
// `ai.model_reply`. `ai.model_reply` submits each tool call of a reply and
// sleeps with `ai.tool_reply`, storing nothing yet; `ai.tool_reply` stores
// that reply and its tool results together in one transaction and submits
// the next provider request. A reply with no tool calls is stored and ends
// the turn with `TurnEnd`. No stored call lacks its result. In debug mode
// the queue log is the transcript of the turn. Nothing measures the
// databases: no request carries their sizes, and the loop reads no setting.
// A tool call's arguments are read by `jslb.json_decode`.
//
// The system prompt: the analyst's prompt document, then the prompt of the
// universe whose `universe` row names the current world, when one does. Two
// rows cannot name one world: the triggers of API/sql/metaverse.sql refuse
// the second with `agent.content_ambiguous` before it is added, in every
// store and on every path a write takes.

declare namespace agent {
  function handlers_register(
    store: substrate.Store,
    clients: mcp.ClientSet,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    register: (type: string, version: number, fn: dispatch.Handler) => void,
  ): void;

  function prompt_build(store: substrate.Store): provider.ChatMessage[];
}
