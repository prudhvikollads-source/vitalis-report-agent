install:
	pip install -r requirements.txt

test:
	pytest tests/ -q

eval:
	python -m src.eval

run:
	python -m src.run

demo:
	streamlit run app/streamlit_demo.py

data:
	python scripts/generate_reports.py

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true
