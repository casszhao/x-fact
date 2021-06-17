# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" XNLI utils (dataset loading and evaluation) """


import logging
import os
import csv
import random
import tqdm
import json
import glob
from filelock import FileLock
from dataclasses import dataclass
from typing import List, Optional
from transformers import PreTrainedTokenizer

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class InputExample:
    """
    A single training/test example for multiple choice

    Args:
        example_id: Unique id for the example.
        question: string. The untokenized text of the second sequence (question).
        contexts: list of str. The untokenized text of the first sequence (context of corresponding question).
        endings: list of str. multiple choice's options. Its length must be equal to contexts' length.
        label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """

    example_id: str
    question: str
    contexts: List[str]
    label: Optional[str]


def get_metadata(line):
    claimant = line[-3].strip()
    review_date = line[-4].strip()
    language = line[0].strip()
    site = line[1].strip()
    claim_date = line[-5].strip()

    s = 'language : ' + str(language) + ', site : ' + str(site) + ', claimant : ' + str(claimant) + ', claim_date : ' + str(claim_date) + ', review_date: ' + str(review_date)
    return s


@dataclass(frozen=True)
class InputFeatures:
    """
    A single set of features of data.
    Property names are the same names as the corresponding inputs to a model.
    """

    example_id: str
    input_ids: List[List[int]]
    attention_mask: Optional[List[List[int]]]
    token_type_ids: Optional[List[List[int]]]
    label: Optional[int]



class DataProcessor:
    """Base class for data converters for multiple choice data sets."""

    def get_train_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the train set."""
        raise NotImplementedError()

    def get_dev_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the dev set."""
        raise NotImplementedError()

    def get_test_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the test set."""
        raise NotImplementedError()

    def get_labels(self):
        """Gets the list of labels for this data set."""
        raise NotImplementedError()

    @classmethod
    def _read_tsv(cls, input_file, quotechar=None):
        """Reads a tab separated value file."""
        print('Loading from file ', input_file)
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(csv.reader(f, delimiter="\t", quotechar=quotechar))




class XFactEvidenceProcessor(DataProcessor):
    """Processor for the XFACT dataset.
    Adapted from https://github.com/google-research/bert/blob/f39e881b169b9d53bea03d2d341b31707a6c052b/run_classifier.py#L207"""

    def __init__(self, sources=None, num_evidences=3, use_metadata=False, data_dir=None):
        self.sources = sources
        self.label_sets = {}
        self.label_count = {}
        self.num_evidences = num_evidences
        self.use_metadata = use_metadata
        if data_dir is not None:
            for source in self.sources:
                self.get_train_examples(data_dir, source, create_label_set=True)
        print('Label counts are : ')
        print(self.label_count)
        self.sort_label_set()

    def get_train_examples(self, data_dir, source, create_label_set=False):
        """See base class."""


        print('Loading from file train.{}.tsv'.format(source))
        examples = []
        if source not in self.label_sets:
            self.label_sets[source] = set()
            self.label_count[source] = {}
        lines = self._read_tsv(os.path.join(data_dir, "train.{}.tsv".format(source)))
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % ("train", i)
            if len(line) == 0:
                continue
            evidences, claim_text, label, metadata = self.create_example(line)
            if create_label_set:
                self.label_sets[source].add(label)
            else:
                if label not in self.label_sets[source]:
                    raise ValueError('Label {} not found in set {}'.format(label, str(self.label_sets[source])))
            if label not in self.label_count[source]:
                self.label_count[source][label] = 0
            self.label_count[source][label] +=1
            assert isinstance(claim_text, str) and  isinstance(label, str)
            if self.use_metadata:
                claim_text = claim_text + ' ' + metadata
            example = InputExample(
                        example_id=guid,
                        question=claim_text,
                        contexts=evidences,
                        label=label
                    )
            examples.append(example)
        print('Examples loaded from source {} : {}'.format(source, len(examples)))

        random.shuffle(examples)
        print(examples[:5])
        #return examples[:5000]
        return examples

    def create_example(self, line):

        evidences = []
        for i in range(self.num_evidences):
            evidences.append(line[2+i])

        claim_text = line[-2]
        label = line[-1].lower()
        metadata = get_metadata(line)
        return evidences, claim_text, label, metadata

    def get_dev_examples(self, data_dir, source, filename=None):
        """See base class."""

        examples = []
        examples_skipped = 0
        if filename is None:
            lines = self._read_tsv(os.path.join(data_dir, "dev.{}.tsv".format(source)))
        else:
            #source = ''
            lines = self._read_tsv(os.path.join(data_dir, filename))
        #lines = self._read_tsv(os.path.join(data_dir, "train.{}.tsv".format(source)))
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % ("train", i)
            if len(line) == 0:
                continue
            evidences, claim_text, label, metadata  = self.create_example(line)
            if label not in self.label_sets[source]:
                #print('Skipping test example')
                examples_skipped +=1
                continue
            assert isinstance(claim_text, str) and  isinstance(label, str)

            if self.use_metadata:
                claim_text = claim_text + ' ' + metadata
            example = InputExample(
                        example_id=guid,
                        question=claim_text,
                        contexts=evidences,
                        label=label
                    )
            examples.append(example)
        if filename is None:
            print('For source: {}, dev examples skipped: {}, Examples left: {}'.format(source, examples_skipped, len(examples)))
        else:
            print('For {} examples skipped: {}, Examples left: {}'.format(filename, examples_skipped, len(examples)))
        return examples

    def sort_label_set(self):
        sorted_sets = {}

        for key, val in self.label_sets.items():
            sorted_sets[key] = sorted(list(val))

        self.label_sets = sorted_sets

    def get_test_examples(self, data_dir, source):
        """See base class."""

        examples = []
        examples_skipped = 0
        lines = self._read_tsv(os.path.join(data_dir, "test.{}.tsv".format(source)))
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % ("train", i)
            if len(line) == 0:
                continue
            evidences, claim_text, label, metadata  = self.create_example(line)
            if label not in self.label_sets[source]:
                #print('Skipping test example')
                examples_skipped +=1
                continue
            assert isinstance(claim_text, str) and  isinstance(label, str)
            if self.use_metadata:
                claim_text = claim_text + ' ' + metadata
            example = InputExample(
                        example_id=guid,
                        question=claim_text,
                        contexts=evidences,
                        label=label
                    )
            examples.append(example)
        print('For source: {}, test examples skipped: {}, Examples left: {}'.format(source, examples_skipped, len(examples)))
        return examples

    def get_labels(self):
        """See base class."""
        self.sort_label_set()
        return self.label_sets


