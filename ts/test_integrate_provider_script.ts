// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the scripted provider: chat and image requests through a
// real `provider_script.ScriptPort` that a real `queue.TaskQueue` on thread
// `ai` owns as `http`, the owner of the type prefix `http.`, walking the
// script of this block's gold under `script`. A queue sends a request to a
// port only from a handler's submit, so each case sends an `ask` line whose
// `request` is the `http.request` line, with no id: the handler of `ask`, this
// file's own function, submits it and sleeps on it, and the handler of the
// wake replies to the `ask` with the provider's reply line whole as its
// `answer`. The test's end is a real `queue.ThreadPort` over a MessageChannel
// whose other end the queue owns as thread `ui`. One port serves every case
// in order, so the script moves on from case to case as a turn does.

namespace test_integrate_provider_script {
  // The gold, the threads, the owned prefixes, the types and their version.
  const constants = Object.freeze({
    script_id: "typescript.test_integrate_provider_script.script",
    thread: "ai" as const,
    test_thread: "ui" as const,
    provider_thread: "http" as const,
    owner_prefix: "provider_script_test.",
    provider_prefix: "http.",
    ask_type: "provider_script_test.ask",
    answer_type: "provider_script_test.answer",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
  });

  // The payload of the wake of an `ask`: the `ask` and the provider's reply.
  interface AnswerWake {
    state: lines.Line;
    replies: lines.Line[];
  }

  // Registers the handlers of the queue, the test's own functions.
  function handlers_register(tasks: queue.TaskQueue): void {
    dispatch.handler_register(
      constants.ask_type,
      constants.handler_version,
      (line) => {
        const request = jslb.payload_of(line).request as lines.Line;
        const id = tasks.task_submit(request);
        return dispatch.task_sleep(line, [id], constants.answer_type);
      },
    );
    dispatch.handler_register(
      constants.answer_type,
      constants.handler_version,
      (line) => {
        const wake = jslb.payload_of(line) as unknown as AnswerWake;
        return dispatch.reply_make(wake.state, { answer: wake.replies[0] });
      },
    );
  }

  // A real queue that owns the scripted provider, and the test's end.
  export function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners = {
      [constants.owner_prefix]: constants.thread,
      [constants.provider_prefix]: constants.provider_thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const script = harness.gold_get(
      constants.script_id,
    ) as provider_script.Script;
    tasks.port_add(
      constants.provider_thread,
      new provider_script.ScriptPort(script),
    );
    handlers_register(tasks);
    const channel = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(channel.port2));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_provider_script);
