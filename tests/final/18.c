//global variables
int cnt;
void func(){
    cnt+=5;
    return;
}
int main(){
    int a;
    cnt = 0;
    func();
    a=cnt*2;
    printf("a=%d\n",a);
    return 0;
}
/*
a=10
*/