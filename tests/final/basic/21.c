int iden(int x)
{
    return x;
}

int main()
{
    int b = 5, c = 2;
    int a = iden(b*c);
    printf("%d\n", a);
}