int fibbonacci(int n)
{
    if (n == 0)
    {
        return 0;
    }
    else if (n == 1)
    {
        return 1;
    }
    else
    {
        return (fibbonacci(n - 1) + fibbonacci(n - 2));
    }
}

int func1(int a, float b, char c)
{
    int k;
    int ar[5];
    float arr[5][10][15];
    {
        int k;
        k = 5;
    }
    for (int i = 1; i <= 5; i++)
    {
        ar[i - 1] = 1;
    }
    arr[1][2][3] = 6.9;
    return a + (int)b - (int)c;
}

int main()
{

    int val;
    val = func1(5, 3.3, 'a');
    return 0;
}
