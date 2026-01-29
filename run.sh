#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the Flask app
echo "Starting NCKH Job Matching System..."
python app.py
