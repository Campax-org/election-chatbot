# 


from transformers import pipeline


fill_mask = pipeline(model="swissbert")

# fr_CH, #it_CH #rm_CH
fill_mask.model.set_default_language("de_CH")


fill_mask("<mask> für Gleichstellungspolitik in Bern")