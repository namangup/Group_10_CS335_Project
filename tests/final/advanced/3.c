//multilevel pointers
int main(){
    int n=10;
    int* p1=&n;
    int **p2=&p1;
    int ***p3=&p2;
    *p1=20;
    printf("***p3=%d\n", ***p3);
    return 0;
}
/*
***p3=20
*/