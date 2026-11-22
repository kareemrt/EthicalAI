"""Instruction-like language aimed at a model rather than a human reader.

Patterns run on a "skeleton" of the text (invisibles removed, look-alikes
folded), so `ig​nore previous instructions` or fullwidth text still match.
"""
from __future__ import annotations

import re

from ..findings import Severity, Source
from .unicode import skeletonize

H, M = Severity.HIGH, Severity.MEDIUM
_F = re.I | re.M

#  rule id, severity, pattern, why it matters
RULES: list[tuple[str, Severity, re.Pattern, str]] = [
    ("phrase.override", H, re.compile(
        r"\b(ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}?\b(previous|prior|above|earlier|"
        r"all|any|your|the|system)\b[^.\n]{0,30}?\b(instructions?|prompts?|rules|directions|"
        r"guidelines|guardrails|context|programming)\b", _F),
     "Tries to override the model's instructions."),
    ("phrase.secrecy", H, re.compile(
        r"\b(do not|don'?t|never|without)\b\s+(tell(ing)?|inform(ing)?|mention(ing)?|reveal(ing)?|"
        r"alert(ing)?|notify(ing)?|warn(ing)?)\b[^.\n]{0,30}?\b(the\s+)?(users?|human|recruiters?|readers?|"
        r"reviewers?|operators?|owners?|customers?)\b", _F),
     "Asks the model to hide its actions from the user."),
    ("phrase.exfiltration", H, re.compile(
        r"\b(send|forward|e-?mail|upload|post|transmit|leak|exfiltrate)\b[^.\n]{0,40}?\b(passwords?|"
        r"credentials?|api[ _-]?keys?|access\s+tokens?|secrets?|private\s+keys?|ssh\s+keys?|"
        r"(conversation|chat)\s+(history|log)|personal\s+data|(the\s+)?user'?s\s+(files|e-?mails|messages|"
        r"contacts|data|documents|conversation))\b|"
        r"\b(send|upload|post|cat|copy)\b[^.\n]{0,40}?(~/\.ssh|~/\.aws|\.env\b|id_rsa)", _F),
     "Asks the model to move sensitive data somewhere."),
    ("phrase.url-smuggling", H, re.compile(
        r"\b(append|add|include|insert|encode|embed)\b[^.\n]{0,50}?\b(in|into|to)\b\s+(the\s+|this\s+|a\s+)?"
        r"(url|link|image|query string|parameter)", _F),
     "Asks the model to hide data inside a URL (a classic exfiltration channel)."),
    ("phrase.remote-code", H, re.compile(
        r"\b(curl|wget|iwr|Invoke-WebRequest)\b[^\n|]{1,200}\|\s*(sudo\s+)?(ba|z)?sh\b|"
        r"\bpowershell\b[^\n]{0,40}-e(nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{20,}", _F),
     "Pipes a remote script into a shell."),
    ("phrase.chat-template", H, re.compile(
        r"<\|(im_start|im_end|system|user|assistant|endoftext|eot_id|start_header_id)\|>|"
        r"\[/?INST\]|<</?SYS>>|<start_of_turn>", _F),
     "Contains raw chat-template tokens used to forge conversation turns."),
    ("phrase.fake-role", M, re.compile(
        r"^\s*(#{1,3}\s*)?\[?(system|assistant|developer)\]?\s*(prompt|message|note|override)?\s*:\s*\S", _F),
     "Line impersonates a system/assistant message."),
    ("phrase.role-reassign", M, re.compile(
        r"\byou\s+are\s+(now|no\s+longer)\b|\bfrom\s+now\s+on,?\s+you\b|\b(developer|god|jailbreak|DAN)\s+mode\b|"
        r"\bact\s+as\s+an?\s+(unrestricted|unfiltered|uncensored|jailbroken)\b|\bnew\s+instructions?\s*:", _F),
     "Tries to give the model a new identity or rule set."),
    ("phrase.ai-addressed", M, re.compile(
        r"\bif\s+you\s+are\s+an?\s+(ai|llm|large\s+language\s+model|language\s+model|assistant|chatbot|bot|agent)\b|"
        r"\b(notes?|messages?|instructions?|attention)\s+(to|for)\s+(any\s+|all\s+)?(ai|llms?|language\s+models?|"
        r"assistants?|chatbots?|agents?|automated\s+(systems?|reviewers?|agents?|contributors?|tools?))\b", _F),
     "Text speaks directly to an AI system, not to the human reader."),
    ("phrase.prompt-leak", M, re.compile(
        r"\b(reveal|print|repeat|output|display|show|dump)\b[^.\n]{0,30}?\b(system\s+prompt|initial\s+"
        r"instructions|hidden\s+instructions|your\s+instructions|developer\s+message)\b", _F),
     "Asks the model to disclose its hidden instructions."),
]


def matches(text: str):
    """Yield (rule, severity, why, start, end) on the skeleton of `text`."""
    skeleton, index = skeletonize(text)
    for rule, severity, pattern, why in RULES:
        for m in pattern.finditer(skeleton):
            yield rule, severity, why, index[m.start()], index[m.end() - 1] + 1


def first_match(text: str):
    return next(matches(text), None)


def detect(src: Source):
    for rule, severity, why, start, end in matches(src.text):
        yield src.finding(rule, severity, why, start, end)
