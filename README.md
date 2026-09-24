# Dr. Nutritionist

Log a meal in plain English, in the words you would actually use, and get the
day's macros against targets worked out from your own body and goal.

```
"2 rotis, a bowl of dal, 150g chicken breast and a cup of curd"
```

The point of the project is where each decision is made. A language model reads
the meal and writes the summary, because those are language problems. Every
nutrition figure comes from a data source through a tool call, and the
arithmetic is ordinary Python. **The model never produces a number.**

General information only. Not dietetic or medical advice.

---

## How it works

```
 meal in English
        │
        ▼
 Meal reader agent  ──────────►  ParsedMeal        (typed handoff)
   (LLM, no tools)               items: name, quantity, unit
        │
        ▼
 Nutrition researcher agent ───►  food_lookup tool  (real function calling)
   (LLM + 1 tool)                 one call per food, every result recorded
        │                              │
        │                              ├── Indian staples table   (roti, dal, idli)
        │                              └── USDA FoodData Central  (everything else)
        ▼
 Python                    ────►  grams, scaling, totals, targets
   (no model involved)            arithmetic that can be unit tested
        │
        ▼
 Coach agent                ───►  Advice            (typed handoff)
   (LLM, given the totals)        summary + suggestions
```

Three agents, run as a sequential CrewAI crew.

## Why two food sources

USDA is a good database of American food. Asked for "roti" it offers a packet
bread, and asked for "dal" it returns whatever branded product shares the word.
Since every macro in the report comes from that match, a wrong match quietly
poisons the whole day.

So around thirty common Indian foods are held locally and USDA answers
everything else. Each row in the result names the source it came from, so a
number can always be traced. Those values are typical home prepared portions
following the ICMR-NIN Indian Food Composition Tables, and they are approximate:
a thin dal and a thick dal are not the same food.

## The design decisions worth knowing

**1. Typed handoffs, because silent failure is the real risk.**
In a sequential crew each task's output becomes the next task's input. A task
that returns something vague does not fail, it gets accepted, and the next agent
builds on it. Three steps later there is a confident answer resting on nothing
and no step ever raised. So each handoff is a Pydantic model (`schemas.py`) and
is validated: an empty meal, a blank food name, a negative quantity or a two
word summary all fail at the step that produced them.

**2. The tool's result is the source of truth, not the agent's description of it.**
The lookup tool records every call it makes, and the totals are built from those
recordings rather than from figures the agent writes into its answer. A model
transcribing "23.1g of protein" can get it wrong, and there is no reason to let
it.

**3. Failure is graded, not all or nothing.**

| What fails | What happens |
|---|---|
| The meal reader | Fatal. With no items there is nothing to look up, and the caller is told. |
| One food's lookup | That food is skipped and named as skipped. The rest of the meal still counts. |
| The model provider | The next provider in the chain is tried. |
| The coach | The summary is templated from the numbers, which were never the model's anyway. |
| No API key at all | The crew is skipped and a rule based path runs. Tidy input only. |

---

## Running it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env`:

```
USDA_API_KEY=       # free: https://fdc.nal.usda.gov/api-key-signup.html
MISTRAL_API_KEY=    # optional
GEMINI_API_KEY=     # optional second provider, tried when the first throttles
```

With no model key at all it still runs, using the rule based parser.

```bash
streamlit run app/streamlit_app.py
python -m pytest -q
```

---

## Layout

```
dr_nutritionist/
  schemas.py        the typed handoffs between agents
  foods.py          one lookup, two sources behind it
  indian_foods.py   the Indian staples table
  usda.py           FoodData Central, framework free
  tools.py          the lookup exposed to the model as a tool
  quantities.py     "2 rotis" and "150g" into grams
  targets.py        daily targets from the profile (Mifflin St Jeor)
  report.py         scaling and totals, no model involved
  parsing.py        rule based meal reading, the no-model fallback
  crew.py           agents, tasks, the crew, and what happens when a step fails
app/
  streamlit_app.py
tests/              114 tests, no API key and no network needed
```

---

## Three bugs worth recording

**An intermittent 400 from USDA.** Identical requests failed about a third of
the time, returning an HTML error page rather than the API's own JSON. The cause
was a bracketed value, `Survey (FNDDS)`, in the `dataType` filter: some of the
nodes behind the API accept it and others reject it, so the same request
succeeded or failed depending on which one answered. Narrowing the filter and
widening the search only when it returns nothing fixed it.

**A meal split on commas only.** "150g chicken breast and a cup of curd" came
through as a single item, matched curd, and counted 150 grams of chicken as
curd. Nothing failed. The total was simply wrong, which is the kind of bug that
survives a demo.

**A plural that cost two and a half times.** "2 rotis" missed the typical weight
for "roti" and fell through to a default of 100g each, counting 200g instead of
80g.

All three are now tests in `tests/test_regressions.py`.

## What this is not

It does not plan meals, hold recipes or track progress over time. An earlier
version of this README described those as features. They were never built, and
claiming them was a mistake.

Micronutrients are not modelled, only the three macros. Counted foods such as
"2 eggs" use a typical weight, so those rows are estimates and the code marks
them as estimated rather than hiding it.

## History

The first version was a command line script. It had the USDA API key written
into the source and pushed to GitHub, compared every user against the same
hardcoded macro targets while collecting a profile it never used, and called a
method that did not exist, so it crashed on the first food.

Rebuilt in September 2026: key revoked and moved to the environment, targets
derived from the person, a second food source for Indian meals, real tool
calling, validated handoffs, a provider fallback chain, a Streamlit front end
and 114 tests.
