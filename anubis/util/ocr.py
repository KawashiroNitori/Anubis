import io
import pyocr
from PIL import Image


_tool = pyocr.get_available_tools()[0]


def recognize_digits(bin_image: bytes):
    global _tool
    try:
        image = Image.open(io.BytesIO(bin_image))
        result = _tool.image_to_string(image, lang='eng', builder=pyocr.tesseract.DigitBuilder())
    except:
        return None
    return result
