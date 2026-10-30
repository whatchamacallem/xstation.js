// A scripted provider for tests: no network, no AI. A port that answers the
// `http.request` lines of provider.ts. The latest user message is one
// integer that picks a reply from the current node; a tool result moves to
// the node the reply names. Every image request is answered with the image
// of `image_pattern` as `b64_json`.

declare namespace provider_script {
  interface ScriptReply {
    // What the assistant says, null when it only calls tools.
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
  }

  class ScriptPort implements queue.Port {
    constructor(script: Script);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // A low resolution PNG test pattern with hard pixel edges, drawn here.
  function image_pattern(): Uint8Array;
}
