#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Launching Gradio app..."
python app.py