// The turn as a chain of tasks on the AI thread. `ai.say` and `ai.click`
// store the conversation's system prompt when it holds none, append the
// player's turn, submit the model request and sleep with `ai.model_reply`.
// `ai.model_reply` submits each function call of a reply and sleeps with
// `ai.tool_reply`, storing nothing yet; `ai.tool_reply` stores that reply and
// its call outputs together in one transaction and submits the next model
// request. A reply with no calls is stored and ends the turn with `TurnEnd`.
// No stored call lacks its output. In debug mode the audit is the transcript
// of the turn. Nothing measures the databases: no request carries their
// sizes, and the loop reads no setting. A call's arguments are read by
// `jslb.json_decode`. The system prompt: the analyst's prompt document, then
// the prompt of the universe whose `universe` row names the current world,
// when one does; the triggers of API/sql/metaverse.sql refuse a second row
// naming one world with `agent.content_ambiguous`, in every store. A
// conversation gets its prompt once, before its first model call, as the
// first rows of its log. The loop keeps in memory, per scene, a chain: the id
// of the last response and the rows its context holds. A request whose log
// still begins with those rows sends the rows after them, chained by
// `previous_response_id`; any other starts a chain with the whole log: the
// first of a conversation, after a page load, and after a compaction.

declare namespace agent {
  // Registers the turn's handlers, the tools sent in debug mode the omission.
  function handlers_register(
    store: substrate.Store,
    clients: mcp.ClientSet,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    register: (type: string, version: number, fn: dispatch.Handler) => void,
    debug: () => boolean,
  ): void;

  function prompt_build(store: substrate.Store): provider.InputMessage[];
}
