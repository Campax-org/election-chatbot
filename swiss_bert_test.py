import tensorflow as tf

cifar = tf.keras.datasets.cifar100
(x_train, y_train), (x_test, y_test) = cifar.load_data()
model = tf.keras.applications.ResNet50(
    include_top=True,
    weights=None,
    input_shape=(32, 32, 3),
    classes=100,)

loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(optimizer="adam", loss=loss_fn, metrics=["accuracy"])
model.fit(x_train, y_train, epochs=5, batch_size=64)


# from transformers import pipeline


# fill_mask = pipeline(model="ZurichNLP/swissbert")

# # fr_CH, #it_CH #rm_CH
# fill_mask.model.set_default_language("de_CH")
# fill_mask("Der schönste Kanton der Schweiz ist <mask>.")