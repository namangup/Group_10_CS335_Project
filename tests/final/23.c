//string lib functions
int main(){
    char str[15];
    str[0] = 'c';
    str[1] = 'o';
    str[2] = 'm';
    str[3] = 'p';
    str[4] = 'i';
    str[5] = 'l';
    str[6] = 'e';
    str[7] = '\0';
    char temp[20];
    temp[0] = 'h';
    temp[1] = 'e';
    temp[2] = 'l';
    temp[3] = 'l';
    temp[4] = 'o';
    temp[5] = '.';
    temp[6] = '\0';
    char str2[10];
    char* ret = strcpy(str2,str);
    printf("str2 = %s\n", str2);
    printf("ret = %s\n", ret);
    ret=strcat(temp,str);
    printf("%s\n", ret);
    ret = strrev(str);
    printf("%s\n", ret);
    ret=strupr(str);
    printf("%s\n", ret);
    ret=strlwr(str);
    printf("%s\n", ret);
    
    return 0;
}