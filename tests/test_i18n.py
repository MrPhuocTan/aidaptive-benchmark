"""
Test Suite 5: i18n — Internationalization
Tests for translation completeness and correctness.
"""

import pytest

from src.i18n import (
    TRANSLATIONS,
    SUPPORTED_LANGUAGES,
    translate,
    normalize_lang,
    get_client_translations,
)


class TestTranslationCompleteness:
    """Ensure all languages have the same keys"""

    def test_all_languages_present(self):
        """TC-I01: All supported languages should have translations"""
        for lang in SUPPORTED_LANGUAGES:
            assert lang in TRANSLATIONS, f"Missing translations for '{lang}'"

    def test_key_parity_vi(self):
        """TC-I02: Vietnamese should have all English keys"""
        en_keys = set(TRANSLATIONS["en"].keys())
        vi_keys = set(TRANSLATIONS["vi"].keys())
        missing = en_keys - vi_keys
        assert len(missing) == 0, f"VI missing keys: {missing}"

    def test_key_parity_zh(self):
        """TC-I03: Chinese should have all English keys"""
        en_keys = set(TRANSLATIONS["en"].keys())
        zh_keys = set(TRANSLATIONS["zh"].keys())
        missing = en_keys - zh_keys
        assert len(missing) == 0, f"ZH missing keys: {missing}"

    def test_no_extra_keys_vi(self):
        """TC-I04: Vietnamese should not have keys that English doesn't"""
        en_keys = set(TRANSLATIONS["en"].keys())
        vi_keys = set(TRANSLATIONS["vi"].keys())
        extra = vi_keys - en_keys
        assert len(extra) == 0, f"VI has extra keys: {extra}"

    def test_no_extra_keys_zh(self):
        """TC-I05: Chinese should not have keys that English doesn't"""
        en_keys = set(TRANSLATIONS["en"].keys())
        zh_keys = set(TRANSLATIONS["zh"].keys())
        extra = zh_keys - en_keys
        assert len(extra) == 0, f"ZH has extra keys: {extra}"


class TestTranslateFunction:
    """Test the translate() helper"""

    def test_english_lookup(self):
        """TC-I06: English translation lookup"""
        result = translate("en", "nav.dashboard")
        assert result == "Dashboard"

    def test_vietnamese_lookup(self):
        """TC-I07: Vietnamese translation lookup"""
        result = translate("vi", "nav.dashboard")
        assert result == "Tổng quan"

    def test_chinese_lookup(self):
        """TC-I08: Chinese translation lookup"""
        result = translate("zh", "nav.dashboard")
        assert result == "总览"

    def test_missing_key_returns_key(self):
        """TC-I09: Missing key should return the key itself"""
        result = translate("en", "nonexistent.key.foobar")
        assert result == "nonexistent.key.foobar"

    def test_unknown_lang_falls_back_to_english(self):
        """TC-I10: Unknown language should fall back to English"""
        result = translate("fr", "nav.dashboard")
        assert result == "Dashboard"

    def test_format_kwargs(self):
        """TC-I11: Format placeholders in translations"""
        result = translate("en", "api.discovery_failed", error="timeout")
        assert "timeout" in result

    def test_format_kwargs_bad_key_safe(self):
        """TC-I12: Bad format kwargs should not crash"""
        result = translate("en", "nav.dashboard", nonexistent="value")
        assert result == "Dashboard"


class TestNormalizeLang:
    """Test normalize_lang()"""

    def test_exact_match(self):
        """TC-I13: Exact language codes"""
        assert normalize_lang("en") == "en"
        assert normalize_lang("vi") == "vi"
        assert normalize_lang("zh") == "zh"

    def test_prefix_match(self):
        """TC-I14: Language code prefixes"""
        assert normalize_lang("en-US") == "en"
        assert normalize_lang("vi-VN") == "vi"
        assert normalize_lang("zh-CN") == "zh"

    def test_case_insensitive(self):
        """TC-I15: Case insensitive"""
        assert normalize_lang("EN") == "en"
        assert normalize_lang("Vi") == "vi"

    def test_none_defaults_to_en(self):
        """TC-I16: None defaults to English"""
        assert normalize_lang(None) == "en"

    def test_empty_defaults_to_en(self):
        """TC-I17: Empty string defaults to English"""
        assert normalize_lang("") == "en"

    def test_unknown_defaults_to_en(self):
        """TC-I18: Unknown language defaults to English"""
        assert normalize_lang("kr") == "en"


class TestGetClientTranslations:
    """Test get_client_translations()"""

    def test_returns_js_keys(self):
        """TC-I19: Should include js.* keys"""
        result = get_client_translations("en")
        js_keys = [k for k in result if k.startswith("js.")]
        assert len(js_keys) > 0

    def test_returns_common_keys(self):
        """TC-I20: Should include common.* keys"""
        result = get_client_translations("en")
        common_keys = [k for k in result if k.startswith("common.")]
        assert len(common_keys) > 0

    def test_excludes_nav_keys(self):
        """TC-I21: Should not include nav.* or dashboard.* keys"""
        result = get_client_translations("en")
        nav_keys = [k for k in result if k.startswith("nav.")]
        assert len(nav_keys) == 0

    def test_respects_language(self):
        """TC-I22: Should return translated values for specified language"""
        en = get_client_translations("en")
        vi = get_client_translations("vi")
        # js.starting should differ between EN and VI
        assert en.get("js.starting") == "Starting..."
        assert vi.get("js.starting") == "Đang bắt đầu..."