def xfact_evidence_convert_examples_to_features(
    examples: List[InputExample], label_list: List[str], max_length: int, tokenizer: PreTrainedTokenizer,
) -> List[InputFeatures]:
    """
    Loads a data file into a list of `InputFeatures`
    """

    label_map = {label: i for i, label in enumerate(label_list)}

    features = []
    for (ex_index, example) in tqdm.tqdm(enumerate(examples), desc="convert examples to features"):
        if ex_index % 10000 == 0:
            logger.info("Writing example %d of %d" % (ex_index, len(examples)))
        choices_inputs = []
        for ending_idx, context in enumerate(example.contexts):
            #text_a = context
            #text_b = example.question
            text_a = example.question
            text_b = context

            inputs = tokenizer(
                text_a,
                text_b,
                add_special_tokens=True,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_overflowing_tokens=True,
            )
            if "num_truncated_tokens" in inputs and inputs["num_truncated_tokens"] > 0:
                logger.info(
                    "Attention! you are cropping tokens (swag task is ok). "
                    "If you are training ARC and RACE and you are poping question + options,"
                    "you need to try to use a bigger max seq length!"
                )

            choices_inputs.append(inputs)

        label = label_map[example.label]

        input_ids = [x["input_ids"] for x in choices_inputs]
        attention_mask = (
            [x["attention_mask"] for x in choices_inputs] if "attention_mask" in choices_inputs[0] else None
        )
        token_type_ids = (
            [x["token_type_ids"] for x in choices_inputs] if "token_type_ids" in choices_inputs[0] else None
        )


        features.append(
            InputFeatures(
                example_id=example.example_id,
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                label=label,
            )
        )

    for f in features[:2]:
        logger.info("*** Example ***")
        logger.info("feature: %s" % f)

    return features

def xfact_claim_evidence_convert_examples_to_features(
    examples: List[InputExample], label_list: List[str], max_length: int, tokenizer: PreTrainedTokenizer,
) -> List[InputFeatures]:
    """
    Loads a data file into a list of `InputFeatures`
    """

    label_map = {label: i for i, label in enumerate(label_list)}

    features = []
    for (ex_index, example) in tqdm.tqdm(enumerate(examples), desc="convert examples to features"):
        if ex_index % 10000 == 0:
            logger.info("Writing example %d of %d" % (ex_index, len(examples)))
        claim = example.question
        claim_inputs = tokenizer(
                 claim,
                None,
                add_special_tokens=True,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_overflowing_tokens=True,
            )
        if "num_truncated_tokens" in claim_inputs and claim_inputs["num_truncated_tokens"] > 0:
            logger.info(
                "Attention! you are cropping tokens (swag task is ok). "
                "If you are training ARC and RACE and you are poping question + options,"
                "you need to try to use a bigger max seq length!"
            )

        choices_inputs = []
        choices_inputs.append(claim_inputs)

        for ending_idx, context in enumerate(example.contexts):
            #text_a = context
            #text_b = example.question
            text_a = example.question
            text_b = context

            inputs = tokenizer(
                text_b,
                None,
                add_special_tokens=True,
                max_length=max_length,
                padding="max_length",
                truncation=True,
                return_overflowing_tokens=True,
            )
            if "num_truncated_tokens" in inputs and inputs["num_truncated_tokens"] > 0:
                logger.info(
                    "Attention! you are cropping tokens (swag task is ok). "
                    "If you are training ARC and RACE and you are poping question + options,"
                    "you need to try to use a bigger max seq length!"
                )

            choices_inputs.append(inputs)

        label = label_map[example.label]

        input_ids = [x["input_ids"] for x in choices_inputs]
        attention_mask = (
            [x["attention_mask"] for x in choices_inputs] if "attention_mask" in choices_inputs[0] else None
        )
        token_type_ids = (
            [x["token_type_ids"] for x in choices_inputs] if "token_type_ids" in choices_inputs[0] else None
        )


        features.append(
            InputFeatures(
                example_id=example.example_id,
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                label=label,
            )
        )

    for f in features[:2]:
        logger.info("*** Example ***")
        logger.info("feature: %s" % f)

    return features



xfact_evidence_processors = {
    "xfact_evidence": XFactEvidenceProcessor,
}

xfact_evidence_output_modes = {
    "xfact_evidence": "classification",
}

#xnli_tasks_num_labels = {
#    "xnli": 3,
#}
