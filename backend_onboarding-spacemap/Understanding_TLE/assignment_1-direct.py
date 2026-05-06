import matplotlib.pyplot as plt
import numpy as np
from sgp4.api import accelerated
from bs4 import BeautifulSoup
import datetime
import requests






tle_data = []

data = '/tleData.html'
page = requests.get(data)
content = page.content
parsed_content = BeautifulSoup(content, 'html.parser')







print(accelerated)