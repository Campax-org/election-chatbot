# 
import pandas as pd


#from transformers import pipeline
import re
from nltk import tokenize

import nltk

from pprint import pprint
from decouple import config


##fill_mask = pipeline(model="ZurichNLP/swissbert")

# fr_CH, #it_CH #rm_CH
# fill_mask.model.set_default_language("de_CH")


#result = fill_mask("<mask> für Gleichstellungspolitik in Bern")

def train():

    df = pd.read_csv('../data/transcript_1000.csv')

    df.sort_values(by=['MeetingDate'], ascending=False, inplace=True)

    sliced_df = df.tail(30)
    sliced_df.to_csv("sliced.csv")

    for index, row in sliced_df.iterrows():
        t = 'Text:' + row['Text'] + ' ' + 'Date: ' + str(row['StartTimeWithTimezone'])
        clean_text = re.sub(re.compile('<.*?>|\[[A-Z]*\]'), '', t.replace('\n', ' '))
        pprint(clean_text)
        #f_name = 'transcript_{0}.txt'.format(index)
        #with open(f_name, 'w') as f:
        #    f.write(clean_text)
        pprint(clean_text)

        sentences = tokenize.sent_tokenize(clean_text)

        print(len(sentences))
        for s in sentences:
            print(s)

train()