.PHONY: check corpus audio clean

corpus:
	python3 scripts/build_corpus.py

check:
	python3 scripts/check_docs.py

audio:
	python3 scripts/generate_audio.py --all

clean:
	rm -rf audio/Day* recordings __pycache__ scripts/__pycache__
