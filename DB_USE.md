# DB_USE.md: the guides run their sims through the databases

A plan, written 2026-11-12 in the session of tmp/tasks_12_0737.md. Nothing
of it is built yet.

## 1 The request

1.1 The user's text, literal:

> read @build/audit/*db and make a plan DB_USE.md to have the fake guide use
> the DBs to operate a simulation of the experiance on the fake users behalf.
> the guide should send over scripts and run them to step a sim using SQL and
> the entity-component-system pattern together. have DB_USE.md describe
> confirming a certain simulator output was repeated to the player by the
> guide at the end of the conversation/run. if agents would help, add a
> schedule.

1.2 Its parts, as this plan answers them:

1.2.1 The fake guide, the scripted provider's table of each guide test,
      operates a sim of the experience through the databases. It does so on
      the fake player's behalf: the player only talks, and the guide writes
      the player's choice into the world database and steps the sim.
1.2.2 The guide sends scripts over, by browser_kv_put of each script's text
      to `/_files/script/<name>.js`, and runs them, by browser_script_run.
1.2.3 The scripts step the sim with SQL and the entity-component-system
      pattern together: entities and components are rows of tables, systems
      are scripts whose work is SQL over those tables, and a step runs the
      systems in a fixed order, tick by tick.
1.2.4 A run confirms that one chosen output of the sim was repeated to the
      player by the guide at the end of the conversation, section 4.
1.2.5 Agents help, as three guides can be rebuilt at once, so section 7 is
      a schedule.

1.3 Read for this plan: build/audit/isaiah_db.txt, ruth_db.txt and
    dawa_db.txt, as no file of build/audit/ ends in `db`; the engineering
    logs tmp/tasks_11_1956.md and tmp/tasks_12_0354.md; the project's
    Guides, Tools, Store and audit_read rules; guides.md; python/guides/;
    python/guide_walk.py; ts/script.ts, ts/substrate.ts and
    ts/tools_browser.ts.

## 2 What the databases show today

2.1 Each guide's world database holds its sim as one state row, a log of
    beats and a keepsake table:

2.1.1 Isaiah's `drive`: `herd`, one row ending `1, 1980, 0, 0, 20, 3, 3, 40,
      1, 1, 'Streets of Laredo'`; `drive_log`, 13 rows from `sing` to
      `count`; `keepsake`, the trail name.
2.1.2 Ruth's `summer`: `jenny`, one row ending `1, 'Sam', 0, 0, 1, 7185`,
      her purse 7185 cents; `flight`, 16 rows from `climb` to `landing`;
      `keepsake`, the handbill.
2.1.3 Dawa's `expedition`: `climber`, one row ending at Camp 4 with
      `high_m` 8749 and record `kept`; `climb_log`, 12 rows; `keepsake`,
      the photograph and the scarf.

2.2 Each guide sends one script, `/_files/script/NAME.js`, of 14463 bytes
    for Isaiah, 21752 for Ruth and 23502 for Dawa in `_files`, and calls it
    once per beat with `{action,
    ...}`. An action reads the one row, works the beat out by a formula,
    writes the row and a log row, and returns `{say, outcome}`. No entity,
    component or step in time exists: a day on Isaiah's trail, a second of
    Ruth's race and a minute of Dawa's descent are each one multiplication.

2.3 Facts of the code this design rests on, each read in the tree:

2.3.1 A script runs as `new Function("engine", "args", text)`, and `engine`
      holds the store's routine methods and i18n. No method runs another
      script, but a script may read another's text by `store.kv_get` and
      compile it the same way.
2.3.2 `store.transaction_run` spans every database a call touches, so one
      step may read `_files` and write the world database atomically.
2.3.3 The browser's `sql_run` sends the server one `sql.run` push, holding
      every statement of the call with its bound values, only when it
      changed a row or the schema. A call of SELECTs alone sends nothing.
2.3.4 The server runs each pushed statement again on its own copy, and
      audit_read.databases_check runs them a third time on a scratch copy.
      The browser's SQLite is 3.46.1 (third_party/sqlite-wasm-3460100.zip)
      and Python's is 3.46.1; both stores turn foreign keys on.
2.3.5 A scripted reply may hold several tool calls, which all run in order
      before the next model call. Its quote reads one path of members
      through objects of the last call's output only, so it cannot index
      the arrays of a sql_run result.
2.3.6 The digest shows every statement of every sql.run commit with its
      params, and the end to end level of `./test_posix.sh` is exactly the
      three guide tests.

## 3 Design

### 3.1 Terms

3.1.1 Entity: one row of `entity`, an id and a unique name, nothing more.
3.1.2 Component: a table keyed by `entity`, plain data, no behaviour. An
      entity holds the component when the table holds its row. A tag is a
      component of no column but `entity`.
3.1.3 System: a script that finds the entities holding a set of components,
      by SQL joins or correlated subqueries, and changes those components by
      set-based SQL. A step system runs once per step; a tick system runs
      once per tick.
3.1.4 Step: one run of `ecs_step` for one decision of the player: the step
      systems once, then ticks while any entity is busy.
3.1.5 Tick: one unit of the sim's time, fixed per guide in its clock: a day
      for Isaiah, 20 seconds for Ruth, 30 minutes for Dawa.
3.1.6 Intent: the player's choice, a component of the player entity that
      the guide writes by SQL and one step system consumes.
3.1.7 Output: one fragment of what a step says, in order; the step's say is
      its outputs joined by single spaces.

### 3.2 The core tables

3.2.1 Every guide's world database gains these tables, made by the core
      script `ecs_init`:

```sql
CREATE TABLE entity (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)
  STRICT
CREATE TABLE system (ord INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('lib', 'step', 'tick'))) STRICT
CREATE TABLE clock (entity INTEGER PRIMARY KEY REFERENCES entity (id)
  ON DELETE CASCADE, step INTEGER NOT NULL, tick INTEGER NOT NULL,
  tick_seconds INTEGER NOT NULL, ticks_max INTEGER NOT NULL) STRICT
CREATE TABLE intent (entity INTEGER PRIMARY KEY REFERENCES entity (id)
  ON DELETE CASCADE, verb TEXT NOT NULL, value TEXT NOT NULL) STRICT
CREATE TABLE busy (entity INTEGER PRIMARY KEY REFERENCES entity (id)
  ON DELETE CASCADE) STRICT
CREATE TABLE output (n INTEGER PRIMARY KEY, step INTEGER NOT NULL,
  tick INTEGER NOT NULL, system TEXT NOT NULL, text TEXT NOT NULL) STRICT
CREATE TABLE beat_log (n INTEGER PRIMARY KEY, step INTEGER NOT NULL,
  tick INTEGER NOT NULL, beat TEXT NOT NULL, choice TEXT NOT NULL,
  outcome TEXT NOT NULL) STRICT
```

3.2.2 `system` is the schedule: the scripts the step runs, in `ord`. Exactly
      one row is of kind `lib`, the guide's library of number formats and
      units, run once per step before the systems.
3.2.3 `clock` is a component of the entity `world` alone: the steps taken,
      the ticks run, the seconds a tick stands for, and `ticks_max`, the
      most ticks one step may run before it fails as a broken table.
3.2.4 `beat_log` replaces `drive_log`, `flight` and `climb_log`, with the
      step and tick added. `output` holds every fragment ever said, so the
      database keeps what the sim told the player and when.

### 3.3 The core scripts

3.3.1 `ecs_init`, from python/guides/ecs/init.js, args `{world}`: runs the
      DDL of 3.2.1 on the world database in one sql_run and returns
      `{value: {world}}`.
3.3.2 `ecs_step`, from python/guides/ecs/step.js, args `{world}`. Inside one
      `store.transaction_run`:
      3.3.2.1 reads the one row of `clock`, and the step becomes its step
              plus 1;
      3.3.2.2 reads `system` in `ord`, reads each script's text by
              `store.kv_get` and compiles it once by `new Function("engine",
              "args", text)`; a value that is no byte array, as a script
              over overflow_bytes comes back as a cache handle, throws
              naming the script;
      3.3.2.3 runs the `lib` script with `{}`, its value the guide's
              library;
      3.3.2.4 runs each step system once, in order, with `{ecs}` of 3.4.1;
      3.3.2.5 throws when an intent is left, naming its verb, as no system
              took it;
      3.3.2.6 while `busy` holds a row, runs a tick: the tick plus 1, then
              each tick system in order; a step that reaches `ticks_max`
              ticks with an entity still busy throws;
      3.3.2.7 writes the step and tick to `clock` in one statement;
      3.3.2.8 reads this step's outputs in `n` and its `beat_log` rows,
              throws unless there is at least one output and exactly one
              log row, and returns `{say, outcome}`: the outputs joined by
              single spaces, and the log row's outcome.
3.3.3 The value keeps the form of today's sims, `{"value":{"say":...,
      "outcome":...}}` in that key order, so the tables' quote `value.say`
      and `after_holds` of `"outcome":"WORD"` work unchanged.

### 3.4 The system contract

3.4.1 Each system gets `args.ecs`, a frozen object the step makes:
      `world`, `step`, `tick`, `system`, its own name, and `lib`; `rows(sql,
      params)`, the rows of a SELECT on the world as objects; `run(statements)`,
      a sql_run on the world; `id(name)`, an entity's id, throwing when it
      is absent; `take(verb)`, the intent of that verb as `{entity, name,
      value}`, deleted, or null when no intent of that verb waits, which
      means that system has no work this step; `say(text)`, one output row;
      `log(beat, choice, outcome)`, one beat_log row.
3.4.2 A system returns nothing, keeps nothing between runs and finds its
      entities by their components alone, never by a list in its code.
3.4.3 A step system takes at most one verb's intent. A choice that fails is
      an outcome with its own say, never a throw; a throw is a broken table,
      an unknown verb or a value of the wrong form, as today.
3.4.4 A tick system that moves an entity to its end deletes the entity's
      `busy` row; one that starts nothing adds none.

### 3.5 SQL that the server repeats exactly

3.5.1 Every value SQL computes is an integer or text: integer arithmetic,
      comparison, MIN, MAX, printf of integers. Floating point is worked in
      JavaScript alone and bound as a parameter, so that the server and the
      replay, which repeat the statements and not the script, store the same
      value. No statement calls a math function, random() or a time
      function.
3.5.2 An UPDATE takes its values from correlated subqueries keyed by
      `entity`, or from an UPDATE ... FROM whose join matches at most one
      row per target row, as SQLite picks an arbitrary row of several.
3.5.3 An INSERT ... SELECT of several rows orders them by a key, so that
      the rowids assigned agree.
3.5.4 Components reference `entity (id) ON DELETE CASCADE`, which both
      stores enforce alike.
3.5.5 Every table is STRICT with columns INTEGER or TEXT and NOT NULL, by
      the existing rule `guide sim tables`.
3.5.6 A system does its writes of one tick in as few sql_run calls as it
      can, as each call that changes something is one push and one record.

3.6 An example, Isaiah's tick system `isaiah_travel`, which moves every
    entity under way toward its goal and ends its travel there:

```sql
UPDATE place SET mile = MIN(
    mile + (SELECT miles FROM pace WHERE pace.entity = place.entity),
    (SELECT goal.mile FROM travel JOIN place AS goal
       ON goal.entity = travel.goal WHERE travel.entity = place.entity))
  WHERE entity IN (SELECT entity FROM travel)
DELETE FROM busy WHERE entity IN (SELECT travel.entity FROM travel
  JOIN place ON place.entity = travel.entity
  JOIN place AS goal ON goal.entity = travel.goal
  WHERE place.mile = goal.mile)
DELETE FROM travel WHERE entity NOT IN (SELECT entity FROM busy)
```

### 3.7 A guide's scripts

3.7.1 Each guide directory holds, in place of sim.js: `lib.js`, the
      number formats and the units of today's sim; `spawn.js`; `report.js`;
      and one file per system, named by the system. The key of each is
      `/_files/script/NAME_STEM.js`, as `isaiah_travel` for
      python/guides/isaiah/travel.js. The core scripts keep the keys
      `ecs_init` and `ecs_step` in every guide.
3.7.2 `NAME_spawn`, args `{world}` and the guide's own, as Ruth's partner:
      makes every entity, every component row and the clock, from the
      constants of today's sim, each with the one line comment naming its
      source that it holds today, and returns today's setup say and
      outcome `ready`. Each constant of the guide's world, game rules and
      the aircraft's book figures included, becomes a component value, so
      the database holds the whole model. Published formulas, their
      coefficients and the units, West's formula, standard gravity, feet a
      mile, stay in `lib.js` with their sources. A figure that is no whole
      number is kept as an integer of a stated scale, as `glide_ratio_x100`
      1066, and divided by its power of ten in JavaScript, which gives the
      same double as today's literal, both being the correctly rounded
      value of the same decimal.
3.7.3 `NAME_report`, args `{world}`: reads the guide's chosen output and
      what frames it from the components by SELECTs alone, so it commits
      nothing, and returns `{say, outcome: "told"}`. The guide runs it once,
      at the end, section 3.8.6.

### 3.8 The table's turns

3.8.1 The build turn, the reply to `let's ride out`, `let's go` or `ready`,
      calls in order: browser_kv_put of each script, core and guide; then
      browser_script_run of `ecs_init`; then browser_sql_run of the guide's
      component DDL and the INSERTs of `system`, the schedule written by
      the guide in SQL; then browser_script_run of `NAME_spawn`. The node
      after it quotes `value.say` and asks the first beat, as `built` does
      today.
3.8.2 A beat's reply makes two calls: browser_sql_run of the player's
      intent, written by the guide on the player's behalf,

```sql
INSERT INTO intent (entity, verb, value)
  SELECT id, ?, ? FROM entity WHERE name = ?
```

with params `[VERB, VALUE, "player"]`, then browser_script_run of
`{"name": "ecs_step", "args": {"world": WORLD}}`. The quote reads the step's
value, the last call's output. Call ids are `call_` and the verb for the
intent, as `call_track`, and `call_step` for the step.
3.8.3 The exit and its resume each make the same two calls, of the verbs
      `exit` and `resume`, so the table source's exit holds lists, `calls`
      and `resume_calls`, in place of `call` and `resume_call`. Call ids:
      `call_exit` and `call_exit_step`, `call_resume` and
      `call_resume_step`.
3.8.4 The keepsake turn writes the intent `keepsake` and steps. Ruth's and
      Dawa's still make their picture first, as today.
3.8.5 Every band of today's walks stays byte for byte: each step's say is
      today's text, now joined from the outputs of the systems that ran. A
      band is the oracle that the sim's arithmetic is unchanged, and the
      golds keep it.
3.8.6 Each walk gains one last step, the end of the conversation: the
      player says goodbye, `So long`, `So long, Ruth` or `Goodbye, Dawa`,
      a reply key of the node `end`; its one call is browser_script_run of
      `NAME_report`; its after node quotes `value.say` with the guide's
      farewell as content, and goes back to `end`. Its band is worked by
      hand from numbers that earlier bands already show.
3.8.7 The rule `guide no number by hand` holds: the table states no number
      of a model, as every number of a say comes from a script. The
      intent's value is the player's own input.

### 3.9 The three sims

3.9.1 Isaiah's drive, world `drive`, a tick of one day, 86400 seconds.
      3.9.1.1 Entities: world, herd, ridge, creek, draw, player, isaiah,
              cimarron, outfit, dodge.
      3.9.1.2 Components: `head (count)` of the herd and each bunch;
              `calm (level, most)` and `temper (song_calm, settled,
              milled)` of the herd; `share (head)` and `cover (name,
              opening)` of each bunch, the 12, 25 and 3 of today; the tag
              `hidden` of a bunch not yet found; `place (mile)` of the herd
              0, cimarron and dodge 100; `pace (miles)` of the herd 10;
              `travel (goal)` of an entity under way; `water (high,
              per_drowned)` of the river; `wait (days)` of the herd while
              it holds on the bank; `toll (floor)`
              of the outfit; `wage (cents_a_day, earned)`, `looks (used,
              most)`, `song (title)` and `exits (count)` of the player;
              `losses (lost, tolled, found)` and `tally (head, tick)` of the
              herd; `keepsake (kind, text)` of an item entity.
      3.9.1.3 Step systems by verb: sing, exit, resume, read, stampede,
              track, river, toll, count, keepsake. Tick systems: travel;
              hold, which counts the herd's day of waiting and lowers the
              water at its end; and wage.
      3.9.1.4 Ticks of the walk: when tracking is done the herd travels to
              the Cimarron; the day waited is one tick; once the toll is
              paid the herd travels to Dodge City. The count reads 11 days
              from the clock and $11.00 from the wage earned, measured by
              stepping where today they are `100 / 10 + waited`.
      3.9.1.5 One new constant: `RIVER_MILE`, the Cimarron's mile, a game
              rule, 60. No band shows it, and any multiple of 10 under 100
              gives the same bands, 6 ticks before the river and 4 after.
      3.9.1.6 The chosen output: the herd's `tally.head`, 1980, first said
              at the toll, `1980 head cross the ford`.
3.9.2 Ruth's summer, world `summer`, a tick of 20 seconds.
      3.9.2.1 Entities: world, jenny, ruth, partner, motorcar, wind, north,
              south.
      3.9.2.2 Components: `airframe` of the jenny, the JN-4D book figures
              of today's constants, wing area and glide ratio scaled by 100;
              `altitude (ft)` and `resume (ft)` of the jenny; `technique
              (loop_pull_g, loop_top_g_x10, roll_seconds)` and `purse
              (cents)` of ruth; `fares (ride_cents, ride_min,
              gas_cents_gal)`; `name (text)` and `exits (count)` of the
              partner; `wind (mph, from)` of the wind; `field (miles_x10,
              name)` of each field; `racer (ground_mph, feet, start_tick,
              finish_tick)` of the jenny and the motorcar while they race,
              and `course (feet)` of the race, 26400.
      3.9.2.3 Step systems by verb: climb, exit, resume, turn, loop, roll,
              buzz, rides, race, wing_walk, field, landing, keepsake, each
              working today's formula in JavaScript from the components.
              Tick systems: drive, which moves each racer its ground speed
              times 20 seconds in whole feet and finishes it at the course's
              end, then finish, which pays the purse and says the result
              once both racers are done.
      3.9.2.4 Ticks of the walk: the race alone. At full throttle the jenny
              makes 60 mph over the road, 1760 feet a tick, done in 15
              ticks, 5:00; the motorcar 45 mph, 1320 feet, 20 ticks, 6:40;
              the margin 1:40. The cruise's 45 over the road is also 1320,
              a dead heat. A ground speed that moves no whole number of feet
              a tick throws, as the throttles of the table never give one.
      3.9.2.5 The chosen output: ruth's `purse.cents`, 7185, said
              `$71.85`, first at the race.
3.9.3 Dawa's climb, world `expedition`, a tick of 30 minutes.
      3.9.3.1 Entities: world, player, dawa, teo, the camps base_camp,
              camp_1, camp_2, camp_3, camp_4, south_summit and summit, the
              bottles player_bottle, teo_bottle and spare, and the forecasts
              of 1 and 3 days ahead.
      3.9.3.2 Components: `camp (name, altitude_m, ord)` of each camp; `at
              (camp)` of each climber; `climb (to_camp, ticks_left,
              start_minute)` of a climber under way; `ams (grade, hidden)`,
              `rest (days)`, `load (kg)`, `high (m)`, `exits (count)` and
              `resume (camp)` of the player; `limits (load_kg, wind_kmh)`
              and `record (text)` of dawa; `bottle (full_l, left_l, holder)`
              of each bottle; `breathe (lpm, bottle)` of a climber on
              oxygen; `forecast (days_ahead, kmh)`; `sun (loosen_hour)` and
              `icefall (hours)` of the world.
      3.9.3.3 Step systems by verb: icefall, morning, exit, resume, window,
              loads, push, decide, keepsake. Tick systems: breathe, which
              draws each breathing climber's lpm times 30 from its bottle,
              and move, which counts a climb down, sets `at` and `high` at
              its end and says the arrival with the air there.
      3.9.3.4 Ticks of the walk: the icefall from 2:00, 12 ticks to 8:00;
              the summit push from 23:00, 10 ticks to 4:00 at 2 litres a
              minute, 600 of 1200 left; the descent, 9 ticks, Teo at 4
              litres a minute on the spare, 1080, and the player at 2, 540.
              A move whose time no band states, as the Western Cwm or the
              Lhotse Face, is set by its step system with no tick.
      3.9.3.5 The chosen output: the spare's `full_l - left_l`, 1080, first
              said at the decision, `1080 of its 1200 litres`.

## 4 Confirming the repeated output

4.1 Each guide's gold gains `repeated`, the SQL that reads the chosen
    output from the server's databases at the end, as one row of one text:

```json
"repeated": {
  "db": "drive",
  "sql": "SELECT CAST(tally.head AS TEXT) FROM tally JOIN entity ON entity.id = tally.entity WHERE entity.name = ?",
  "params": ["herd"]
}
```

4.1.1 Ruth's reads `printf('$%d.%02d', cents / 100, cents % 100)` of
      ruth's purse, and Dawa's `CAST(full_l - left_l AS TEXT)` of the
      spare. The text T is a measurement, or plain arithmetic on one; the
      gold holds the query and never the value.

4.2 audit_read.repeat_check(entries, table, end, repeated) runs the query
    on the databases copied to `end` when the server ended, read only, and
    raises AuditFailed at the first of these that fails, naming the line of
    the audit that shows it:

4.2.1 the query gives exactly one row of one text, not empty;
4.2.2 at the end: the last ai.say reply of the audit, the band the player
      saw last, holds T as a whole token, neither a letter nor a digit on
      either side;
4.2.3 by the guide: the model reply before that ai.say holds T in its
      output_text, so the guide said it;
4.2.4 from the sim: the last model call of the end turn holds T in a
      function_call_output, so a tool result carried it to the guide;
4.2.5 not by hand: no `content` text of the built table holds T, which
      covers every ask, puzzled, otherwise, after and paused text, as
      table_build folds them into contents; the scripts the table sends are
      arguments, not contents;
4.2.6 read, not made: the end turn, from its ui.input to its ai.say reply,
      commits nothing but turn.append, so the guide read T from the
      database and wrote nothing;
4.2.7 repeated: an earlier ai.say reply holds T too, the first one named,
      so the sim's output was told when it was made and told again at the
      end.

4.3 It returns the evidence as one line of this form, each L naming a line
    of the audit: `repeated: "1980" from drive, first said at L<first>,
    said at the end at L<band> by the reply L<reply>, carried by the tool
    result L<result>, in no text of the guide's own, and the last turn
    committed nothing but turns`.

4.4 guide_walk gains a last rung, `repeated`, smoke-test, after
    `databases`. It runs repeat_check on the audit, the built table, the
    copy the databases rung made and the gold's `repeated`, appends a blank
    line and the evidence or `failure: ...` to build/audit/NAME_db.txt in
    every run, and only then fails on what it found.

4.5 audit_read.py's program does not run the check, as it holds no copy of
    the databases.

4.6 The check fits the scripted guide, which repeats by quoting. A real
    model could say 1980 as nineteen eighty and fail 4.2.2; a real provider
    is tried only by the maintainer, by hand, outside every run.

4.7 The unit suite test_audit_read gains a told walk with a repeat that
    passes, and one case per condition of 4.2 that fails it, each with its
    own message, its databases written by the real store in a scratch
    directory, so the line count reaches every line of repeat_check.

## 5 Changes by file

5.1 Rules first, in the project's rules, before any code: new rules
    `guide ecs`,
    `ecs core tables`, `ecs_step`, `ecs system contract`, `ecs replay
    agreement`, `guide scripts`, `guide intent`, `guide end step`, `guide
    repeated`, `repeat_check` and `guide repeated rung`; rewritten `guide
    sim contract`, `guide sim result`, `guide sim tables`, `guide build
    turn`, `guide beat`, `guide keepsake turn`, `guide table source`,
    `table_build`, `guide exit expansion`, `guide gold`, `guide rungs`,
    `guide digest`, `guide walks`, `guide time`, and Isaiah Cole's, Ruth
    Calloway's and Dawa's rules for their scripts, tables and constants.
    `guide compaction` is rewritten from the audits of the first passing
    run, as each beat now stores one more tool row and compaction comes
    sooner.
5.2 Stubs: API/python/audit_read.pyi gains repeat_check; the header of
    API/python/guide_walk.pyi names the `repeated` rung, `$ecs` and the
    exit's lists.
5.3 python/guide_walk.py: table_build replaces `{"$ecs": FILE}` by the text
    of python/guides/ecs/FILE, by the rules of `$text`; the exit takes
    `calls` and `resume_calls`; the rung `repeated`.
5.4 python/audit_read.py: repeat_check.
5.5 python/guides/ecs/: init.js and step.js, new.
5.6 python/guides/NAME/: table.json, lib.js, spawn.js, report.js and the
    systems, new or rewritten; prompt.txt rewritten for the scripts, verbs
    and report a real model would call; sim.js removed; introduction.txt
    unchanged.
5.7 Golds: python/test_setting_test_guide_NAME.json, every band unchanged,
    the rows checks re-pinned to the components, the last step, and
    `repeated`; python/test_setting_test_guide_walk.json, the scratch guide
    in the new forms; python/test_setting_test_audit_read.json, the cases
    of 4.7.
5.8 Tests: python/test_guide_walk.py, `$ecs` and the exit's lists built
    and refused; python/test_audit_read.py, the cases of 4.7.
5.9 No TypeScript, engine module, line type or tool changes: the engine is
    untouched, and what changes is what the fake guide does with it and
    what the test checks.

## 6 Runs

6.1 `./test_posix.sh` at the end to end level runs exactly the three guide
    tests, so it proves the sims, the bands, the replay and the repeat, and
    it is the run allowed after changes.
6.2 The unit suites test_guide_walk and test_audit_read, the API match of
    the stubs and the line count of audit_read.py run only at higher
    levels, which need the maintainer's permission, question 9.2.
6.3 Estimates, to be measured in wave 3 of the schedule: today Isaiah's
    walk commits 27 sql.run lines in 3.1 s of audit time; with a push per
    changed system per tick, about 100 to 150 a guide, and the three tests
    under 60 s, inside the 180 s of the end to end deadline.
6.4 No run contacts a real AI provider; the scripted provider answers every
    model and image request.

## 7 Schedule

7.1 Agents help: the three guides are independent once the core and the
    table's forms exist, and each guide's scripts, table and gold are about
    two thousand lines of work kept by one hand.
7.2 Rules for every agent:
    7.2.1 It owns the files its line names and touches no other; a fix it
          finds elsewhere goes in its report. With no file owned twice, no
          lock is needed.
    7.2.2 It runs nothing: no test, no `node`, `python3`, `wc` or `awk`, as
          the coordinator alone runs `./test_posix.sh`. It never stages or
          commits.
    7.2.3 Its report is its final message: files changed, decisions, draft
          rule text for the project's rules, and anything left open.
    7.2.4 It follows the comment rules, one line below the header, and gives
          each function two English names.
7.3 Wave 0, the coordinator, no agent: the rules of 5.1 but the per-guide
    ones, the stubs of 5.2, and the engineering log.
7.4 Wave 1, two agents at once:
    7.4.1 core: python/guides/ecs/init.js and step.js; python/guide_walk.py;
          python/test_guide_walk.py and its gold.
    7.4.2 check: python/audit_read.py's repeat_check;
          python/test_audit_read.py and its gold.
7.5 Wave 2, three agents at once, each starting as soon as `core` reports:
    7.5.1 isaiah: python/guides/isaiah/ and
          python/test_setting_test_guide_isaiah.json.
    7.5.2 ruth: python/guides/ruth/ and
          python/test_setting_test_guide_ruth.json.
    7.5.3 dawa: python/guides/dawa/ and
          python/test_setting_test_guide_dawa.json.
    Each keeps every band, adds the last step and `repeated`, re-pins the
    rows checks, and drafts its guide's rules.
7.6 Wave 3, the coordinator: applies the drafted rules; runs
    `./test_posix.sh`; reads build/audit/NAME.txt and NAME_db.txt; sends
    each failure to the agent that owns the file, at most three rounds;
    then the runs question 9.2 allows.
7.7 Wave 4, two reading reviews at once, read only: one of the JavaScript,
    the core and the three guides' scripts, against 3.4, 3.5 and the band
    rule; one of the Python, guide_walk, audit_read, the tests and golds,
    against the rules. The coordinator fixes what they find, then runs
    `./test_posix.sh` again and writes the postmortem.
7.8 Seven agents in all, never more than three at once.

## 8 Designs weighed and not built

8.1 An engine call `engine.script_run(name, args)`, so a script runs
    another through the engine's own runner with its error capture and
    trace: ts/script.ts adds the method to the frozen `engine`, built
    from the same store, and API/ts/script.d.ts names it. Not built, as a
    guide's step can load its systems with what scripts have today, and
    the plan then changes no engine code. Take it when nested runs need
    script_debug's trace.
8.2 The guide calls each system by its own browser_script_run. Not built,
    as the table is fixed and cannot know how many ticks a step runs; the
    step's loop until no entity is busy decides that from the data.
8.3 A quote through arrays, as `results.0.rows.0.0`, so the guide could
    read the output by browser_sql_run alone: ts/provider_script.ts's quote
    takes a member that is a decimal index of an array, and
    audit_read.guide_check's twin does the same. Not built, as a report
    script reads it with no provider change.
8.4 Systems kept as SQL text in a column of `system`, run by the step with
    no JavaScript. Not built: the request asks for scripts sent over, and
    the sims need floating point that SQL must not compute, 3.5.1.
8.5 A shorthand `{"$intent": [VERB, VALUE]}` in table.json for the two
    calls of a beat. Not built: the repeated SQL is plain data, and a guide
    stays written in JSON and JavaScript with no new Python form.

## 9 Questions

9.1 Which guides move to the entity-component-system sim? This decides
    the size of wave 2.
    [x] A. All three, Isaiah's, Ruth's and Dawa's: the core is proven by
        three different sims, seven agents, each walk one step longer.
    [ ] B. Isaiah's alone now; Ruth's and Dawa's keep their one-row sims
        until his passes: five agents now, two more later.
    [ ] C. A fourth guide built this way from the start, the three left as
        they are: a new walk and gold, written by hand.
9.2 May runs above the end to end level prove the new unit tests, the
    stubs and the line count? This decides whether wave 3 ends proven.
    [x] A. Yes, after `./test_posix.sh` passes, `./test_posix.sh
        --test-all` as often as fixing needs, as task 1.1 of
        tmp/tasks_12_0354.md allowed for the audit's work.
    [ ] B. One `./test_posix.sh --test-all` at the end, its failures
        reported and not fixed by more full runs.
    [ ] C. None; the maintainer's own full run proves them.

## 10 Requirements

10.1 Of this request, 1.1: every part is planned without modification,
     class D: the databases read, the guide operating the sim through them
     on the player's behalf, scripts sent and run, SQL and the
     entity-component-system pattern together, the confirmation of a
     repeated output at the end, and a schedule, as agents help.
10.2 Of the earlier requests in tmp/tasks_11_1956.md and
     tmp/tasks_12_0354.md, kept, class D: the guides confirm, talk, build a
     sim and guide the player through it, offline, on the fake AI alone;
     Ruth's sim stays a real world aviation stunt model; the audit is
     checked and every message is the guide's; the digest shows every
     entry; the server's databases are copied at the end, proven by replay
     and written as text to build/audit/NAME_db.txt.
10.3 Class C: the `continue` of tmp/tasks_12_0354.md 1.3, confirmed by the
     maintainer as no request.
10.4 Class A, request unsatisfied or modified without cause: none.
10.5 Class B, modified with cause but without confirmation:
     10.5.1 "The fake guide" is taken as all three guides; question 9.1
            asks.
     10.5.2 "A certain simulator output" is chosen per guide: Isaiah's 1980
            head, Ruth's $71.85 and Dawa's 1080 litres, each made by
            stepping or by a system and said before the end.
     10.5.3 "At the end of the conversation" adds one last step to each
            walk, a goodbye answered by a read-only report, so that the
            last words are a repeat read from the database.
     10.5.4 "Repeated" is read as said again: told when the sim made it and
            told at the end, 4.2.7.
     10.5.5 "Send over scripts and run them": the guide runs `ecs_step` once
            per decision, and the step runs the systems the guide sent,
            8.2 giving why.
     10.5.6 Every band of today's walks is kept byte for byte, so the new
            sims are proven equal to the old by the same golds.
     10.5.7 The cuts of the digest and the database text, removed in
            tmp/tasks_12_0354.md 1.3 with no request, stand unconfirmed.
            This plan neither needs nor changes them; with whole system
            scripts in `_files`, NAME_db.txt grows by their text.
10.6 Each B item is satisfied by the plan as written, and each is cheap to
     overturn before wave 2 starts; 10.5.1 alone holds a question.
