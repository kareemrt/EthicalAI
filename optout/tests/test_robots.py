import unittest

from optout.robots import parse


class RobotsSemantics(unittest.TestCase):
    def test_longest_match_wins_and_allow_breaks_ties(self):
        r = parse("User-agent: *\nDisallow: /docs/\nAllow: /docs/public/\nAllow: /x\nDisallow: /x\n")
        self.assertFalse(r.can_fetch("bot", "/docs/secret"))
        self.assertTrue(r.can_fetch("bot", "/docs/public/a"))
        self.assertTrue(r.can_fetch("bot", "/x"))  # equal length → Allow

    def test_wildcards_and_end_anchor(self):
        r = parse("User-agent: *\nDisallow: /*.pdf$\nDisallow: /tmp*/cache\n")
        self.assertFalse(r.can_fetch("bot", "/files/a.pdf"))
        self.assertTrue(r.can_fetch("bot", "/files/a.pdf?download=1"))
        self.assertFalse(r.can_fetch("bot", "/tmp-1/cache/x"))

    def test_specific_group_overrides_star(self):
        r = parse("User-agent: *\nDisallow: /\n\nUser-agent: GoodBot\nAllow: /\n")
        self.assertTrue(r.can_fetch("goodbot"))
        self.assertFalse(r.can_fetch("OtherBot"))
        self.assertEqual(r.decide("GOODBOT").group, "goodbot")

    def test_stacked_user_agents_share_rules_and_groups_merge(self):
        r = parse("User-agent: A\nUser-agent: B\nDisallow: /a\n\nUser-agent: A\nDisallow: /b\n")
        for path in ("/a", "/b"):
            self.assertFalse(r.can_fetch("A", path))
        self.assertTrue(r.can_fetch("B", "/b"))

    def test_empty_disallow_comments_and_unknown_lines(self):
        r = parse("﻿# hi\nUser-agent: *  # all\nCrawl-delay: 5\nDisallow:\nSitemap: /s.xml\n")
        self.assertTrue(r.can_fetch("bot", "/anything"))

    def test_no_matching_group_means_allowed(self):
        d = parse("User-agent: GPTBot\nDisallow: /\n").decide("ClaudeBot")
        self.assertTrue(d.allowed)
        self.assertIsNone(d.group)

    def test_robots_txt_itself_is_always_allowed(self):
        self.assertTrue(parse("User-agent: *\nDisallow: /\n").can_fetch("bot", "/robots.txt"))

    def test_version_suffix_in_user_agent_is_ignored(self):
        self.assertFalse(parse("User-agent: CCBot/2.0\nDisallow: /\n").can_fetch("ccbot"))


if __name__ == "__main__":
    unittest.main()
