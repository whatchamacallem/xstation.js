// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the scripted provider: model and image requests through a
// real `provider_script.ScriptPort` that a real `queue.TaskQueue` on thread
// `ai` owns as `http`, the owner of `http.`, walking the script of this
// block's gold under `script`, whose calls are in the form `ScriptCall`. A
// queue sends to a port only from a handler's submit, so each case sends an
// `ask` line whose `request` is the `http.request` line, with no id: the
// handler of `ask` submits it and sleeps on it, and the handler of the wake
// replies with the provider's reply line as its `answer`. No gold can hold
// the digest of the fake's ids, so the gold writes it as sixteen zeros: `ask`
// fills a `previous_response_id` of `resp_` and zeros with the id of the last
// model answer, and the wake checks that a model answer's ids carry one
// digest and its echo that id, then writes them with zeros, throwing
// otherwise. The test's end is a real `queue.ThreadPort` over a MessageChannel
// whose other end the queue owns as thread `ui`. One port serves every case in
// order, so the chain and the script move on from case to case as a turn does.

namespace test_integrate_provider_script {
  // The gold, the threads, the owned prefixes, the types, the ids' digest.
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
    // The digest a gold writes in place of the fake's.
    zero_digest: "0000000000000000",
    response_prefix: "resp_",
    // A response id and the digest it carries, 16 hexadecimal digits.
    response_form: /^resp_([0-9a-f]{16})$/,
    // The prefix of an output item's id by the item's type.
    item_prefixes: Object.freeze({
      reasoning: "rs_",
      message: "msg_",
      function_call: "fc_",
    }),
    call_type: "function_call",
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // The payload of the wake of an `ask`: the `ask` and the provider's reply.
  interface AnswerWake {
    state: lines.Line;
    replies: lines.Line[];
  }

  // The id of the last model answer, as the fake wrote it.
  interface ChainHeld {
    last: string | undefined;
  }

  // Sets a `previous_response_id` of zeros to the id of the last answer.
  function previous_fill(body: FieldTable, chain: ChainHeld): void {
    const zeros = `${constants.response_prefix}${constants.zero_digest}`;
    if (body.previous_response_id !== zeros) {
      return;
    }
    if (chain.last === undefined) {
      throw new Error("No model answer came before the chained request.");
    }
    body.previous_response_id = chain.last;
  }

  // Checks that an answer's ids carry one digest, keeps its id, writes zeros.
  function ids_zero(body: FieldTable, chain: ChainHeld): void {
    const id = body.id as string;
    const found = constants.response_form.exec(id);
    if (found === null) {
      throw new Error(`The response id ${id} carries no digest.`);
    }
    const digest = found[1];
    const previous = body.previous_response_id;
    if (previous !== null && previous !== chain.last) {
      throw new Error(`The echo ${String(previous)} is not the id chained.`);
    }
    const prefixes: { [type: string]: string } = constants.item_prefixes;
    let calls = 0;
    for (const item of body.output as FieldTable[]) {
      const type = item.type as string;
      if (!Object.hasOwn(prefixes, type)) {
        throw new Error(`The output item of type ${type} has no id form.`);
      }
      if (type === constants.call_type) {
        calls += 1;
      }
      const suffix = type === constants.call_type ? `_${calls}` : "";
      const prefix = prefixes[type];
      if (item.id !== `${prefix}${digest}${suffix}`) {
        throw new Error(`The item id ${String(item.id)} is not of ${id}.`);
      }
      item.id = `${prefix}${constants.zero_digest}${suffix}`;
    }
    chain.last = id;
    body.id = `${constants.response_prefix}${constants.zero_digest}`;
    if (previous !== null) {
      body.previous_response_id = body.id;
    }
  }

  // Registers the handlers of the queue, the test's own functions.
  function handlers_register(tasks: queue.TaskQueue): void {
    const chain: ChainHeld = { last: undefined };
    dispatch.handler_register(
      constants.ask_type,
      constants.handler_version,
      (line) => {
        const request = jslb.payload_of(line).request as lines.Line;
        previous_fill(request.json as FieldTable, chain);
        const id = tasks.task_submit(request);
        return dispatch.task_sleep(line, [id], constants.answer_type);
      },
    );
    dispatch.handler_register(
      constants.answer_type,
      constants.handler_version,
      (line) => {
        const wake = jslb.payload_of(line) as unknown as AnswerWake;
        const answer = wake.replies[0];
        const body = answer.json as FieldTable;
        if (Object.hasOwn(body, "output")) {
          ids_zero(body, chain);
        }
        return dispatch.reply_make(wake.state, { answer });
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
      new provider_script.ScriptPort(script, switches.debug_on),
    );
    handlers_register(tasks);
    const channel = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(channel.port2));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_provider_script);
