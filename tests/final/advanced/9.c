// Malloc, Calloc, Realloc, Free, Sizeof
int main()
{
    int *arr = (int*)malloc(10*sizeof(int));
    arr[9] = 10;
    printf("%d\n", arr[9]);
    printf("%d\n", arr[5]);
    free(arr);
    printf("%d\n", arr[9]);
    arr = (int*)calloc(10, sizeof(int));
    printf("%d\n", arr[9]);
    printf("%d\n", arr[5]);
    arr = (int*)realloc(arr, 20*sizeof(int));
    arr[19] = 10;
    printf("%d\n", arr[9]);
    printf("%d\n", arr[19]);
}
/*
10
0
10
0
0
0
10
*/