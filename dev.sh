#!/bin/bash

source venv/bin/activate
uvicorn src.main:app --reload --port 8000