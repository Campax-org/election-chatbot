import pandas as pd
import urllib
import xml.etree.ElementTree as ET
from scraper import *
import numpy as np


pd.set_option('display.max_columns', 50)


scrap = Scraper()
df_party = scrap.get('Party')
