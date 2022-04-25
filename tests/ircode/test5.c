struct a
{
    int x;
};
struct b
{
    int x1, y1;
};
union c
{
    int k;
};
int main()
{
    int float c;
    int d = 5;
    float d = 'a';

    struct a *ptr;
    ptr->x = 5;
    ptr->x = 'a';
    ptr->y = 6;

    int ar[10];
    int i;
    for (i = 0; i <= 10; i++)
        ar[i] = i + 1;

    struct a x1;
    struct b x2;
    x1.x = 56;
    x2 = x1;
    print("%d\n", x2.x1);

    union c x3;
    x3 = x1;

    float sin_d = sine(d);
    int itr = 0;
    do
    {
        printf("Hey\n");
    } while (itr < 2);

    int arr[5][10];
    arr[5][9] = 10;
    arr[0] = 14;
    arr[1][1][1] = 2;

    return 0;
}