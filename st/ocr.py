import pytesseract
import numpy as np
import PIL
from .image_process import preprocess_image

def ocr_text(img : np.ndarray, to_lang : str ="eng", config : str = ""):
    #img = preprocess_image(img, "edge_detect")
    result = pytesseract.image_to_string(img, lang=to_lang, config=config)
    result_clean = result.replace("\n", " ")
    return result_clean

def binarize_PIL_image(img: PIL.Image.Image) -> PIL.Image.Image:
    greyscale = img.convert('L')
    return greyscale.point(lambda x: 0 if x < 128 else 255, "1")

def get_available_ocr_languages() -> list[str]:
    langs =  pytesseract.get_languages()
    langs.remove("osd")  # osd is not actually a language
    return langs

