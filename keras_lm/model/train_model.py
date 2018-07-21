from keras.callbacks import EarlyStopping, ModelCheckpoint
import keras.backend as K
from keras.callbacks import EarlyStopping, ModelCheckpoint

import os
import numpy as np
import pickle

from keras_lm.model.language_models import build_language_model, build_fast_language_model, build_many_to_one_language_model
from keras_lm.preprocessing.batch_generators import BatchGenerator


class ModelTrainer():

    def __init__(self, model_builder, model_description, corpus):
        """

        :param model_builder:
        :param str model_description: One of ['normal', 'many_to_one', 'fast'], determines which batch generator to use
        :param corpus:
        """
        self.model_builder = model_builder
        self.corpus = corpus
        self.model_description = model_description

    def _setup_generators(self, batch_size, valid_batch_size, seq_length):
        '''
        Sets up the train/validation generators
        :return:
        '''
        train_gen = BatchGenerator(self.corpus.train, batch_size, self.model_description, modify_seq_len=True).batch_gen(seq_length)
        valid_gen = BatchGenerator(self.corpus.valid, valid_batch_size, self.model_description, modify_seq_len=True).batch_gen(seq_length)

        return train_gen, valid_gen

    def train_language_model(self, batch_size=64, eval_batch_size=10, seq_length=50, epochs=5,
                             embedding_size=300, use_gpu=True, callbacks=None):

        K.clear_session()
        num_words = len(self.corpus.word2idx) +1
        self.model = self.model_builder(num_words, embedding_size=embedding_size, use_gpu=use_gpu)
        self.model.summary()


        train_gen, valid_gen = self._setup_generators(batch_size, eval_batch_size, seq_length)

        self.model.fit_generator(train_gen,
                                 steps_per_epoch=len(self.corpus.train)//(seq_length * batch_size),
                                 epochs=epochs,
                                 validation_data=valid_gen,
                                 validation_steps=len(self.corpus.valid)//(seq_length * batch_size),
                                 callbacks=callbacks,
                                 )

        return self.model

    def evaluate_model(self, test_sentence):
        model = self.model
        model_description = self.model_description

        if self.model_description == 'fast':
            #  we need to change to a different model where the output corresponds to the one-hot encoded words
            from keras_lm.model.language_models import fast_language_model_evaluation
            model = fast_language_model_evaluation(self.model)
            model_description = 'normal'

        test_sentence = test_sentence.split()
        encoded_sentence = [self.corpus.word2idx[w] for w in test_sentence]

        for i in range(5):
            X = np.reshape(encoded_sentence, (1, len(encoded_sentence)))

            pred = model.predict(X)
            answer = np.argmax(pred, axis=2)
            encoded_sentence.append([a[0] for a in answer][-1])

            print(' '.join([corpus.idx2word[i[0]] for i in answer]))
            print(' '.join([corpus.idx2word[i] for i in encoded_sentence]))


def check_fast_model_output():
    """
    Trains the fast network a little and then prints out the predictions of the network for consistency check.
    The predictions should be between -1 and 1 (see definition of the model).
    :return:
    """
    corpus = pickle.load(open('assets/wikitext-103/wikitext-103.corpus','rb'))

    model_trainer = ModelTrainer(build_fast_language_model, 'fast', corpus)
    train_gen, valid_gen = model_trainer._setup_generators(batch_size=64, valid_batch_size=64, seq_length=50)

    model = model_trainer.model_builder(num_words=len(corpus.word2idx) +1, embedding_size=300, use_gpu=False)
    model.fit_generator(train_gen,
                        steps_per_epoch=5,
                        epochs=1,
                       )

    X, y = next(train_gen)
    predictions = model.predict(X)
    print(predictions)
    print(predictions[predictions > 1])


if __name__ == '__main__':
    os.environ["CUDA_VISIBLE_DEVICES"]="1"
    #check_fast_model_output()

    corpus = pickle.load(open('assets/wikitext-103/wikitext-103.corpus','rb'))
    model_trainer = ModelTrainer(build_fast_language_model, 'fast', corpus)
    callbacks = [EarlyStopping(patience=2),
                 ModelCheckpoint('assets/language_model.hdf5', save_weights_only=True)
                 ]

    language_model = model_trainer.train_language_model(batch_size=64, eval_batch_size = 10,
                                                        seq_length=50, epochs=1,
                                                        use_gpu=False, callbacks=callbacks)

    model_trainer.evaluate_model('i feel sick and go to the ')
