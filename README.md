# Trading Agent — Using FastAPI and Streamlit

Run the FastAPI server (from the project root):

```bash
uvicorn app.interfaces.api:app --reload --port 8000
```

Run the Streamlit app (in another terminal, from project root):

```bash
streamlit run app/interfaces/streamlit_app.py
```