int v;
int INF;
void printSolution(int **dist)
{
    char *str = "The following matrix shows the shortest distances between every pair of vertices \n";
    printf ("%s", str);
    for (int i = 0; i < v; i++)
    {
        for (int j = 0; j < v; j++)
        {
            if (dist[i][j] == INF)
                printf("%7s", "INF");
            else
                printf ("%7d", dist[i][j]);
        }
        printf("%s\n", "");
    }
}

void floydWarshall (int **graph)
{
    int **dist = (int **)malloc(v*sizeof(int*));
    for(int i=0; i<v; i++)
    {
        dist[i] = (int *)malloc(v*sizeof(int));
    }
    int i, j, k;

    for (i = 0; i < v; i++)
        for (j = 0; j < v; j++)
            dist[i][j] = graph[i][j];
 

    for (k = 0; k < v; k++)
    {
        for (i = 0; i < v; i++)
        {
            for (j = 0; j < v; j++)
            {
                if (dist[i][k] + dist[k][j] < dist[i][j])
                    dist[i][j] = dist[i][k] + dist[k][j];
            }
        }
    }
    printSolution(dist);
}
 
int main()
{
    v = 4;
    INF = 99999;
    int **graph = (int **)malloc(v*sizeof(int*));
    for(int i=0; i<v; i++)
    {
        graph[i] = (int *)malloc(v*sizeof(int));
    }
    graph[0][0]=0;
    graph[0][1]=5;
    graph[0][2]=INF;
    graph[0][3]=10;
    graph[1][0]=INF;
    graph[1][1]=0;
    graph[1][2]=3;
    graph[1][3]=INF;
    graph[2][0]=INF;
    graph[2][1]=INF;
    graph[2][2]=0;
    graph[2][3]=1;
    graph[3][0]=INF;
    graph[3][1]=INF;
    graph[3][2]=INF;
    graph[3][3]=0;
    floydWarshall(graph);
    return 0;
}
/*
The following matrix shows the shortest distances between every pair of vertices 
      0      5      8      9
    INF      0      3      4
    INF    INF      0      1
    INF    INF    INF      0
*/