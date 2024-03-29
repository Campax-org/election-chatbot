
import nlpcloud

from pandas import Series, DataFrame
import pandas as pd
import re
from nltk import tokenize

import nltk

from pprint import pprint
from decouple import config

#nltk.download('punkt')

API_KEY = config('NLP_CLOUD_API_KEY')


# What needed was experinemts
def summarize(txt, language):
    client = nlpcloud.Client("bart-large-cnn", API_KEY, gpu=False, lang=language)
    client.summarization(
        txt,
        size="small"
    )


#options for clinet fast-gpt-j, finetuned-gpt-neox-20b
#however the fined-one can be only a limited nr of models
def question(txt, language):
    client = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)
    response = client.question(txt, 
    context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
    )

    print(response)

def speak(txt, language):
    client = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)
    response = client.chatbot(txt, 
    context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
    )

    print(response)

#options for clinet gpt-j, fast-gpt-j, finetuned-gpt-neox-20b, gpt-neox-20b
def generate(txt, language):
    client = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)
    response = client.generation(txt    )

    print(response)

# This is an expensive operation
# 
def train():


    df = pd.read_csv('../data/transcript_1000.csv')

    df.sort_values(by=['MeetingDate'], ascending=False, inplace=True)

    sliced_df = df.tail(30)
    sliced_df.to_csv("sliced.csv")

    # trainling input has limited size, so we need to feed sentanece by sentence here
    # https://docs.nlpcloud.com/#gpt-j-dataset-format
    # GPT J however acceptcs the sequences of 2048 tokens
    # but again, it might be expensive to do so
    # We would suggest searching other ways, to train the model or optimize the traing
    # And in general, we're chellenging us and the community to brainstorm altenatives
    # ways to reach the goal too
    for index, row in sliced_df.iterrows():
        t = 'Text:' + row['Text'] + ' ' + 'Date: ' + str(row['StartTimeWithTimezone'])
        clean_text = re.sub(re.compile('<.*?>|\[[A-Z]*\]'), '', t.replace('\n', ' '))
        pprint(clean_text)
        f_name = 'transcript_{0}.txt'.format(index)
        with open(f_name, 'w') as f:
            f.write(clean_text)
        pprint(clean_text)

        if index == 30:

            sentences = tokenize.sent_tokenize(clean_text)

            print(len(sentences))

            client = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)
            for s in sentences:
                
                response = client.chatbot(s, 
                context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
                )
                print(response)


if __name__ == '__main__':

    qs = ["Wer engagiert sich am meisten für Gleichstellungspolitik in Bern?",
    "Wie viele Leute kann ich in Zürich für den Nationalrat wählen?",
    "Wer im Nationalrat hat immer gegen mehr Transparanz gestummen?",
    "Welcher Nationalrät*in macht am politisch wenigsten gegen den Klimawandel?",
    "Wen muss ich wählen im Kanton Graubünden damit es bei der Gleichstellungspolitik voran geht?",
    "Welcher Nationalrat*in hat gegen Sanktionen für den Iran gestimmt?"
    ]

    #train()
    #for q in qs:
    q = "Wie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?"
    question(q, "de")








