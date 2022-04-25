# ccpy
C compiler implemented in Python for x86, CS335 2021-22 II, Group No. 10

Our implementation of the C compiler follows grammar rules for ANSI C (C89). One of major differences in this version of C is the need to declare variables at the start of the scope. Therefore our compiler would be able to work with code that is compliant with C89 standards.

Source Language : C (ANSI C89)\
Implementation Language : Python 3 \
Target Language : x86 Assembly (32-bit)

## Usage

### Lexer
```
python src/lexer.py -h
usage: lexer.py [-h] [-d] [-o OUT] infile

positional arguments:
  infile             Input File

optional arguments:
  -h, --help         show this help message and exit
  -d, --debug        Debug Mode
  -o OUT, --out OUT  Store output of lexer in a file
```

### Parser
```
python src/parser.py -h
usage: parser.py [-h] [-d] [-o OUT] infile

positional arguments:
  infile             Input File

optional arguments:
  -h, --help         show this help message and exit
  -d, --debug        Parser Debug Mode
  -o OUT, --out OUT  Store output of parser in a file
```

### Codegen
```
python src/codegen.py
usage: codegen.py  infile
```

### Generating Automaton Graph
> Note: This is a time consuming step.

Make sure you have [graphviz](http://www.graphviz.org/) installed, which is a tool for generating graphs.

You need to first run parser in debug mode to generate parser.out
```bash
$ python src/automaton.py
$ dot -Tpdf -O automaton.dot
```

## Structure

### For installing Dependencies
```bash 
$ make install
# OR
$ pip install --ignore-installed -r ./requirements.txt  
```

### For running individual lexer tests
- make sure that you are the home directory, i.e., ccpy
```bash
$ python3 ./src/lexer.py -o out/lexer/1.out ./test/lexer/test1.c

```
### For running all lexer tests at once
```bash
$ make lexer-tests 

```
### For running individual parser tests
- make sure that you are the home directory, i.e., ccpy
```bash
$ python3 ./src/parser.py -o out/parser/1.out ./test/parser/test1.c

```
### For running all parser tests at once
```bash
$ make parser-tests 

```
### For cleaning the test outputs
```bash
$ make clean 

```

## Contributors


Naman Gupta \
Ayush Shakya \
Soham Ghosal \
Lakshay Rastogi