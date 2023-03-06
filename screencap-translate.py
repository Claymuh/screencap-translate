import numpy as np
import cv2
import pytesseract
import deepl
import PIL.ImageGrab

from config import DEEPL_KEY

img = np.array(PIL.ImageGrab.grab())

coords = cv2.selectROI('select', img, False)
cv2.destroyWindow('select')

x, y, w, h = coords
roi = img[y:y+h, x:x+w]

#cv2.imshow('roi', roi)
#cv2.waitKey(0)
#cv2.destroyAllWindows()


text = pytesseract.image_to_string(roi, lang='eng')
print(text)

text_clean = text.replace('\n', ' ')


translator = deepl.Translator(DEEPL_KEY)
result = translator.translate_text(text_clean, target_lang='DE')
print(f'Translated: {result.text}')


