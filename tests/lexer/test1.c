/* In this file, we test various combinations of constants and individual 
tokens trying to deliberately break the lexer */

/***** CONSTANTS *****/
/* Integers and Floats */

// Legal
10
20
01 // Octal
0xAF1 // Hex
2.E-10
2.0e0
0.e879
3.14159

// Illegal but the parser would handle the syntax error
93840+
3E5.          /* Illegal: Exponent can only be an integer */
314159E-5L    /* Illegal: Suffixes like U, L not supported */
510E          /* Illegal: incomplete exponent */
210f          /* Illegal: no decimal or exponent */
.e55          /* Illegal: missing integer or fraction */

/* Character and String */

'a'
'\?'
''\n''
'\'
'
"a\n\b\b\b\b\?"
"te" + "a" - "x" // testing that the first matching double quote ends the string
_stri
g@!/
"for loop"


/***** KEYWORDS *****/

break 
case 
char 
"break char"
"br"eak
for (int x = 0; x < 5; x++)
unsigned int x = false
int break = 34
short bool while 
if ( bool x = true){
    return 3
} else {
    float def = 3.5e-3
}
if < else if > 
char arr[10] = "stringing"
struct car {
    int tire;
    int driver;
};
Union

int brEAk
Short bool 

/***** IDENTIFIERS *****/
int num007ber=5;
bool 55num = true;                              /*Illegal : Starts with number */
unsigned int __heLLo, _hi_, hi_hOx2e5_hi_ho;
char _123 = (char)(123);
char _John_117_a[]="343_Industries";
int *ptr1 = NULL;                               
char* ptr_X2= (char *)null;                     /* Illegal: Only NULL (upper case) is supported */
int do for if else else if not or and while = 619;                                /*Illegal : Reserved Keyword */
int WHILE, While, wHiLe;
printf("%d %.2f %3d")

int isEven_ig_2isDefinitely___Even(int num123)
{
    return ~(num123%2);
}

/***** OPERATORS *****/


a + b - c / d
++ += == -= -- - - + + ++a++
34%10
while(x=3){
    x+=4 || y -=2 || z >>= 1 || k <<= 1
}
int x = !((f_l&&l_f)||o_r)) // testing if brackets work correctly

int log = (3<<3)&(1|10)
int* k = &f // pointer operators
f->k->two->f 
int x, y // comma seperator
(void* ptr = null, ptr = &p, !ptr)
 a,, b ,. c
x = (x != y)?(a++:b++) // ternary operator
