import os
import matplotlib.pyplot as plt
from IPython.display import display, Image

def show_image(filename):
    """
    Display an image with proper path handling for both local and GitHub viewing.
    
    Args:
        filename: Image filename (without path)
    """
    # The image directory relative to this file
    img_dir = "img"
    
    # Full path to the image
    img_path = os.path.join(img_dir, filename)
    
    # Display the image
    display(Image(img_path))