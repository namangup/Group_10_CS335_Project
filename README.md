# ccpy
C compiler implemented in Python for x86, CS335 2021-22 II, Group No. 10

Source Language : C \
Implementation Language : Python 3 \
Target Language : x86 Assembly (32-bit)

## Usage

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
## Structure

### For installing Dependencies
```bash 
$ make install
# OR
$ pip install --ignore-installed -r ./requirements.txt  
```
### For running individual tests
- make sure that you are the home directory, i.e., ccpy
```bash
$ python3 ./src/lexer.py -o out/1.out ./test/test1.c

```
### For running all tests at once
```bash
$ make tests 

```
### For cleaning the test outputs
```bash
$ make clean 

```

