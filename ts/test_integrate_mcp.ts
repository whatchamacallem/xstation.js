// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the Model Context Protocol between a real `mcp.Client`
// and a real `mcp.Server` on real queues. The clients run on a queue of
// thread `ai`, in the mode of the setting `queue_synchronous`, in the tasks
// of the type prefix `mcp_case.`, each started by a request from `ui`, the
// test's end, and answered with what the clients read. The server, with the
// tools and results of the gold, runs on a second queue, of `server`, whose
// `mcp` handler is the test's function: it notifies a copy of each `mcp` line
// it gets, of type `mcp_seen.line`, which the clients' queue forwards to
// `ui`, then hands the line to the server. Each lane is a MessageChannel with
// a `queue.ThreadPort` at each end. A client whose owner is `ui` sends its
// lines to the test's end, which reads them and never answers. The cases, the
// gold of the block's id, are the handshake, the results read with and
// without the error flag, the name form of a call, a call routed by a set of
// clients to each prefix, and the tools of a set under their prefixes.

namespace test_integrate_mcp {
  // The threads, types, identities and gold names of the block.
  const constants = Object.freeze({
    gold_id: "typescript.test_integrate_mcp",
    thread: "ai" as const,
    far_thread: "server" as const,
    test_thread: "ui" as const,
    line_type: "mcp",
    case_prefix: "mcp_case.",
    seen_prefix: "mcp_seen.",
    seen_type: "mcp_seen.line",
    handshake_type: "mcp_case.handshake",
    results_type: "mcp_case.results",
    form_type: "mcp_case.form",
    routed_type: "mcp_case.routed",
    browser_type: "mcp_case.browser",
    prefixed_type: "mcp_case.prefixed",
    client_name: "hyperposition-engine",
    server_name: "xsjs-browser",
    version: "0",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
  });

  // A step of a case's task: the ids its next step sleeps on, or the reply.
  type StepFn = (
    request: lines.Line,
    replies: lines.Line[],
  ) => number[] | lines.Line;

  // The request a step's wake answers, which the sleep kept.
  interface WaitState {
    request: lines.Line;
  }

  // A copy of a value of the block's gold.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A line of the type in the name form the settings pick.
  function line_new(
    type: string,
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
  }

  // Registers a case's steps: the request's type, then each wake numbered.
  function chain_register(type: string, steps: readonly StepFn[]): void {
    for (const [index, step] of steps.entries()) {
      const name = index === 0 ? type : `${type}.${index}`;
      dispatch.handler_register(name, constants.handler_version, (line) => {
        const request = index === 0 ? line : (line.state as WaitState).request;
        const replies = index === 0 ? [] : (line.replies as lines.Line[]);
        const outcome = step(request, replies);
        if (!Array.isArray(outcome)) {
          return outcome;
        }
        const state: WaitState = { request };
        return dispatch.task_sleep(state, outcome, `${type}.${index + 1}`);
      });
    }
  }

  // A client of the clients' queue whose server the owner given reaches.
  function client_make(
    tasks: queue.TaskQueue,
    owner: queue.ThreadName,
  ): mcp.Client {
    return new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      owner,
    );
  }

  // The server with the tools of the gold, each returning its gold result.
  function server_make(): mcp.Server {
    const server = new mcp.Server(constants.server_name, constants.version);
    for (const tool of gold_value("tools") as mcp.Tool[]) {
      server.tool_register(
        tool,
        () => gold_value(`results.${tool.name}`) as mcp.ToolResult,
      );
    }
    return server;
  }

  // Registers the server queue's `mcp` handler: a copy, then the server.
  function server_register(far: queue.TaskQueue, server: mcp.Server): void {
    dispatch.handler_register(
      constants.line_type,
      constants.handler_version,
      (line) => {
        const payload = { header: line[0], message: jslb.payload_of(line) };
        far.line_notify(line_new(constants.seen_type, payload));
        return server.line_handle(line);
      },
    );
  }

  // Registers the tasks of the cases on the clients' queue.
  function cases_register(tasks: queue.TaskQueue): void {
    const near = constants.far_thread;
    const shake = client_make(tasks, near);
    chain_register(constants.handshake_type, [
      () => [shake.initialize_send()],
      (_request, [answer]) => {
        shake.initialized_send(answer);
        return [shake.tools_list()];
      },
      (request, [list]) =>
        dispatch.reply_make(request, { tools: shake.tools_read(list) }),
    ]);
    const reader = client_make(tasks, near);
    const read: mcp.ToolResult[] = [];
    chain_register(constants.results_type, [
      () => [reader.tool_call("source_put", {})],
      (_request, [reply]) => {
        read.push(reader.result_of(reply));
        return [reader.tool_call("render", {})];
      },
      (request, [reply]) => {
        read.push(reader.result_of(reply));
        return dispatch.reply_make(request, { results: read });
      },
    ]);
    const shown = client_make(tasks, constants.test_thread);
    chain_register(constants.form_type, [
      () => [
        shown.tool_call(
          "console_run",
          gold_value("arguments.console_run") as { [key: string]: unknown },
        ),
      ],
    ]);
    const set = new mcp.ClientSet();
    set.client_add("browser", client_make(tasks, constants.test_thread));
    set.client_add("server", client_make(tasks, near));
    const nothing = gold_value("arguments.kv_get") as {
      [key: string]: unknown;
    };
    chain_register(constants.routed_type, [
      () => [set.tool_call("server.kv_get", nothing)],
      (request, [reply]) =>
        dispatch.reply_make(request, { result: set.result_of(reply) }),
    ]);
    chain_register(constants.browser_type, [
      () => [set.tool_call("browser.kv_get", nothing)],
    ]);
    const listed = new mcp.ClientSet();
    const first = client_make(tasks, near);
    const second = client_make(tasks, near);
    listed.client_add("browser", first);
    listed.client_add("server", second);
    chain_register(constants.prefixed_type, [
      () => [first.tools_list(), second.tools_list()],
      (request, [first_list, second_list]) => {
        first.tools_read(first_list);
        second.tools_read(second_list);
        return dispatch.reply_make(request, { tools: listed.tools_cached() });
      },
    ]);
  }

  // The clients' queue and the server's, joined, and the test's end of `ui`.
  export function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners: queue.OwnerTable = {
      [constants.case_prefix]: constants.thread,
      [constants.seen_prefix]: constants.test_thread,
    };
    const far_owners: queue.OwnerTable = {
      [constants.line_type]: constants.far_thread,
      [constants.seen_prefix]: constants.thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const far = new queue.TaskQueue(
      constants.far_thread,
      far_owners,
      synchronous,
    );
    server_register(far, server_make());
    cases_register(tasks);
    const link = new MessageChannel();
    tasks.port_add(constants.far_thread, new queue.ThreadPort(link.port1));
    far.port_add(constants.thread, new queue.ThreadPort(link.port2));
    const lane = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(lane.port2));
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_mcp);
