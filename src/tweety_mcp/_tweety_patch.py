"""Upstream tweety workaround for X.com ondemand.s.js layout change.

The PyPI release of ``tweety-ns`` (2.4.1, July 2025) predates the X.com
change of 2026-03-18, which broke the regex used to locate the
``ondemand.s`` chunk and derive the animation key. The fix lives in the
upstream tweety ``main`` branch (PR #288, merged 2026-03-22) but has not
been released to PyPI yet. This module ports that fix as a runtime
monkey-patch so we can keep depending on the released package.

Remove this file and its import from ``__init__.py`` once a tweety
release containing the upstream fix is published.
"""

from __future__ import annotations

import re

import httpx


_POINTER_REGEX = re.compile(
    r'(\d+)\s*:\s*"ondemand\.s"',
    flags=(re.VERBOSE | re.MULTILINE),
)


def _find_on_demand_file(text: str) -> str | None:
    pointer_match = _POINTER_REGEX.search(text)
    if pointer_match is None:
        return None
    pointer = pointer_match.group(1)
    hash_match = re.search(rf'{pointer}\s*:\s*"([0-9a-f]+)"', text)
    if hash_match is None:
        return None
    return hash_match.group(1)


_SEARCH_QUERY_ID = "GcXk9vN_d1jUfHNqLacXQA"
_SEARCH_URL = f"https://x.com/i/api/graphql/{_SEARCH_QUERY_ID}/SearchTimeline"
_SEARCH_FEATURES = {
    "rweb_video_screen_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "verified_phone_label_enabled": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": True,
    "premium_content_api_read_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": True,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
    "responsive_web_grok_analysis_button_from_backend": True,
    "creator_subscriptions_quote_tweet_preview_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_enhance_cards_enabled": True,
}
_SEARCH_FIELD_TOGGLES = {"withArticleRichContentState": True}


def _patch_transaction() -> None:
    from tweety import transaction as tx

    indices_regex = tx.INDICES_REGEX

    def get_indices(self, home_page_html=None):
        response = self.validate_response(home_page_html) or self.home_page_html
        filename = _find_on_demand_file(str(response))
        if filename is None:
            raise Exception("Couldn't get animation key indices")
        on_demand_file_url = (
            f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
        )
        on_demand_file_response = httpx.get(on_demand_file_url)
        key_byte_indices: list[str] = []
        for match in indices_regex.finditer(str(on_demand_file_response.text)):
            key_byte_indices.append(match.group(2))
        if not key_byte_indices:
            raise Exception("Couldn't get animation key indices")
        parsed = list(map(int, key_byte_indices))
        return parsed[0], parsed[1:]

    tx.TransactionGenerator.get_indices = get_indices


def _patch_search() -> None:
    """Migrate SearchTimeline from GET to POST.

    X changed the SearchTimeline GraphQL endpoint method around 2026-03-18.
    GET requests now return 404. The fix lives in tweety upstream as
    issue #292 but has not been released. We patch the builder's ``search``
    method to return a POST + JSON body request, and patch the http
    layer's ``perform_search`` to skip the URL-quote pre-encoding of the
    keyword (the raw string belongs in the JSON body verbatim).
    """
    from tweety.builder import UrlBuilder
    from tweety.http import Request

    def search(self, keyword, cursor, filter_):
        variables = {
            "rawQuery": str(keyword),
            "count": 20,
            "querySource": "typed_query",
            "product": "Top",
        }
        if cursor:
            variables["cursor"] = cursor
        if filter_:
            variables["product"] = filter_
        body = {
            "variables": variables,
            "features": _SEARCH_FEATURES,
            "fieldToggles": _SEARCH_FIELD_TOGGLES,
            "queryId": _SEARCH_QUERY_ID,
        }
        return {
            "method": "POST",
            "url": _SEARCH_URL,
            "params": None,
            "json": body,
            "headers": {},
        }

    UrlBuilder.search = search

    async def perform_search(self, keyword, cursor, filter_):
        if keyword.startswith("#"):
            keyword = f"#{keyword[1:]}"
        request_data = self._builder.search(keyword, cursor, filter_)
        return await self.__get_response__(**request_data)

    Request.perform_search = perform_search


def apply() -> None:
    _patch_transaction()
    _patch_search()


apply()
