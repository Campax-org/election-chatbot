

![Swiss Election Bot Campax](https://campax.org/wp-content/uploads/2022/09/cropped-campax_logo-1.png "Swiss Election Bot Campax").
# About


This is the Election chat box

Scructure (folder == service | module)

- chatbot service - so far telegram bot and then more
- data storage - temp location for the data
- nlp cloud (this includes experiments with chatbot, text generation etc) 
- scraper - scraper using scrapy to scrape pariament.ch data


Deployed as telegram chatbot [here](https://t.me/CampaxElectionBot)

## Using Telegram bot

Run it 

```
cd chatbot
python3 bot.py
```

Make sure you set the variables from .env
and then:
commands and respective handlers:
**vote** - reads the votes from the scraped data 
**parl** - send request

Within the telegram bot the commands are

`/parl YOUR QUERY`
`/vote NAME OF THE POLITICIAL`


## Using scraper

For examples - you can relate to:

```/scraper/Collect_data_for_Elections.ipynb```
```/scraper/README.md```

The basic approach would be
```
scrap = Scraper()
df_party = scrap.get('ENTITY NAME')
#or
df_transcript_count = scrap.count('Transcript')
```

Where ENTITY NAME is taken from [here](https://ws.parlament.ch/odata.svc/)
Name of the **collection**

see or run ```pythin3 craper/test_scraper.py```
It will save data to the data directory
With this data we then can decide - how do we make use of it to contrinute to make the chatbot smarter.


### NLP cloud
In this section we find the scripts we used to train, test and use the nlpcloud.com library
We tried "summarize" "question" and "text appeoaches

The bot script uses **finetuned-gpt-neox-20b** model - and the method called "chatbot"

See ```/nlpcloud/main.py -> def speak()``` method

Actually you can refer to [NLP cloud documentation](https://docs.nlpcloud.com/#introduction). It's quite good and exensive.


Good luck with the challenge!


# Challenge progess https://bd.hack4socialgood.ch/

1. [Make progress] Swiss BERT model https://vamvas.ch/introducing-swissbert
Things to be
- Build it up - Done
- Test it - Done
- Augment / Train with data - Partially Done / TBD

2. [To research] Next - generate questions for the scraped data -> Build an index


Notes:
- https://www.aicrowd.com/ - try to file a challenge



# Notes

```
!pip install pytorch-pretrained-bert
import pytorch_pretrained_bert as ppb
assert 'bert-large-cased' in ppb.modeling.PRETRAINED_MODEL_ARCHIVE_MAP
```


# Swiss BERT
```
'Original prompt'
('[Politische Partei] Im Jahr 2023 hat die <mask> massgeblich zur Abstimmung '
 'der Tamponsteuer-Initiative beigetragen.')
'Result from Swiss BERT'
[{'score': 0.3236805200576782,
  'sequence': 'Politische Partei Im Jahr 2023 hat die SVP massgeblich zur '
              'Abstimmung der Tamponsteuer-Initiative beigetragen.',
  'token': 741,
  'token_str': 'SVP'},
 {'score': 0.25119855999946594,
  'sequence': 'Politische Partei Im Jahr 2023 hat die SP massgeblich zur '
              'Abstimmung der Tamponsteuer-Initiative beigetragen.',
  'token': 1017,
  'token_str': 'SP'},
 {'score': 0.15169617533683777,
  'sequence': 'Politische Partei Im Jahr 2023 hat die Partei massgeblich zur '
              'Abstimmung der Tamponsteuer-Initiative beigetragen.',
  'token': 1028,
  'token_str': 'Partei'},
 {'score': 0.04907562583684921,
  'sequence': 'Politische Partei Im Jahr 2023 hat die GLP massgeblich zur '
              'Abstimmung der Tamponsteuer-Initiative beigetragen.',
  'token': 12794,
  'token_str': 'GLP'},
 {'score': 0.04162818193435669,
  'sequence': 'Politische Partei Im Jahr 2023 hat die Jungpartei massgeblich '
              'zur Abstimmung der Tamponsteuer-Initiative beigetragen.',
  'token': 46706,
  'token_str': 'Jungpartei'}]
'Original prompt'
('[Politikerin] Die <mask> ist eine der engagiertesten Politikerinnen für '
 'Gleichberechtigung und Feminismus')
'Result from Swiss BERT'
[{'score': 0.33690086007118225,
  'sequence': 'Politikerin Die Autorin ist eine der engagiertesten '
              'Politikerinnen für Gleichberechtigung und Feminismus',
  'token': 15310,
  'token_str': 'Autorin'},
 {'score': 0.21666944026947021,
  'sequence': 'Politikerin Die Schweizerin ist eine der engagiertesten '
              'Politikerinnen für Gleichberechtigung und Feminismus',
  'token': 14039,
  'token_str': 'Schweizerin'},
 {'score': 0.06902963668107986,
  'sequence': 'Politikerin Die Frau ist eine der engagiertesten Politikerinnen '
              'für Gleichberechtigung und Feminismus',
  'token': 622,
  'token_str': 'Frau'},
 {'score': 0.06879016757011414,
  'sequence': 'Politikerin Die Nationalrätin ist eine der engagiertesten '
              'Politikerinnen für Gleichberechtigung und Feminismus',
  'token': 20190,
  'token_str': 'Nationalrätin'},
 {'score': 0.03002847544848919,
  'sequence': 'Politikerin Die Deutsche ist eine der engagiertesten '
              'Politikerinnen für Gleichberechtigung und Feminismus',
  'token': 3748,
  'token_str': 'Deutsche'}]
'Original prompt'
('[Politische Kampagne] Gleichstellung  ist einer der grundlegenden Werte der '
 '<mask>')
'Result from Swiss BERT'
[{'score': 0.24675796926021576,
  'sequence': 'Politische Kampagne Gleichstellung ist einer der grundlegenden '
              'Werte der Frau',
  'token': 622,
  'token_str': 'Frau'},
 {'score': 0.18075180053710938,
  'sequence': 'Politische Kampagne Gleichstellung ist einer der grundlegenden '
              'Werte der Gesellschaft',
  'token': 2153,
  'token_str': 'Gesellschaft'},
 {'score': 0.16865766048431396,
  'sequence': 'Politische Kampagne Gleichstellung ist einer der grundlegenden '
              'Werte der Schweiz',
  'token': 214,
  'token_str': 'Schweiz'},
 {'score': 0.0794895812869072,
  'sequence': 'Politische Kampagne Gleichstellung ist einer der grundlegenden '
              'Werte der Frauen',
  'token': 573,
  'token_str': 'Frauen'},
 {'score': 0.05319949984550476,
  'sequence': 'Politische Kampagne Gleichstellung ist einer der grundlegenden '
              'Werte der Schweizerinnen',
  'token': 11577,
  'token_str': 'Schweizerinnen'}]
```



# NLP before the training

Input:

transcript_76


Question:
L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires

Speak:
{'input': "L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires", 'response': "Oui, le Conseil fédéral soutient les efforts de l'Association Exposition nationale pour organiser des élections parlementaires dans les cantons et les villes. Les fonds supplémentaires demandés par l'Association Exposition nationale serviront à financer les élections et à fournir des informations aux électeurs."}]

Generate:
"L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires pour étendre leur rayonnement et renforcer leurs


# after the training

Speak

C'est très intéressant! Il est important que le Conseil fédéral soutienne ces démarches afin de garantir que les élections parlementaires se déroulent sans incident et dans le respect des règles démocratiques. Nous devons veiller à ce que le processus de vote soit sûr et sécurisé pour assurer la participation équitable de tous les citoyens.


Generate
L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires pour l’association au cours des deux prochaines ann

L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires pour permettre à l’exposition de se dérouler d


L'Association Exposition nationale est en discussion, et le Conseil fédéral soutient ses démarches, avec des cantons et des villes pour obtenir des montants supplémentaires pour ses mérites et contribuer à la préservation




# now a free form question

{'answer': 'An der Expo 2002 in der Schweiz wirkten zahlreiche Länder mit, darunter Deutschland, Frankreich, Italien, Spanien, Österreich, die Niederlande, das Vereinigte Königreich, Polen, die USA, China, Indien, Japan, Mexiko, Südkorea und Dänemark. Außerdem waren einige Unternehmen und Organisationen wie Microsoft, Unicef, Remax und Nestle anwesend.', 'score': 1, 'start': 0, 'end': 0}
➜  nlpcloud git:(vladimi/nlp-extra) ✗ python3 main.py
{'response': 'Die Schweizer Regierung hat an der Expo 2002 in der Schweiz mitgewirkt. Zu den Teilnehmern gehörten der Schweizer Bundesrat, der Schweizer Parlamentarische Rat, der Schweizer Bundesrat für Auswärtige Angelegenheiten und der Schweizer Parlamentsausschuss für Wirtschaft und Abgaben.', 'history': [{'input': 'Wer hat an der Expo 2002 in der Schweiz mitgewirkt?', 'response': 'Die Schweizer Regierung hat an der Expo 2002 in der Schweiz mitgewirkt. Zu den Teilnehmern gehörten der Schweizer Bundesrat, der Schweizer Parlamentarische Rat, der Schweizer Bundesrat für Auswärtige Angelegenheiten und der Schweizer Parlamentsausschuss für Wirtschaft und Abgaben.'}]}
➜  nlpcloud git:(vladimi/nlp-extra) ✗ python3 main.py
{'generated_text': 'Wer hat an der Expo 2002 in der Schweiz mitgewirkt?\n\nAn der EXPO 2002 in der Schweiz beteiligten sich unter anderem: \n \n• Internationale Organisationen wie die W', 'nb_generated_tokens': 65, 'nb_input_tokens': 28}



BEFORE traning

{'response': 'Laut parlament.ch stimmten die Parteien CVP, FDP, SVP und die Grünen für das Budget der Expo 2002.', 'history': [{'input': 'Welche Partei hat für das Budget der Expo 2002 gestimmt?', 'response': 'Laut parlament.ch stimmten die Parteien CVP, FDP, SVP und die Grünen für das Budget der Expo 2002.'}]}

after traninig
{'response': 'Die Schweizerische Volkspartei (SVP) hat für das Budget der Expo 2002 gestimmt.', 'history': [{'input': 'Welche Partei hat für das Budget der Expo 2002 gestimmt?', 'response': 'Die Schweizerische Volkspartei (SVP) hat für das Budget der Expo 2002 gestimmt.'}]}

OR

{'response': 'Die Partei, die für das Budget der Expo 2002 gestimmt hat, war die Schweizerische Volkspartei (SVP).', 'history': [{'input': 'Welche Partei hat für das Budget der Expo 2002 gestimmt?', 'response': 'Die Partei, die für das Budget der Expo 2002 gestimmt hat, war die Schweizerische Volkspartei (SVP).'}]}


Transcript 30:




Before training:

q = "Wie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?"


Question (model)
Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica betrug im Jahr 1999 CHF 2.450.000.

Speak (model)
ie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?', 'response': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 2,3 Millionen Franken


After training:

Speak (model)

{'response': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 2,2 Millionen Franken.', 'history': [{'input': 'Wie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?', 'response': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 2,2 Millionen Franken.'}]}

[{'input': 'Wie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?', 'response': 'Im Jahr 1999 beantragte der Bundesrat einen Kredit von CHF 6,5 Millionen für die Stiftung Pro Helvetica.'}]}
➜  nlpcloud git:(vladimi/nlp-extra) ✗ python3 main.py
{'response': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 6 Millionen Schweizer Franken.', 'history': [{'input': 'Wie hoch war der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999?', 'response': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 6 Millionen Schweizer Franken.'}]}

Question (model)

➜  nlpcloud git:(vladimi/nlp-extra) ✗ python3 main.py
{'answer': 'Der Bundesrat beantragte im Jahr 1999 einen Kredit in Höhe von CHF 10 Millionen für die Stiftung Pro Helvetica.', 'score': 1, 'start': 0, 'end': 0}
➜  nlpcloud git:(vladimi/nlp-extra) ✗ python3 main.py
{'answer': 'Der vom Bundesrat beantragte Kredit für die Stiftung Pro Helvetica im Jahr 1999 betrug 47,5 Millionen Schweizer Franken.', 'score': 1, 'start': 0, 'end': 0}


