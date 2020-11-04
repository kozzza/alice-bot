from PIL import Image
from io import BytesIO
import requests

class Stitcher:
    def __init__(self):
        pass

    def stitch_images(self, background_url, foreground_path, target_ratio=0.4, target_x=0.85, target_y=0.2):
        response = requests.get(background_url)
        background_png = Image.open(BytesIO(response.content))
        x1, y1 = background_png.size
        
        foreground_png = Image.open(foreground_path)
        x2, y2 = foreground_png.size

        scale_factor = target_ratio/(x2/x1)
        foreground_png.thumbnail((x2*scale_factor, y2*scale_factor), Image.ANTIALIAS)
        x2, y2 = foreground_png.size

        # adjust for paste moving edge of the image instead of the center by subtracting half of the width/height as a ratio
        x_pos, y_pos = int(x1*target_x-x2/2), int(y1*target_y-y2/2)
        background_png.paste(foreground_png, (x_pos, y_pos), foreground_png)

        image_array = BytesIO()
        background_png.save(image_array, format='PNG')
        image_array.seek(0)
        return image_array
