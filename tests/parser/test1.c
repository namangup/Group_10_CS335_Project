int main()
{
    int t = 0;
    int n = 0;
    char s[100000][4] = {0};

    int res = 0;
    int i;

    int s_int[100000] = {0};
    int s_app[19683] = {0};

    res = scanf("%d", &t);

    for (i = 0; i < 19683; i++)
    {
        s_app[i] = t + 1;
    }

    while (t > 0)
    {
        int is_ok = 0;
        res = scanf("%d", &n);
        for (i = 0; i < n; i++)
        {
            int tmp = 0;
            res = scanf("%s", s[i]);
            if (s[i][1] == '\0')
            {
                tmp = ((int)(s[i][0] - 'a')) + 1;
                is_ok = 1;
            }
            else if (s[i][2] == '\0')
            {
                tmp = ((int)(s[i][0] - 'a')) + 1;
                tmp *= 27;
                tmp += ((int)(s[i][1] - 'a')) + 1;
                if (s[i][0] == s[i][1])
                {
                    is_ok = 1;
                }
                else
                {
                    int tmp = 0;
                    if (s_app[((int)(s[i][0] - 'a')) + 1] == t)
                    {
                        is_ok = 1;
                    }
                    tmp = ((int)(s[i][1] - 'a')) + 1;
                    tmp *= 27;
                    tmp += ((int)(s[i][0] - 'a')) + 1;
                    if (s_app[tmp] == t)
                    {
                        is_ok = 1;
                    }
                    for (i = 1; i <= 26; i++)
                    {
                        if (s_app[tmp * 27 + i] == t)
                        {
                            is_ok = 1;
                        }
                    }
                }
            }
            else
            {
                tmp = ((int)(s[i][0] - 'a')) + 1;
                tmp *= 27;
                tmp += ((int)(s[i][1] - 'a')) + 1;
                tmp *= 27;
                tmp += ((int)(s[i][2] - 'a')) + 1;
                if (s[i][0] == s[i][2])
                {
                    is_ok = 1;
                }
                else
                {
                    int tmp = ((int)(s[i][2] - 'a')) + 1;
                    tmp *= 27;
                    tmp += ((int)(s[i][1] - 'a')) + 1;
                    tmp *= 27;
                    tmp += ((int)(s[i][0] - 'a')) + 1;
                    if (s_app[tmp] == t || s_app[tmp / 27] == t)
                    {
                        is_ok = 1;
                    }
                }
            }
            s_app[tmp] = t;
        }
        if (is_ok > 0)
        {
            printf("YES\n");
        }
        else
        {
            printf("NO\n");
        }
        t--;
    }

    return 0;
}