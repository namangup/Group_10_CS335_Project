//Multidimensional Arrays
int main(){
    int a[10][10];
    int i,j;
    for(i=0;i<10;i++){
        for(j=0;j<10;j++){
            a[i][j]=((i+j)%(j+1))*j;
        }
    }
    for(i=0;i<10;i++){
        for(j=0;j<10;j++){
            printf("Matrix element:%d\n",a[i][j]);
        }
    }
    return 0;
}
/*
Matrix element:0
Matrix element:1
Matrix element:4
Matrix element:9
Matrix element:16
Matrix element:25
Matrix element:36
Matrix element:49
Matrix element:64
Matrix element:81
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:1
Matrix element:2
Matrix element:3
Matrix element:4
Matrix element:5
Matrix element:6
Matrix element:7
Matrix element:8
Matrix element:9
Matrix element:0
Matrix element:0
Matrix element:4
Matrix element:6
Matrix element:8
Matrix element:10
Matrix element:12
Matrix element:14
Matrix element:16
Matrix element:18
Matrix element:0
Matrix element:1
Matrix element:0
Matrix element:9
Matrix element:12
Matrix element:15
Matrix element:18
Matrix element:21
Matrix element:24
Matrix element:27
Matrix element:0
Matrix element:0
Matrix element:2
Matrix element:0
Matrix element:16
Matrix element:20
Matrix element:24
Matrix element:28
Matrix element:32
Matrix element:36
Matrix element:0
Matrix element:1
Matrix element:4
Matrix element:3
Matrix element:0
Matrix element:25
Matrix element:30
Matrix element:35
Matrix element:40
Matrix element:45
Matrix element:0
Matrix element:0
Matrix element:0
Matrix element:6
Matrix element:4
Matrix element:0
Matrix element:36
Matrix element:42
Matrix element:48
Matrix element:54
Matrix element:0
Matrix element:1
Matrix element:2
Matrix element:9
Matrix element:8
Matrix element:5
Matrix element:0
Matrix element:49
Matrix element:56
Matrix element:63
Matrix element:0
Matrix element:0
Matrix element:4
Matrix element:0
Matrix element:12
Matrix element:10
Matrix element:6
Matrix element:0
Matrix element:64
Matrix element:72
*/