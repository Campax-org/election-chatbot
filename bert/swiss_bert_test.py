# 

from pprint import pprint

from transformers import pipeline


fill_mask = pipeline(model="ZurichNLP/swissbert")

# fr_CH, #it_CH #rm_CH
fill_mask.model.set_default_language("de_CH")

promts = ['[Politische Partei] Im Jahr 2023 hat die <mask> massgeblich zur Abstimmung der Tamponsteuer-Initiative beigetragen.',
          '[Politiker*innen] Die <mask> ist eine der engagiertesten Politikerinnen für Gleichberechtigung und Feminismus',
          '[Politische Kampagne] Gleichstellung  ist einer der grundlegenden Werte der <mask>'
          ]


for p in promts:
    result = fill_mask(p)
    pprint("Original prompt")
    pprint(p)
    pprint("Result from Swiss BERT")
    pprint(result)

