// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_stampede` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_stampede.js`: takes the intent `stampede`, its value
// the flank the player rides for, `east` or `west`. Every bunch of `share`
// runs off with its share of the herd: it gains `head` and the tag `hidden`,
// and the herd, the entity of `temper`, loses their sum and mills down to
// its `temper.milled` calm. East bends the run short of the breaks, and west
// lets it on into them, where the herd of `breaks` loses `breaks.loss` more.
// It says the count at sunrise and the rider's `looks.most`, and logs the
// beat `circled` or `broken`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `share`, `temper`,
// `breaks` and `looks`. Writes `head`, `hidden`, `calm.level` and
// `losses.lost`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to ride for a flank, taken, or none and no work this step.
const intent = ecs.take("stampede");
if (intent === null) {
  return;
}
const flank = lib.choice_read(intent.value, ["east", "west"]);

// The bunches scatter and the herd mills, whichever flank is ridden.
const statements = [
  {
    sql:
      "INSERT INTO head (entity, count) SELECT share.entity, share.head" +
      " FROM share ORDER BY share.entity",
    params: [],
  },
  {
    sql:
      "INSERT INTO hidden (entity) SELECT share.entity FROM share" +
      " ORDER BY share.entity",
    params: [],
  },
  {
    sql:
      "UPDATE head SET count = count - (SELECT SUM(share.head) FROM share)" +
      " WHERE entity IN (SELECT entity FROM temper)",
    params: [],
  },
  {
    sql:
      "UPDATE calm SET level = (SELECT temper.milled FROM temper" +
      " WHERE temper.entity = calm.entity)" +
      " WHERE entity IN (SELECT entity FROM temper)",
    params: [],
  },
];
// The run that goes on east reaches the breaks.
if (flank === "west") {
  statements.push(
    {
      sql:
        "UPDATE head SET count = count - (SELECT breaks.loss FROM breaks" +
        " WHERE breaks.entity = head.entity)" +
        " WHERE entity IN (SELECT entity FROM breaks)",
      params: [],
    },
    {
      sql:
        "UPDATE losses SET lost = lost + (SELECT breaks.loss FROM breaks" +
        " WHERE breaks.entity = losses.entity)" +
        " WHERE entity IN (SELECT entity FROM breaks)",
      params: [],
    },
  );
}
ecs.run(statements);

const herd = lib.row_one(
  ecs.rows(
    "SELECT head.count AS count, breaks.loss AS loss FROM head" +
      " JOIN temper ON temper.entity = head.entity" +
      " JOIN breaks ON breaks.entity = head.entity ORDER BY head.entity",
    [],
  ),
  "the herd's head",
);
const out = ecs.rows(
  "SELECT head.count AS count FROM head" +
    " JOIN hidden ON hidden.entity = head.entity ORDER BY head.entity",
  [],
);
const scattered = out.reduce((sum, bunch) => sum + bunch.count, 0);
const looks = lib.row_one(
  ecs.rows("SELECT most FROM looks WHERE entity = ?", [intent.entity]),
  "the rider's looks",
);

const tail =
  `${lib.whole_text(scattered)} head scattered, and` +
  ` ${lib.whole_text(looks.most)} looks before noon to find them.`;
if (flank === "east") {
  ecs.say(
    "You ride for the leaders on the east flank and bend the run west" +
      " into a circle, short of the breaks. At sunrise the count is" +
      ` ${lib.whole_text(herd.count)}: ${tail}`,
  );
  ecs.log("stampede", flank, "circled");
} else {
  ecs.say(
    "You ride for the leaders on the west flank, and the run goes on east" +
      " into the breaks. At sunrise the count is" +
      ` ${lib.whole_text(herd.count)}: ${lib.whole_text(herd.loss)} head` +
      ` lost in the breaks, ${tail}`,
  );
  ecs.log("stampede", flank, "broken");
}
