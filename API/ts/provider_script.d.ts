declare namespace provider_script {
  // A scripted provider for tests and transcripts: no network, no AI.
  // The latest user message is one integer that picks a reply from the
  // current node; a tool result moves to the node the reply names.

  interface ScriptReply {
    // What the assistant says; null when it only calls tools.
    content: string | null;
    tool_calls?: provider.ToolCall[];
    // The node to be in after this reply's tool results arrive.
    next: string;
  }

  interface ScriptNode {
    // Replies by the integer the user sent, as decimal strings.
    replies: { [input: string]: ScriptReply };
    // The reply after tool results, when the node was reached by tools.
    after_tools?: ScriptReply;
  }

  interface Script {
    start: string;
    nodes: { [node: string]: ScriptNode };
    // Every image request answers with this, a URL the UI can fetch.
    image: provider.ImageResponse;
  }

  class ScriptProvider implements provider.Provider {
    constructor(script: Script);
    chat_complete(request: provider.ChatRequest): Promise<provider.ChatResponse>;
    image_generate(request: provider.ImageRequest): Promise<provider.ImageResponse>;
    // The node the script is in, for assertions.
    node(): string;
  }
}
