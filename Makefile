PYTHON=python3
SRC=./src
LEXER_TEST=./test/lexer
PARSER_TEST=./test/semantics

install:
	$(PYTHON) -m pip install --ignore-installed -r ./requirements.txt

lexer-tests:
	mkdir -p out/lexer
	for i in {1..5} ; do \
		$(PYTHON) $(SRC)/lexer.py -o out/lexer/$$i.out $(LEXER_TEST)/test$$i.c; \
	done

parser-tests:
	mkdir -p out/parser
	mkdir -p dot/pdf
	for i in {1..5} ; do \
		$(PYTHON) -Wignore $(SRC)/parser.py -o out/parser/$$i.csv $(PARSER_TEST)/test$$i.c; \
		dot -Tpdf -o dot/pdf/$$i.pdf dot/$$i.dot; \
	done

clean:
	-rm dot/{1..5}.dot
	-rm dot/pdf/{1..5}.pdf
	-rm -r out