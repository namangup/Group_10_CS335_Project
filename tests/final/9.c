//While loop
int main(){
    int a=1;
    int b=256;
    while(a<=5){
        b=b<<1;
        a++;
    }
    printf("b=%d\n",b);
    return 0;
}
/*
b=8192
*/