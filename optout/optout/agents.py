"""Registry of known crawlers, grouped by what they do with your content.

Edit this list freely — it is plain data. Tokens are the robots.txt
"product token" each operator documents; matching is case-insensitive.

Last reviewed: 2026-11. Operators add and rename bots often; PRs welcome.
"""

from typing import NamedTuple

TRAINING = "training"  # collects content to train AI models
ANSWER = "answer"      # indexes content for AI search / answer engines
USER = "user"          # fetches a page live because a user asked an AI to
SEARCH = "search"      # classic search engines — usually you want these OPEN

CATEGORIES = {
    TRAINING: "AI training crawlers",
    ANSWER: "AI answer engines",
    USER: "User-triggered AI fetchers",
    SEARCH: "Search engines (keep open)",
}


class Agent(NamedTuple):
    token: str
    operator: str
    category: str


AGENTS = [
    # --- AI training -------------------------------------------------------
    Agent("GPTBot", "OpenAI", TRAINING),
    Agent("ClaudeBot", "Anthropic", TRAINING),
    Agent("anthropic-ai", "Anthropic (legacy)", TRAINING),
    Agent("Google-Extended", "Google (Gemini)", TRAINING),
    Agent("Applebot-Extended", "Apple", TRAINING),
    Agent("Meta-ExternalAgent", "Meta", TRAINING),
    Agent("CCBot", "Common Crawl", TRAINING),
    Agent("Bytespider", "ByteDance", TRAINING),
    Agent("Amazonbot", "Amazon", TRAINING),
    Agent("cohere-training-data-crawler", "Cohere", TRAINING),
    Agent("AI2Bot", "Allen Institute for AI", TRAINING),
    Agent("Diffbot", "Diffbot", TRAINING),
    Agent("omgili", "Webz.io", TRAINING),
    Agent("Timpibot", "Timpi", TRAINING),
    # --- AI answer / search engines ---------------------------------------
    Agent("OAI-SearchBot", "OpenAI", ANSWER),
    Agent("Claude-SearchBot", "Anthropic", ANSWER),
    Agent("PerplexityBot", "Perplexity", ANSWER),
    Agent("DuckAssistBot", "DuckDuckGo", ANSWER),
    Agent("YouBot", "You.com", ANSWER),
    # --- Live fetches on behalf of a user ---------------------------------
    Agent("ChatGPT-User", "OpenAI", USER),
    Agent("Claude-User", "Anthropic", USER),
    Agent("Perplexity-User", "Perplexity", USER),
    Agent("Meta-ExternalFetcher", "Meta", USER),
    Agent("MistralAI-User", "Mistral", USER),
    # --- Classic search (sanity check: blocking these hurts discoverability)
    Agent("Googlebot", "Google", SEARCH),
    Agent("Bingbot", "Microsoft", SEARCH),
    Agent("DuckDuckBot", "DuckDuckGo", SEARCH),
    Agent("Applebot", "Apple", SEARCH),
]


def by_category(*categories: str) -> list[Agent]:
    return [a for a in AGENTS if a.category in categories]
