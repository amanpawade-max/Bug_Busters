#!/bin/bash

# Start the FastAPI backend in the background on port 8000
uvicorn server:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit frontend on the port provided by Render
streamlit run app.py --server.port $PORT --server.address 0.0.0.0