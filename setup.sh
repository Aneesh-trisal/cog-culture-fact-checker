#!/bin/bash
echo "Setting up spaCy model..."
python -m spacy download en_core_web_sm --quiet || true
echo "Setup completed."
