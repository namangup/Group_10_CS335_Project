PYTHON=python3
SRC=./src
LEXER_TEST=./test/lexer
PARSER_TEST=./test/parser

install:
	$(PYTHON) -m pip install --ignore-installed -r ./requirements.txt

lexer-tests:
	mkdir -p out/lexer
	for i in {1..5} ; do \
		$(PYTHON) $(SRC)/lexer.py -o out/lexer/$$i.out $(LEXER_TEST)/test$$i.c; \
	done

parser-tests:
	mkdir -p out/parser
	for i in {1..5} ; do \
		$(PYTHON) -Wignore $(SRC)/parser.py -o out/parser/$$i.out $(PARSER_TEST)/test$$i.c; \
	done

clean:
	rm -r out