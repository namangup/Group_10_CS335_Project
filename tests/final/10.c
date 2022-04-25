//do while
int main(){
    short x=2;
    int y=0;
    do{
        if(x%2==0){
            y=1;
        }
        x++;
    }while(x!=3);
    printf("x=%d\n",x);
    printf("y=%d\n",y);
    return 0;
}
/*
x=3
y=1
*/