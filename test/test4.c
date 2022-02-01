char *reverse(char *px) {
  int n = strlen(px);
  char *perm = malloc(sizeof(char) * (n+1));
  for (int i = 0; i < n; i++)
    perm[i] = px[n-1-i];
  perm[n] = '\0';
  return perm;
}
  
char *gen(int a) {
  char *perm = malloc(sizeof(char) * 100);
  int i = 0;
  while (a) {
    if (a & 1) perm[i++] = '1';
    else perm[i++] = '0';
    a >>= 1;
  }
  perm[i] = '\0';
  return reverse(perm);
}
  
int check(char *y, char *x) {
  char *yy = malloc(sizeof(char) * 100), *xx = malloc(sizeof(char) * 100), one[100], temp[100];
  strcpy(xx, x), strcpy(yy, y);
  for (int i = 0; i < 100; i++) one[i] = '1';
  
  char *str = strstr(yy, xx);
  int len = strlen(xx), i;
  if (str != NULL) {
    strncpy(temp, str, len);
    strncpy(str, one, len);
    for (i = 0; yy[i] != '\0'; i++)
      if (yy[i] != '1') break;
    strncpy(str, temp, len);
  
    if (yy[i] == '\0') return 1;
  }
  
  xx = reverse(xx);
  
  str = strstr(yy, xx);
  if (str != NULL) {
    strncpy(temp, str, len);
    strncpy(str, one, len);
    for (i = 0; yy[i] != '\0'; i++)
      if (yy[i] != '1') break;
    strncpy(str, temp, len);
  
    if (yy[i] == '\0') return 1;
  }
  
  return 0;
}
  
int main() {
  int x, y;
  scanf("%d %d", &x, &y);
  int found = (x == y);
  char *permX = gen(x), *permY = gen(y);
  x = strlen(permX), y = strlen(permY);
  
  if (permX[x-1] == '1') {
    found |= check(permY, permX);
  }
  else {
    permX[x] = '1', permX[x+1] = '\0';
    found |= check(permY, permX);
    while (permX[x-1] == '0') permX[--x] = '\0';
    found |= check(permY, permX);
  }
  
  puts(found ? "YES" : "NO");
  
  return 0;
}