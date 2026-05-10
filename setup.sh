#!/bin/bash
# Pre-download spaCy model to avoid build issues
python -m spacy download en_core_web_sm --quiet || true
