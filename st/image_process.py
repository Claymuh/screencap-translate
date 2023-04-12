import cv2
import numpy as np
from skimage.metrics import structural_similarity
from typing import Literal


def preprocess_image(image: np.ndarray, mode: str = 'edge_detect') -> np.ndarray:
    grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(grayscale, (5, 5), 0)
    if mode == 'edge_detect':
        return cv2.Canny(blurred, 50, 150)
    elif mode == 'adaptive_thresholding':
        return cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 15)

def get_image_similarity(img1: np.ndarray, img2: np.ndarray, method:Literal["ncc", "ssi"]="ncc") -> float:
    if method == "ncc":
        return cv2.matchTemplate(img1, img2, cv2.TM_CCORR_NORMED)[0][0]
    elif method == "ssi":
        return structural_similarity(img1, img2)
    else:
        raise ValueError("method parameter needs to be 'ncc' or 'ssi")

def are_images_similar(img1: np.ndarray, img2: np.ndarray, threshold: float, method: Literal["ncc", "ssi"]="ncc") -> bool:
    return get_image_similarity(img1, img2, method) > threshold

