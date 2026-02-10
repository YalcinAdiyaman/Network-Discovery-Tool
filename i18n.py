"""
Internationalization (i18n) Module
Simple localization system using JSON-based language files.
"""

import json
import locale
import os
from typing import Dict, Optional, Callable, List


class I18n:
    """
    Internationalization class for loading and retrieving translations.
    
    Usage:
        i18n = I18n()
        i18n.load('tr')  # Load Turkish
        print(i18n.t('app_title'))  # Get translated string
    """
    
    SUPPORTED_LANGUAGES = ['tr', 'en']
    DEFAULT_LANGUAGE = 'en'
    
    def __init__(self, locales_dir: Optional[str] = None):
        """
        Initialize the i18n system.
        
        Args:
            locales_dir: Path to locales directory. 
                        Defaults to 'locales' in the project root.
        """
        if locales_dir is None:
            # Default to locales/ directory relative to this file (i18n.py is in project root)
            project_root = os.path.dirname(os.path.abspath(__file__))
            locales_dir = os.path.join(project_root, 'locales')
        
        self._locales_dir = locales_dir
        self._translations: Dict[str, str] = {}
        self._current_language = self.DEFAULT_LANGUAGE
        self._on_language_change_callbacks: List[Callable[[], None]] = []
        
        # Auto-detect system language and load
        detected_lang = self._detect_system_language()
        self.load(detected_lang)
    
    def _detect_system_language(self) -> str:
        """
        Detect system language from locale settings.
        
        Returns:
            Language code ('tr' or 'en')
        """
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                lang_code = system_locale.split('_')[0].lower()
                if lang_code in self.SUPPORTED_LANGUAGES:
                    return lang_code
        except Exception:
            pass
        
        return self.DEFAULT_LANGUAGE
    
    def load(self, language: str) -> bool:
        """
        Load translations for the specified language.
        
        Args:
            language: Language code ('tr' or 'en')
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if language not in self.SUPPORTED_LANGUAGES:
            print(f"[i18n] Unsupported language: {language}, falling back to {self.DEFAULT_LANGUAGE}")
            language = self.DEFAULT_LANGUAGE
        
        filepath = os.path.join(self._locales_dir, f'{language}.json')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            self._current_language = language
            print(f"[i18n] Loaded language: {language}")
            
            # Notify listeners
            for callback in self._on_language_change_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"[i18n] Callback error: {e}")
            
            return True
            
        except FileNotFoundError:
            print(f"[i18n] Language file not found: {filepath}")
            return False
        except json.JSONDecodeError as e:
            print(f"[i18n] Invalid JSON in {filepath}: {e}")
            return False
    
    def t(self, key: str, **kwargs) -> str:
        """
        Get translated string for the given key.
        
        Args:
            key: Translation key
            **kwargs: Format arguments (e.g., count=5)
            
        Returns:
            Translated string, or the key itself if not found
        """
        value = self._translations.get(key, key)
        
        # Support simple formatting like {count}
        if kwargs:
            try:
                value = value.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return value
    
    def on_language_change(self, callback: Callable[[], None]):
        """
        Register a callback to be called when language changes.
        
        Args:
            callback: Function to call (no arguments)
        """
        self._on_language_change_callbacks.append(callback)
    
    @property
    def current_language(self) -> str:
        """Get current language code."""
        return self._current_language
    
    @property
    def supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def __repr__(self) -> str:
        return f"<I18n lang='{self._current_language}' keys={len(self._translations)}>"


# Global i18n instance for convenience
_global_i18n: Optional[I18n] = None


def get_i18n() -> I18n:
    """Get the global i18n instance, creating it if needed."""
    global _global_i18n
    if _global_i18n is None:
        _global_i18n = I18n()
    return _global_i18n


def t(key: str, **kwargs) -> str:
    """
    Shortcut function to get translation from global i18n instance.
    
    Args:
        key: Translation key
        **kwargs: Format arguments
        
    Returns:
        Translated string
    """
    return get_i18n().t(key, **kwargs)
