"""
The crew: three agents, three tasks, run in order.

WHAT EACH STEP IS FOR
Reading a meal written in English is a language problem, so a model does
it. Looking up macros is a data problem, so a tool does it. Adding the
day up is arithmetic, so Python does it. Writing the advice is a
language problem again, so the model does that.

The model is never the thing that produces a number.

WHY THE HANDOFFS ARE TYPED
In a sequential crew, each task's output is the next task's input. A task
that returns something vague does not fail, it gets accepted, and the
next agent builds on it. Three steps later you have a confident answer
resting on nothing, and no step ever raised.

So every handoff is validated against a schema. A bad handoff fails
loudly, at the step that caused it, which is the only place it can be
diagnosed.

WHAT HAPPENS WHEN A STEP FAILS
Task 1 failing is fatal, because with no items there is nothing to look
up, and the caller is told. Task 2 failing on one food is not fatal: that
food is skipped, reported as skipped, and the rest of the meal still
counts. Task 3 failing costs the written summary only, and a plain one is
produced from the numbers, which were never the model's to begin with.

With no model at all the whole crew is skipped and the deterministic
path runs, so the app degrades rather than stopping.
"""

from __future__ import annotations

from dataclasses import dataclass

from crewai import LLM, Agent, Crew, Process, Task

from . import config, parsing, report
from .schemas import Advice, DayTotals, ParsedMeal
from .targets import Profile, daily_targets
from .tools import UsdaLookupTool


@dataclass
class DayResult:
    """Everything one run produced, including what went wrong."""

    totals: DayTotals
    advice: Advice
    skipped: list[str]
    used_model: bool
    notes: list[str]


def _llm(model: str, key: str) -> LLM:
    # Low temperature throughout: splitting a meal into foods and
    # summarising numbers are both tasks where invention is the failure.
    return LLM(model=model, api_key=key, temperature=0.2)


# -- the agents ---------------------------------------------------------
#
# Roles are narrow on purpose. An agent told it is a nutritionist will
# offer nutrition advice at every step, including the step where it is
# only supposed to be splitting a sentence into foods.


