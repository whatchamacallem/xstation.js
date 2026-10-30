// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the browser's tool `console_run` past its permit, group C: the
// console shown first as ctrl 0 shows it, the command typed into tty 0 and
// its output read back until the prompt or the timeout, and the permits
// asked and allowed always. A server double, a store double and a queue
// double stand in for the server, the store and the queue, as no realm
// without ttyd has the console on tty 0, so this module runs only on the
// ttyd page. The lines the test sends and expects are the gold of
// test_settings.json. The provider key is set by provider.key_set.

namespace test_tools_browser_console {
  // Finishes a tool's result from the state and replies of its wake.
  type WakeFinish = (
    state: unknown,
    replies: lines.Line[],
  ) => mcp.ToolResult | dispatch.Sleep;

  // A line a tool sent: the line, its owner and, for a request, its id.
  interface SentLine {
    line: lines.Line;
    owner: queue.ThreadName | undefined;
    id: number | undefined;
  }

  // What a double gives for one call: the value the test chose, or a throw.
  type Answer = { value: unknown } | { error: Error };

  // One call a double was given: the method's name and its arguments.
  type Call = [string, unknown[]];

  // The doubles one test registers the tools on.
  interface ToolBench {
    store: StoreDouble;
    server: ServerDouble;
    tasks: TasksDouble;
  }

  // The names, texts and data the tests use.
  const constants = Object.freeze({
    // The id of this module's gold in `test_settings.json`.
    gold_id: "typescript.test_tools_browser_console",
    // The store's methods the tools and the script module call or bind.
    store_methods: Object.freeze<readonly string[]>([
      "sql_run",
      "db_list",
      "db_create",
      "db_drop",
      "kv_get",
      "kv_put",
      "kv_delete",
      "kv_list",
      "doc_get",
      "doc_put",
      "doc_head",
      "turn_append",
      "turn_list",
      "turn_compact",
      "transaction_run",
      "sink",
    ]),
    // A synthetic provider key, which every image request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // The owner the image requests go to.
    provider_owner: "http" as const,
    // The input message of ttyd's protocol that types `echo hi`.
    console_input: "0echo hi\n",
    // The result of `console_run` for the output of `echo hi`, trimmed.
    console_result: '{"output":"hi\\n","timed_out":false}',
  });

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A copy of a reply line of the gold, to the request of the id.
  function reply_gold(name: string, id: number): lines.Line {
    const line = gold_line(name);
    line[0].r = id;
    return line;
  }

  // The line of the gold that types a message into tty 0, its blob set.
  function input_line(typed: string): lines.Line {
    const data = new TextEncoder().encode(typed);
    const line = gold_line("console_input");
    line[1] = { size: data.length, d: data };
    return line;
  }

  // A settings reader: the test's own values for some ids, else the harness.
  function reader_make(values: {
    [id: string]: unknown;
  }): (id: string) => unknown {
    return (id: string) =>
      Object.hasOwn(values, id) ? values[id] : harness.setting_get(id);
  }

  // Keeps each call and gives the next answer the test added for its method.
  class CallDouble {
    // The calls, in order.
    readonly calls: Call[] = [];
    // The answers not yet given, by method.
    readonly #answers = new Map<string, Answer[]>();

    // Adds the answer of a later call of the method, after those added.
    answer_add(name: string, answer: Answer): void {
      const left = this.#answers.get(name);
      if (left === undefined) {
        this.#answers.set(name, [answer]);
      } else {
        left.push(answer);
      }
    }

    // Keeps the call and gives its answer, or throws when none is left.
    call_answer(name: string, values: unknown[]): unknown {
      this.calls.push([name, values]);
      const left = this.#answers.get(name);
      const answer = left === undefined ? undefined : left.shift();
      if (answer === undefined) {
        throw new Error(`the double has no answer for a call of ${name}`);
      }
      if ("error" in answer) {
        throw answer.error;
      }
      return answer.value;
    }
  }

  // A store double with every method the tools and the script module call.
  class StoreDouble extends CallDouble {
    // Makes each method of the store keep its call and give its answer.
    constructor() {
      super();
      const methods = this as unknown as { [name: string]: unknown };
      for (const name of constants.store_methods) {
        methods[name] = (...values: unknown[]): unknown =>
          this.call_answer(name, values);
      }
    }
  }

