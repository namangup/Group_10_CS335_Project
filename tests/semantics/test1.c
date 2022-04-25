// test for checking all loops
int main()
{
    int a;
    float b;
    char c;
    a = -5;
    b = -6.5;
    c = 'a';
    for (int i = b; i <= a + 100; i++)
        ;
    while (c <= 'z')
    {
        if (c == 'q' || c == 'c')
            continue;
        c++;
    }
    do
    {
        b -= -0.1;
    } while (b != 6);
    return 0;
}