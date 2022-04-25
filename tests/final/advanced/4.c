//short circuit
int main(){
    int a=1;
    int b=2;
    int c;
    if(a==1||b++){
        c=a+b;
    }
    printf("a=%d\n",a);
    printf("b=%d\n",b);
    printf("c=%d\n",c);
    return 0;
}
/*
a=1
b=2
c=3
*/