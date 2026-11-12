// A scripted provider, which the tests and the engine page run: no network,
// no AI. A port that answers the `http.request` lines of provider.ts. The
// latest user message, its ends trimmed and its letters lowered, picks the
// reply its node's `replies` holds under that text: a number, a word or a
// phrase. Any other text gets the node's `otherwise`, a person's bad input
// being expected; with none it is refused, in a test's own table a bug of the
// test, as is a content that is not a string and a key no input can match. A
// tool result moves to the node the reply names, which answers with
// `after_tools`, or with `after_lacks` when it holds `after_holds` and a
// result lacks that text. A reply's `quote` is a path into the JSON of the
// last tool result, whose string it says before its `content`. Every image
// request gets the image of `image_pattern` as `b64_json`. Once it has chosen
// a reply it holds the request to what xAI expects, refusing the first bad
// field by `provider_script.field_invalid`. It keeps each response under its
// id, unless `store` is false, to check a request chained from it. Each reply
// holds a reasoning item, xAI's echoes of the request, and a `usage` of
// arithmetic on the context in characters. In debug mode, by its reader, it
// takes `provider.tools_omitted` for tools.

declare namespace provider_script {
  // A call of the script, which the reply sends as a `function_call` item.
  interface ScriptCall {
    call_id: string;
    name: string;
    arguments: string;
  }

  interface ScriptReply {
    // What the assistant says, null when it only calls tools or only quotes.
    content: string | null;
    // A path of members joined by `.` into the JSON of the last tool result.
    quote?: string;
    tool_calls?: ScriptCall[];
    // The node to be in after this reply's tool results arrive.
    next: string;
  }

  interface ScriptNode {
    // Replies by the text the user sent, its ends trimmed, in lower case.
    replies: { [input: string]: ScriptReply };
    // The reply to any other text the user sent.
    otherwise?: ScriptReply;
    // The reply after tool results, when the node was reached by tools.
    after_tools?: ScriptReply;
    // A text every tool result must hold for `after_tools` to follow.
    after_holds?: string;
    // The reply after tool results of which one lacks `after_holds`.
    after_lacks?: ScriptReply;
  }

  interface Script {
    start: string;
    nodes: { [node: string]: ScriptNode };
  }

  class ScriptPort implements queue.Port {
    constructor(script: Script, debug: () => boolean);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // A low resolution PNG test pattern with hard pixel edges, drawn here.
  function image_pattern(): Uint8Array;
}
