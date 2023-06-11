run:
	python main.py

install:
	pip install -r requirements.txt

pipe:
	make install
	make run