  // A server double that keeps the tools and the wakes registered on it.
  class ServerDouble {
    // The tools, in the order they were registered.
    readonly tools: mcp.Tool[] = [];
    // The function of each tool, by name.
    readonly runs = new Map<string, mcp.ToolFn>();
    // The function of each wake, by type.
    readonly wakes = new Map<string, WakeFinish>();

    // Keeps a tool and its function.
    tool_register(tool: mcp.Tool, fn: mcp.ToolFn): void {
      this.tools.push(tool);
      this.runs.set(tool.name, fn);
    }

    // Keeps a wake type and its function.
    wake_register(then_type: string, fn: WakeFinish): void {
      this.wakes.set(then_type, fn);
    }
  }

  // A queue double that keeps each line and gives the ids the test picked.
  class TasksDouble {
    // The lines sent, in order.
    readonly sent: SentLine[] = [];
    // The ids not yet given, in the order the requests get them.
    readonly #ids: number[];

    // Keeps the ids the test picked for the requests to come.
    constructor(ids: number[]) {
      this.#ids = [...ids];
    }

    // Keeps a request and gives it the next id, or throws when none is left.
    task_submit(line: lines.Line, owner?: queue.ThreadName): number {
      const id = this.#ids.shift();
      if (id === undefined) {
        throw new Error("the queue double has no id left for a request");
      }
      this.sent.push({ line, owner, id });
      return id;
    }

    // Keeps a notification.
    line_notify(line: lines.Line, owner?: queue.ThreadName): void {
      this.sent.push({ line, owner, id: undefined });
    }
  }

  // A tool test: the provider key set, the tools on new doubles.
  class ToolCase extends unittest.TestCase {
    // Sets the provider key, which the image requests carry.
    setUp(): void {
      provider.key_set(constants.key);
    }

    // The tools registered on new doubles, the queue giving the ids picked.
    bench_make(
      ids: number[],
      values: { [id: string]: unknown } = {},
    ): ToolBench {
      const store = new StoreDouble();
      const server = new ServerDouble();
      const tasks = new TasksDouble(ids);
      tools_browser.tools_register(
        server as unknown as mcp.Server,
        store as unknown as substrate.Store,
        tasks as unknown as queue.TaskQueue,
        constants.provider_owner,
        constants.info,
        reader_make(values),
      );
      return { store, server, tasks };
    }

    // Runs a tool by name on its arguments.
    tool_run(
      bench: ToolBench,
      name: string,
      args: { [key: string]: unknown },
    ): mcp.ToolResult | dispatch.Sleep {
      const fn = bench.server.runs.get(name) as mcp.ToolFn;
      return fn(args);
    }

    // Runs the wake a sleep names with the replies it waited for.
    wake_run(
      bench: ToolBench,
      sleep: dispatch.Sleep,
      replies: lines.Line[],
    ): mcp.ToolResult | dispatch.Sleep {
      const fn = bench.server.wakes.get(sleep.then_type) as WakeFinish;
      return fn(sleep.state, replies);
    }

    // The result a tool or a wake returned, which must be no sleep.
    result_of(value: mcp.ToolResult | dispatch.Sleep): mcp.ToolResult {
      this.assertTrue("content" in value, "a result was expected");
      return value as mcp.ToolResult;
    }

    // The text of a result that holds one text block and is no error.
    text_of(value: mcp.ToolResult | dispatch.Sleep): string {
      const result = this.result_of(value);
      this.assertFalse("isError" in result);
      this.assertEqual(result.content.length, 1);
      const block = result.content[0];
      this.assertEqual(block.type, "text");
      return (block as { type: "text"; text: string }).text;
    }

    // A sleep of the type, waiting on exactly the requests sent from `start`.
    sleep_check(
      bench: ToolBench,
      value: mcp.ToolResult | dispatch.Sleep,
      start: number,
      then_type: string,
    ): dispatch.Sleep {
      this.assertTrue("then_type" in value, "a sleep was expected");
      const sleep = value as dispatch.Sleep;
      this.assertEqual(sleep.then_type, then_type);
      const ids = bench.tasks.sent
        .slice(start)
        .filter((entry) => entry.id !== undefined)
        .map((entry) => entry.id);
      this.assertEqual(sleep.wait_ids, ids);
      return sleep;
    }
  }

