import deepl

DEEPL_LANGUAGES = {
    "EN-US": "English (American)",
    "DE": "German",
    "ES": "Spanish",
    "IT": "Italian",
    "BG": "Bulgarian",
    "CS": "Czech",
    "DA": "Danish",
    "EL": "Greek",
    "EN-GB": "English (British)",
    "ET": "Estonian",
    "FI": "Finnish",
    "FR": "French",
    "HU": "Hungarian",
    "ID": "Indonesian",
    "JA": "Japanese",
    "KO": "Korean",
    "LT": "Lithuanian",
    "LV": "Latvian",
    "NB": "Norwegian (Bokmål)",
    "NL": "Dutch",
    "PL": "Polish",
    "PT-BR": "Portuguese (Brazilian)",
    "PT-PT": "Portuguese (all Portuguese varieties excluding Brazilian Portuguese)",
    "RO": "Romanian",
    "RU": "Russian",
    "SK": "Slovak",
    "SL": "Slovenian",
    "SV": "Swedish",
    "TR": "Turkish",
    "UK": "Ukrainian",
    "ZH": "Chinese (simplified)"
}


def translate_text_deepl(text: str, api_key: str, target_lang='DE'):
    translator = deepl.Translator(api_key)
    result = translator.translate_text(text, target_lang=target_lang)
    return result.text


# TODO: Add functionality to get remaining API usage quota

