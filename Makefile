PYTHON=python3
SRC=./src
TEST=./test

install:
	$(PYTHON) -m pip install --ignore-installed -r ./requirements.txt

tests:
	mkdir -p out
	for i in {1..5} ; do \
		$(PYTHON) $(SRC)/lexer.py -o out/$$i.out $(TEST)/test$$i.c; \
	done

clean:
	rm -r out