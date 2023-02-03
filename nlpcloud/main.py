
import nlpcloud

from pandas import Series, DataFrame
import pandas as pd
import re
from nltk import tokenize

import nltk
nltk.download('punkt')

API_KEY = "4329be765d81cb0c809270d9911cb3798c541fd5"


def summarize(txt, language):
    client = nlpcloud.Client("bart-large-cnn", API_KEY, gpu=False, lang=language)
    client.summarization(
        txt,
        size="small"
    )


#options for clinet fast-gpt-j, finetuned-gpt-neox-20b
#however the fined-one can be 
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


def train():
    df = pd.read_csv('../data/transcript_1000.csv')

    for index, row in df.iterrows():
        t = row['Text']
        clean_text = re.sub(re.compile('<.*?>|\[[A-Z]*\]'), '', t.replace('\n', ' '))
        print(clean_text)

        sentences = tokenize.sent_tokenize(clean_text)

        for s in sentences:
            client = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)
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

    train()
    #for q in qs:
    #    q = "Wer engagiert sich am meisten für Gleichstellungspolitik in Bern?"
    #    speak(q, "de")








