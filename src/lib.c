#define NULL 0
int strlen(char *s) // may need fixing
{
    char *tmp;
    for(tmp = s; *tmp; tmp++);
    return (tmp-s);
}

char* strcpy(char *dest, char *source)
{
    if (dest==NULL) // check if Null works correctly
    {
        return NULL;
    }
    char *ret_value=dest;

    while((*dest++ = *source++)!='\0');

    return ret_value;
}

char* strcat(char *dest, char *source) {
    char *ptr = dest + strlen(dest);
    while(*source != '\0') {
        *ptr = *source;
        ptr ++;
        source++;
    }
    *ptr = '\0';
    return dest;
}

int strcmp(char *first, char *second)
{
    int diff=-1;
    while (*second++ == *first)
    {
        if(*first++ == '\0')
            diff=0;
    }
    second--;
    if(diff==-1)
        diff= *first - *second;
    return diff;
}

char* strrev(char *str)
{
    int len=strlen(str);
    for(int i=0;i<=len/2;i++)
    {
        char tmp = str[i];
        str[i] = str[len-1-i];
        str[len-1-i]=tmp;

    }
    return str;
}

char* strupr(char *str)
{
    char* tmp=str;
    int offset='a'-'A';
    while(str && *tmp!='\0')
    {
        if(*tmp >='a' && *tmp <= 'z')
            *tmp-=offset;
        tmp++;
    }
    return str;
}

char* strlwr(char *str)
{
    char* tmp=str;
    int offset='a'-'A';
    while(str && *tmp!='\0')
    {
        if(*tmp >='A' && *tmp <= 'Z')
            *tmp+=offset;
        tmp++;
    }
    return str;
}