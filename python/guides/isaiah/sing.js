// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_sing` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_sing.js`: takes the intent `sing`, its value the
// song's title, and sings on night guard. Each herd, an entity of `calm` and
// `temper`, comes up by its `temper.song_calm` to at most its `calm.most`,
// and the singer keeps the song in `song`. It says the calm before and after
// and logs the beat `calmer`, or `steady` when the calm was at its most.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `calm` and `temper`.
// Writes `calm.level` and the singer's `song.title`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The calm of the herd, the entity of `calm` and `temper`, and its most.
const HERD_CALM =
  "SELECT calm.level AS level, calm.most AS most FROM calm" +
  " JOIN temper ON temper.entity = calm.entity ORDER BY calm.entity";

// The intent to sing, taken, or none and no work this step.
const intent = ecs.take("sing");
if (intent === null) {
  return;
}
if (intent.value === "") {
  throw new Error("Isaiah's drive takes the intent sing with a song's title.");
}

const before = lib.row_one(ecs.rows(HERD_CALM, []), "the herd's calm");
ecs.run([
  {
    sql:
      "UPDATE calm SET level = MIN(most, level + (SELECT temper.song_calm" +
      " FROM temper WHERE temper.entity = calm.entity))" +
      " WHERE entity IN (SELECT entity FROM temper)",
    params: [],
  },
  {
    sql:
      "INSERT INTO song (entity, title) VALUES (?, ?)" +
      " ON CONFLICT (entity) DO UPDATE SET title = excluded.title",
    params: [intent.entity, intent.value],
  },
]);
const after = lib.row_one(ecs.rows(HERD_CALM, []), "the herd's calm");

const start =
  `You ride the slow circle singing ${intent.value}, and the herd's calm`;
const most = `of ${lib.whole_text(after.most)}.`;
if (after.level === before.level) {
  ecs.say(`${start} holds at ${lib.whole_text(before.level)} ${most}`);
  ecs.log("sing", intent.value, "steady");
} else {
  ecs.say(
    `${start} comes up from ${lib.whole_text(before.level)} to` +
      ` ${lib.whole_text(after.level)} ${most}`,
  );
  ecs.log("sing", intent.value, "calmer");
}
