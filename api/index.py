import sys
import os

# Ensure the root directory is accessible so we can import our project modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import the Flask application instance from glavny_kod_vsego_proekta.py
# The application object is named 'shaitan_mashina_dlya_zhalob'
from glavny_kod_vsego_proekta import shaitan_mashina_dlya_zhalob as app
