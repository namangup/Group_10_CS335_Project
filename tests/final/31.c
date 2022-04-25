//Multiple scoping
int main()
{
    int i = 5;
    {
        int i = 8;
        {
            int i = 10;
            printf("%d\n", i);
        }
        printf("%d\n", i);
    }
    printf("%d\n", i);
}