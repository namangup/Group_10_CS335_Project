//bool
int main(){
    bool a=true;
    bool b=false;
    a&=b;
    int c=0;
    if(a==b){
        c=5;
    }
    printf("c=%d\n",c);
    return 0;
}
/*
c=5
*/