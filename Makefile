install:
	python -m pip install -r requirements.txt
test:
	python -m pytest tests/ -v
run:
	streamlit run web/app.py
build:
	python -m build
screenshots:
	python scripts/screenshots.py --out screenshots
