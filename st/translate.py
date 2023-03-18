import deepl

def translate_text_deepl(text: str, api_key: str, target_lang='DE'):
    translator = deepl.Translator(api_key)
    result = translator.translate_text(text, target_lang=target_lang)
    return result.text


# TODO: Add functionality to get remaining API usage quota

