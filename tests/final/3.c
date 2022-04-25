/*
Operators
and
expressions
and multiline comment
*/
int main(){
    int a=5;
    int b=6;
    int c=7;
    int d=a*b;
    int e=a%b;
    int *ptr;
    int f;
    int g;
    int h;
    d+=e;
    a>>=2;
    b=b>>1;
    c=(a<b)?5:6;
    ptr=&a;
    f=*ptr;
    g=a||b;
    h=a&&b;
    printf("a=%d\n",a);
    printf("b=%d\n",b);
    printf("c=%d\n",c);
    printf("d=%d\n",d);
    printf("e=%d\n",e);
    printf("f=%d\n",f);
    printf("g=%d\n",g);
    printf("h=%d\n",h);
    return 0;
}
/*
a=1
b=3
c=5
d=35
e=5
f=1
g=1
h=1
*/