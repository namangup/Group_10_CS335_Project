// Given an integer array nums, return the sum of Hamming distances between all the pairs of the integers in nums.
int totalHammingDistance(int *nums, int numsSize)
{
    int ret = 0;
    int temp = 0;
    int i, j;
    for (i = 0; i < 32; i++)
    {
        temp = 0;
        for (j = 0; j < numsSize; j++)
        {
            if ((nums[j] & 1) == 1)
            {
                temp++;
            }
            nums[j] = nums[j] >> 1;
        }
        ret = ret + temp * (numsSize - temp);
    }
    return ret;
}
void main()
{
    int *nums;
    int n[10]; /* n is an array of 10 integers */
    int i, j;

    /* initialize elements of array n to 0 */
    for (i = 0; i < 10; i++)
    {
        n[i] = i + 100; /* set element at location i to i + 100 */
    }

    nums = n;

    printf("Result : %d \n", totalHammingDistance(nums, 10));
}
