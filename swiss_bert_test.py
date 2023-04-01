# 


from transformers import pipeline


fill_mask = pipeline(model="ZurichNLP/swissbert")

# fr_CH, #it_CH #rm_CH
fill_mask.model.set_default_language("de_CH")


result = fill_mask("<mask> für Gleichstellungspolitik in Bern")