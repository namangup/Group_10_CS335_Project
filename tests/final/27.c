// Function with large number of parameters
int f1(int a, int b, int c, int d, int e, int f, int g, int h, int i, int j, int k, int l, int m)
{
    int ret = a+b+c+d+e+f+g+h+i+j+k+l+m;
    return ret;
}
int main()
{
    int ans;
    ans = f1(1,2,3,4,5,6,7,8,9,10,11,12,13);
    printf("%d\n", ans);
}