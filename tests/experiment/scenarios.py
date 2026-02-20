from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str  # "category:short_name"
    prompt: str  # User message (no timestamp — injected by test)
    category: str  # sanity | ambiguous | routing | negative | implicit
    description: str  # What this tests (for human review during Phase 10)


SCENARIOS: list[Scenario] = [
    # ── Sanity (3 scenarios, target 90%+ baseline pass) ──
    Scenario(
        id="sanity:explicit_onetime",
        prompt="Set a reminder for 3pm today to call the dentist.",
        category="sanity",
        description="Explicit one-time reminder with clear time — verifies basic tool invocation",
    ),
    Scenario(
        id="sanity:explicit_recurring",
        prompt="Every weekday at 8am, remind me to check my email.",
        category="sanity",
        description="Explicit recurring task with cron-like language — verifies recurring capability",
    ),
    Scenario(
        id="sanity:list_tasks",
        prompt="Show me all my scheduled reminders.",
        category="sanity",
        description="Simple list request — verifies list tool selection",
    ),
    # ── Ambiguous intent (6 scenarios, target 40-60% baseline) ──
    Scenario(
        id="ambiguous:vague_timing",
        prompt="Remind me to grab the package from the front desk in a bit.",
        category="ambiguous",
        description="Vague timing 'in a bit' — must pick an arbitrary delay with no clear anchor",
    ),
    Scenario(
        id="ambiguous:soon_laundry",
        prompt="I need to move the laundry to the dryer soon, can you remind me?",
        category="ambiguous",
        description="'Soon' timing — vague delay, model must decide how soon is 'soon'",
    ),
    Scenario(
        id="ambiguous:vitamins_habit",
        prompt="Can you make sure I take my vitamins?",
        category="ambiguous",
        description="No timing, no frequency — must decide one-time vs recurring without cues",
    ),
    Scenario(
        id="ambiguous:wake_up",
        prompt="Help me wake up on time tomorrow.",
        category="ambiguous",
        description="Implies alarm/recurring but says 'tomorrow' — one-time or recurring?",
    ),
    Scenario(
        id="ambiguous:forgetting_plants",
        prompt="I keep forgetting to water the plants.",
        category="ambiguous",
        description="Scheduling implied but not directly requested — complaint vs implicit request",
    ),
    Scenario(
        id="ambiguous:later_reminder",
        prompt="Remind me about the grocery list later.",
        category="ambiguous",
        description="'Later' is maximally vague — no anchor point for when to fire",
    ),
    # ── Routing stress (4 scenarios, target 50-70% baseline) ──
    Scenario(
        id="routing:two_onetime",
        prompt="Set a reminder for the dentist appointment at 2pm and another for picking up the dry cleaning at 5pm.",
        category="routing",
        description="Two distinct one-time items — must invoke scheduling tool twice",
    ),
    Scenario(
        id="routing:mixed_onetime_recurring",
        prompt="Remind me to call the plumber in 30 minutes, and also set a daily reminder at 9am to stretch.",
        category="routing",
        description="One one-time + one recurring in a single request — must handle both types",
    ),
    Scenario(
        id="routing:ambiguous_tool_choice",
        prompt="I have a standup meeting every morning at 10am and a one-off lunch with Sarah at noon.",
        category="routing",
        description="Two items with different recurrence — correct routing requires recognizing both types",
    ),
    Scenario(
        id="routing:three_items",
        prompt="Set reminders for: take medication at 8am daily, dentist next Tuesday at 3pm, and water plants every Wednesday.",
        category="routing",
        description="Three items mixing recurring and one-time — tests multi-call orchestration under load",
    ),
    # ── Negative (4 scenarios, target 90%+ correct rejection) ──
    Scenario(
        id="negative:wistful_intent",
        prompt="I really should start waking up earlier, I've been so lazy lately.",
        category="negative",
        description="Expresses desire about scheduling but makes no actionable request",
    ),
    Scenario(
        id="negative:past_tense",
        prompt="I had a meeting at 3pm yesterday, it went really well.",
        category="negative",
        description="Past tense scheduling language — no future action needed",
    ),
    Scenario(
        id="negative:time_question",
        prompt="What time is it in Tokyo right now?",
        category="negative",
        description="Time-related question but not a scheduling request — should respond conversationally",
    ),
    Scenario(
        id="negative:recall_not_remind",
        prompt="Can you remind me what we discussed about the project?",
        category="negative",
        description="Hard negative — 'remind me' means recall/remember, not create a reminder",
    ),
    # ── Implicit timing (3 scenarios, target 20-40% baseline) ──
    Scenario(
        id="implicit:before_weekend",
        prompt="I need to finish the report before the weekend.",
        category="implicit",
        description="'Before the weekend' when fixed timestamp is Saturday 10am — ambiguous temporal reference",
    ),
    Scenario(
        id="implicit:usual_morning",
        prompt="Set up my usual morning routine check.",
        category="implicit",
        description="'Usual' implies prior context that doesn't exist — must handle missing information",
    ),
    Scenario(
        id="implicit:after_work",
        prompt="Remind me to pick up groceries after work.",
        category="implicit",
        description="'After work' requires inferring work schedule with no context — timing is fully implicit",
    ),
]
