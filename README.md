# Run the AI Todo Assistant Github Codespace

1. Open a terminal in the project folder.
2. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   ```
3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
4. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bash
   streamlit run ui.py
   ```
6. Open the local URL shown in the terminal (usually http://localhost:8501).

If the app uses environment variables, create a `.env` file in the project root and add the required values before running.
