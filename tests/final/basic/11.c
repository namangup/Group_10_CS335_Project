//Single dimensional Arrays
int main(){
    char a[10];
    int i=0;
    for(i=0;i<10;i++){
        a[i]='z';
    }
    int b[10];
    for(i=0;i<10;i++){
        b[i]=a[i];
    }
    for(i=0;i<10;i++){
        printf("Array element:%d\n",b[i]);
    }
    return 0;
}
/*
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
Array element:122
*/