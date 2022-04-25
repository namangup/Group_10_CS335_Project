PYTHON=python3
SRC=./src
LEXER_TEST=./test/lexer
PARSER_TEST=./test/semantics
FINAL_TEST=./tests/final

install:
	$(PYTHON) -m pip install --ignore-installed -r ./requirements.txt

lexer-tests:
	mkdir -p out/lexer
	for i in {1..5} ; do \
		$(PYTHON) $(SRC)/lexer.py -o out/lexer/$$i.out $(LEXER_TEST)/test$$i.c; \
	done

parser-tests:
	mkdir -p out/tac out/symtab
	mkdir -p dot/pdf
	for i in {1..5} ; do \
		$(PYTHON) -Wignore $(SRC)/parser.py $(PARSER_TEST)/test$$i.c; \
		dot -Tpdf -o dot/pdf/$$i.pdf dot/$$i.dot; \
	done

final-tests:
	mkdir -p out/tac out/symtab out/exec out/assembly
	for i in {1..33} ; do \
		$(PYTHON) -Wignore $(SRC)/parser.py $(FINAL_TEST)/$$i.c; \
		$(PYTHON) -Wignore $(SRC)/codegen.py out/tac/$$i.txt; \
		gcc -w -m32 -o out/exec/$$i.out out/assembly/$$i.s src/lib.o -lm 2> /dev/null; \
	done

compile:
	mkdir -p out/tac out/symtab out/exec out/assembly
	- rm out/tac/$(TEST).txt out/assembly/$(TEST).s out/exec/$(TEST).out
	$(PYTHON) -Wignore $(SRC)/parser.py $(FINAL_TEST)/$(TEST).c
	$(PYTHON) -Wignore $(SRC)/codegen.py out/tac/$(TEST).txt
	gcc -w -m32 -o out/exec/$(TEST).out out/assembly/$(TEST).s src/lib.o -lm 2> /dev/null

make exec:
	for i in {1..33} ; do \
		./out/exec/$$i.out; \
	done

clean:
	-rm dot/*.dot
	-rm dot/pdf/*.pdf
	-rm -r out