//mutual recursion
int count;
int f2(int x)
{
    char ch;
    if(x>0 && x<=5)
    {
        x--;
        ch=f2(x);
    }
    return x;
}
int f1(int x)
{
    float c;
    if(x>0)
    {
        x--;
        c=f2(x);
    }
    printf("x=%d\n",x);
    return x;
}
int main()
{
    count = 5;
    int a=f1(count);
    printf("a=%d\n",a);
}
/*
x=4
a=4
*/