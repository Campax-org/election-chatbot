
# About

This is the Election chat box

Scructure (folder == service | module)

- chatbot service - so far telegram bot and then more
- data storage - temp location for the data
- nlp cloud (this includes experiments with chatbot, text generation etc) 
- scraper - scraper using scrapy to scrape pariament.ch data



## Using bot

chatbot -> bot.py

Run it 

```
python3 bot.py
```

Make sure you set the variables from .env




# Draft and log


# before the training

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


