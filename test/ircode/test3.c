struct st
{
    int a;
    float b;
    char c;
    short d;
    bool e;
};
union un
{
    int a;
    float b;
    char c;
    short d;
    bool e;
};

int *main()
{

    struct st st1;
    union un un1;
    struct st *st_pointer, *st_pointer2;
    int *a;
    int **aa;
    {
        struct st st11;
        int a11 = 0;
        st11.a = 1;
        st11.b = 1.1;
        st11.c = 'a';
        st11.d = 1;
        st11.e = false;
        {
            union un un11;
            int b1 = 0;
            un11.a = 2;
            un11.c = 'b';
            un11.b = 2.2;
            un11.d = st1.a + 5;
            un11.e |= true;
            {
                int x1 = 0;
                int x12 = 0;
            }
        }
        {
            int b2 = 0;
            {
                int x2 = 0;
                int x22 = 0;
                {
                    int acs = 0;
                }
                {
                    int bdx = 0;
                }
            }
        }
        {
            int b2 = 0;
            {
                int x2 = 0;
                int x22 = 0;
                {
                    int acs = 0;
                }
                {
                    int bdx = 0;
                }
                {
                    int acs = 0;
                    {
                        int qrety = 0;
                        {
                            int bdxx = 0;
                        }
                        {
                            int cdxx = 0;
                        }
                        {
                            int ddxx = 0;
                        }
                    }
                }
                {
                    int bdx;
                    {
                        int kaju = 0;
                    }
                }
            }
        }
    }
    {
        int a = 1;
    }
    st1.a = 1;
    st1.b = 1.1;
    st1.c = 'a';
    st1.d = 1;
    st1.e = false;

    un1.a = 2;
    un1.b = 2.2;
    un1.c = 'b';
    un1.d = st1.a + 5;
    un1.e |= true;

    st_pointer = &st1;
    *st_pointer2 = st1;
    a = &un1.a;
    aa = &a;
    return a;
}