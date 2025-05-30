import email
import spacy
import re
from typing import Dict

nlp = spacy.load("en_core_web_sm")

def extract_caption_features(text):
    doc = nlp(text.lower())
    
    objects = set()
    attributes = set()
    relations = set()
    in_image_text = set()
    numbers = set()

    for token in doc:
        if token.pos_ == "NOUN":
            objects.add(token.lemma_)
        elif token.pos_ == "ADJ":
            attributes.add(token.lemma_)
        elif token.pos_ == "NUM":
            numbers.add(token.text)

    # Extract (object, attribute) pairs
    for chunk in doc.noun_chunks:
        noun = chunk.root.lemma_
        for tok in chunk:
            if tok.pos_ == "ADJ":
                attributes.add(tok.lemma_)
                relations.add((tok.lemma_, noun))  # attribute-object

    # Extract object relations via prepositions
    for tok in doc:
        if tok.dep_ == "prep" and tok.head.pos_ == "VERB":
            pobj = [c.lemma_ for c in tok.children if c.pos_ == "NOUN"]
            if pobj:
                relations.add((tok.head.lemma_, tok.lemma_, pobj[0]))  # verb-prep-object

    # Extract in-image text (e.g., "stop", "$5.99")
    quoted = re.findall(r'["“”‘’\'](.*?)["“”‘’\']', text)
    in_image_text.update(quoted)
    in_image_text.update(re.findall(r'\$\d+(\.\d{1,2})?', text))  # match $3.99 style

    return {
        "objects": objects,
        "attributes": attributes,
        "relations": relations,
        "numbers": numbers,
        "in_image_text": in_image_text
    }

def feature_coverage(gt_text, cand_text):
    gt_feats = extract_caption_features(gt_text)
    cand_feats = extract_caption_features(cand_text)

    scores = {}
    missing = {}
    total_gt = 0
    total_matched = 0

    for key in gt_feats:
        gt_set = gt_feats[key]
        cand_set = cand_feats[key]
        match = gt_set & cand_set
        gt_count = len(gt_set)
        match_count = len(match)

        scores[key] = match_count / gt_count if gt_count else 1.0
        missing[key] = gt_set - cand_set

        total_gt += gt_count
        total_matched += match_count

    overall = total_matched / total_gt if total_gt > 0 else 1.0
    return scores, overall, missing


# gt = """A red vintage car with a number plate 'XJ128' is parked beside a blue truck. 
# The car has a shiny chrome bumper and a worn-out leather seat inside. Price tag reads '$12,500'."""

# cand = """A vintage car is parked near a truck. The car is shiny and has leather seats."""

# scores, overall_score, missing = feature_coverage(gt, cand)
# print("Per-category scores:", scores)
# print("Overall coverage:", overall_score)
# print("Missing details:", missing)

def compute_score(predict: str, ground_truth: str) -> Dict[str, float]:
    predict, ground_truth = predict.lower(), ground_truth.lower()
    detail_score, overall_score, missing = feature_coverage(ground_truth, predict)
    return {
        "overall": overall_score,
        "detail_score": detail_score,
        "missing_details": missing
    }