def meal_reader(llm: LLM) -> Agent:
    return Agent(
        role="Meal reader",
        goal="Turn a meal written in ordinary English into a list of foods and amounts.",
        backstory=(
            "You read how people actually write food down, including 'a couple of "
            "eggs' and '2 rotis'. You split the meal and nothing else. You never "
            "comment on whether it is healthy."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def nutrition_looker_upper(llm: LLM, tool: UsdaLookupTool) -> Agent:
    return Agent(
        role="Nutrition data researcher",
        goal="Find every food in the USDA database, using the tool for each one.",
        backstory=(
            "You know that remembered nutrition figures are unreliable, so you look "
            "everything up. If the first wording finds nothing, you try a plainer "
            "one, for example 'rice' instead of 'leftover fried rice'."
        ),
        llm=llm,
        tools=[tool],
        verbose=False,
        allow_delegation=False,
    )


def coach(llm: LLM) -> Agent:
    return Agent(
        role="Nutrition coach",
        goal="Explain what the day's totals mean against the person's targets.",
        backstory=(
            "You are given the totals and the targets. You explain them plainly and "
            "suggest practical changes. You do not recalculate anything, you do not "
            "invent figures, and you do not give medical advice."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


# -- the tasks ----------------------------------------------------------


def _read_task(agent: Agent, meal_text: str) -> Task:
    return Task(
        description=(
            f"Split this meal into individual foods with amounts:\n\n{meal_text}\n\n"
            "Give each item a plain food name with no adjectives about cooking or "
            "leftovers, a quantity, and one of these units: g, kg, ml, piece, "
            "cup, bowl, katori, glass, or an empty string. If someone writes 'a "
            "couple of eggs', that is quantity 2, unit 'piece'. 'A bowl of dal' is "
            "quantity 1, unit 'bowl'. Keep the serving word: dropping it turns a "
            "bowl into a default handful. Do not invent foods that were not "
            "mentioned."
        ),
        expected_output="A list of food items, each with name, quantity and unit.",
        agent=agent,
        output_pydantic=ParsedMeal,
    )


def _lookup_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "For every food in the list from the previous step, call the usda_lookup "
            "tool once. If a lookup fails, try one simpler wording, then move on. "
            "Do not state any nutrition figure that did not come from the tool."
        ),
        expected_output="A short note of which foods were found and which were not.",
        agent=agent,
        context=context,
    )


def _advice_task(agent: Agent, totals: DayTotals, short: list[str]) -> Task:
    shortfall_text = "; ".join(short) if short else "nothing is notably short"
    return Task(
        description=(
            "Here are the day's totals, already calculated. Do not recalculate them.\n\n"
            f"Eaten: {totals.protein_g}g protein, {totals.fat_g}g fat, "
            f"{totals.carbs_g}g carbohydrate, {totals.calories} kcal.\n"
            f"Target: {totals.target_protein_g}g protein, {totals.target_fat_g}g fat, "
            f"{totals.target_carbs_g}g carbohydrate, {totals.target_calories} kcal.\n"
            f"Shortfalls: {shortfall_text}.\n\n"
            "Write two or three sentences explaining where the day stands, then two "
            "or three practical suggestions naming real foods. Use only the figures "
            "above. This is general information, not medical advice."
        ),
        expected_output="A short summary and a few practical suggestions.",
        agent=agent,
        output_pydantic=Advice,
    )


# -- running it ---------------------------------------------------------


def _plain_advice(totals: DayTotals, short: list[str]) -> Advice:
    """The summary used when there is no model, or the model step failed."""
    if short:
        summary = (
            f"The day came to {totals.calories} kcal against a target of "
            f"{totals.target_calories}. Short on: {', '.join(short)}."
        )
        suggestions = [f"Add something to bring up your {s.split(' is ')[0]}." for s in short]
    else:
        summary = (
            f"The day came to {totals.calories} kcal against a target of "
            f"{totals.target_calories}, with every macro within range of target."
        )
        suggestions = ["Keep the day roughly as it is."]
    return Advice(summary=summary, suggestions=suggestions)


def run_deterministic(meal_text: str, profile: Profile) -> DayResult:
    """
    The whole pipeline with no model involved.

    Used when there is no API key, and as the fallback when the crew
    cannot complete. It handles tidy input only, which is exactly the
    trade: no model means no understanding of 'a couple of eggs'.
    """
    parsed = parsing.parse_meal(meal_text)
    found, skipped = report.look_up_all(parsed.items)
    totals = report.total_day(found, daily_targets(profile))
    short = report.shortfalls(totals)
    return DayResult(
        totals=totals,
        advice=_plain_advice(totals, short),
        skipped=skipped,
        used_model=False,
        notes=["No model was used: meals were parsed by rule and advice was templated."],
    )


def run(meal_text: str, profile: Profile) -> DayResult:
    """Run the crew, falling back to the deterministic path when it cannot."""
    if not config.model_available():
        return run_deterministic(meal_text, profile)

    notes: list[str] = []
    tool = UsdaLookupTool()

    # Try each provider in turn. A throttled free tier is the most common
    # failure here by far, and it is not a reason to give up on the model
    # altogether when another one is configured.
    read = None
    llm = None
    failures: list[str] = []
    for model, key in config.providers():
        tool.forget()
        try:
            # Building the model counts as part of trying it. A missing
            # provider package raises here rather than on the call, and
            # the first draft of this loop let that crash the whole run
            # instead of moving on to the next provider.
            llm = _llm(model, key)
            reader = meal_reader(llm)
            researcher = nutrition_looker_upper(llm, tool)
            read = _read_task(reader, meal_text)
            look_up = _lookup_task(researcher, context=[read])
            Crew(
                agents=[reader, researcher],
                tasks=[read, look_up],
                process=Process.sequential,
            ).kickoff()
            if model != config.providers()[0][0]:
                notes.append(f"Used {model} after the first provider failed.")
            break
        except Exception as problem:  # noqa: BLE001, try the next provider
            failures.append(f"{model}: {problem}")
            read = None

    if read is None:
        return _fell_back(meal_text, profile, "No provider could complete the crew: " + "; ".join(failures))

    parsed = read.output.pydantic if read.output else None
    if not isinstance(parsed, ParsedMeal):
        return _fell_back(meal_text, profile, "The meal reader did not return a usable list of foods.")

    # The numbers come from what the tool returned, not from what the
    # agent wrote about it. Anything the agent failed to look up is
    # counted as skipped rather than guessed.
    found = []
    skipped = []
    for item in parsed.items:
        match = tool.match_for(item.name)
        if match is None:
            skipped.append(f"{item.name}: the researcher did not find a USDA entry")
            continue
        found.append(report.macros_for(item, match))

    if not found:
        return _fell_back(meal_text, profile, "No food in that meal could be matched in USDA.")

    totals = report.total_day(found, daily_targets(profile))
    short = report.shortfalls(totals)

    # The advice step is the only one that can fail without costing the
    # result, because the numbers are already final by this point.
    # The same chain again, because the provider that answered a minute
    # ago can be busy by the time this runs: in testing the reader
    # succeeded on one provider and the coach came back 503 on the next
    # call to it.
    advice = None
    last_problem = ""
    for model, key in config.providers():
        try:
            coach_agent = coach(_llm(model, key))
            advice_task = _advice_task(coach_agent, totals, short)
            Crew(agents=[coach_agent], tasks=[advice_task], process=Process.sequential).kickoff()
            candidate = advice_task.output.pydantic if advice_task.output else None
            if not isinstance(candidate, Advice):
                raise ValueError("the coach did not return a usable summary")
            advice = candidate
            break
        except Exception as problem:  # noqa: BLE001, try the next provider
            last_problem = str(problem)

    if advice is None:
        notes.append(f"Wrote the summary without the model: {last_problem[:120]}")
        advice = _plain_advice(totals, short)

    return DayResult(totals=totals, advice=advice, skipped=skipped, used_model=True, notes=notes)


def _fell_back(meal_text: str, profile: Profile, why: str) -> DayResult:
    result = run_deterministic(meal_text, profile)
    result.notes.insert(0, why)
    return result
