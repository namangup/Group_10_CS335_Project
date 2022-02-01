int main()
{
    int t = 0;
    int n = 0;
    int k = 0;
    int b[1000] = {};
    int c[1000] = {};

    int res = 0;

    int dp[20000] = {};
    int op[1000] = {};
    int d[1001] = {};

    int q[1000] = {};
    int q_hd = 0;
    int q_tl = 0;
    switch (res)
    {
    case 0:
        break;
    default:
        break;
    }

    res = scanf("%d", &t);
    while (t > 0)
    {
        int op_sum = 0;
        int c_sum = 0;

        res = scanf("%d", &n);
        res = scanf("%d", &k);
        for (int i = 0; i < n; i++)
        {
            res = scanf("%d", b + i);
        }
        for (int i = 0; i < n; i++)
        {
            res = scanf("%d", c + i);
            c_sum += c[i];
        }

        for (int i = 0; i < n; i++)
        {
            for (int j = 0; j <= b[i]; j++)
            {
                d[j] = -1;
            }
            d[1] = 0;
            q[0] = 1;
            q_hd = 0;
            q_tl = 1;
            while (q_hd < q_tl && d[b[i]] < 0)
            {
                int v = q[q_hd];
                q_hd++;
                for (int j = 1; j * j <= v; j++)
                {
                    int u = v + v / j;
                    if (u <= b[i] && d[u] < 0)
                    {
                        d[u] = d[v] + 1;
                        q[q_tl] = u;
                        q_tl++;
                    }
                    u = v + j;
                    if (u <= b[i] && d[u] < 0)
                    {
                        d[u] = d[v] + 1;
                        q[q_tl] = u;
                        q_tl++;
                    }
                }
            }
            op[i] = d[b[i]];
            op_sum += op[i];
        }

        if (op_sum <= k)
        {
            printf("%d\n", c_sum);
        }
        else
        {
            int ans = 0;
            for (int i = 0; i <= k; i++)
            {
                dp[i] = 0;
            }
            if (op[0] <= k)
            {
                dp[op[0]] = c[0];
            }
            for (int i = 1; i < n; i++)
            {
                for (int j = k; j >= 0; j--)
                {
                    if (j + op[i] <= k && dp[j + op[i]] < dp[j] + c[i])
                    {
                        dp[j + op[i]] = dp[j] + c[i];
                    }
                }
                if (op[i] <= k && dp[op[i]] < c[i])
                {
                    dp[op[i]] = c[i];
                }
            }
            for (int i = 0; i <= k; i++)
            {
                if (ans < dp[i])
                {
                    ans = dp[i];
                }
            }
            printf("%d\n", ans);
        }

        t--;
    }

    return 0;
}
