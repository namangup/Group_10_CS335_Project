//pointers
int main(){
    int a=10;
    int b=a;
    int* p=&a;
    int* q=&b;
    int c;
    *p=20;
    c=a+b;
    printf("a=%d\n",a);
    printf("b=%d\n",b);
    printf("c=%d\n",c);
    return 0;
}
/*
a=20
b=10
c=30
*/