  // The tool that runs a command line in the debug console.
  export class TestConsole extends ToolCase {
    // Runs the tool on a command and returns its sleep on the permit.
    permit_start(bench: ToolBench, text: string): dispatch.Sleep {
      const start = bench.tasks.sent.length;
      return this.sleep_check(
        bench,
        this.tool_run(bench, "console_run", { text, timeout_seconds: 5 }),
        start,
        "tools.permit_reply",
      );
    }

    // The permit's reply of the gold, to the last request sent.
    choice_make(bench: ToolBench, name: string): lines.Line {
      const ask = bench.tasks.sent[bench.tasks.sent.length - 1];
      const reply = reply_gold(name, ask.id as number);
      reply.permit = ask.line.permit;
      return reply;
    }

    // The sleep on the `console.show` sent at `start`, then on the read.
    show_answer(
      bench: ToolBench,
      value: mcp.ToolResult | dispatch.Sleep,
      start: number,
    ): dispatch.Sleep {
      const wake = "tools.show_reply";
      const showing = this.sleep_check(bench, value, start, wake);
      const show = bench.tasks.sent[start];
      this.assertEqual(show.owner, "ui");
      this.assertEqual(show.line, gold_line("console_show"));
      const shown = reply_gold("show_reply", show.id as number);
      return this.sleep_check(
        bench,
        this.wake_run(bench, showing, [shown]),
        start + 1,
        "tools.console_reply",
      );
    }

    // A command asks, shows the console, runs and returns its output trimmed.
    test_console_recorded(): void {
      const bench = this.bench_make([41, 42, 43]);
      const asked = this.permit_start(bench, "echo hi");
      const ask = bench.tasks.sent[0];
      this.assertEqual(ask.owner, "ui");
      this.assertEqual(ask.line, gold_line("permit_ask"));
      const accepted = this.choice_make(bench, "permit_accept");
      const reading = this.show_answer(
        bench,
        this.wake_run(bench, asked, [accepted]),
        1,
      );
      const [input, read] = bench.tasks.sent.slice(2);
      this.assertEqual(input.owner, "console");
      this.assertEqual(input.id, undefined);
      this.assertEqual(input.line, input_line(constants.console_input));
      this.assertEqual(read.owner, "console");
      this.assertEqual(read.line, gold_line("console_read"));
      const output = reply_gold("read_reply", read.id as number);
      const result = this.wake_run(bench, reading, [output]);
      this.assertEqual(this.text_of(result), constants.console_result);
    }

    // Always Allow shows and runs this command and every later one, no ask.
    test_permit_always(): void {
      const bench = this.bench_make([45, 46, 47, 48, 49]);
      const asked = this.permit_start(bench, "echo hi");
      const always = this.choice_make(bench, "permit_always");
      this.show_answer(bench, this.wake_run(bench, asked, [always]), 1);
      this.show_answer(
        bench,
        this.tool_run(bench, "console_run", {
          text: "pwd",
          timeout_seconds: 5,
        }),
        4,
      );
      const later = bench.tasks.sent.slice(4).map((entry) => entry.line);
      this.assertEqual(later, [
        gold_line("console_show"),
        input_line("0pwd\n"),
        gold_line("console_read"),
      ]);
    }

    // Each permit asked has the next number, and Accept lasts one command.
    test_permits_counted(): void {
      const bench = this.bench_make([51, 52, 53, 54, 55, 56]);
      for (const number of [1, 2]) {
        const start = bench.tasks.sent.length;
        const asked = this.permit_start(bench, `echo ${number}`);
        const ask = bench.tasks.sent[start];
        this.assertEqual(ask.line.permit, number);
        this.show_answer(
          bench,
          this.wake_run(bench, asked, [
            this.choice_make(bench, "permit_accept"),
          ]),
          start + 1,
        );
      }
    }

    // A read that timed out keeps the output after the echo, with no prompt.
    test_console_expired(): void {
      const bench = this.bench_make([57, 58, 59]);
      const asked = this.permit_start(bench, "sleep 600");
      const accepted = this.choice_make(bench, "permit_accept");
      const reading = this.show_answer(
        bench,
        this.wake_run(bench, asked, [accepted]),
        1,
      );
      const read = bench.tasks.sent[3];
      const output = reply_gold("read_reply_expired", read.id as number);
      const result = this.wake_run(bench, reading, [output]);
      this.assertEqual(this.text_of(result), gold_value("result_expired"));
    }
  }
}

Object.freeze(test_tools_browser_console);
