//struct
struct rect{
    int height;
    int width;
};
struct circ{
    float xc;
    float yc;
    int rad;
};
int main(){
    struct rect r1;
    struct rect r2;
    r1.height=45;
    r1.width=44;
    r2.height=r1.height-r1.width;
    r2.width=1;
    printf("r2.height=%d\n",r2.height);
    printf("r2.width=%d\n",r2.width);
    return 0;
}
/*
r2.height=1
r2.width=1
*/